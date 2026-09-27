from __future__ import annotations

import hashlib
import os
import re
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from uuid import UUID, uuid4

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings
from app.domain.errors import AvatarInvalidError, AvatarTooLargeError

_OBJECT_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_READ_CHUNK = 64 * 1024

# The only two formats accepted, identified by their leading bytes rather than by the
# Content-Type or filename the client sent. Both of those are attacker-chosen, and the
# whole point of validating an avatar is that the stored object really is the kind of image
# the row says it is.
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"
_SIGNATURES: tuple[tuple[bytes, str, str], ...] = (
    (PNG_MAGIC, "image/png", "png"),
    (JPEG_MAGIC, "image/jpeg", "jpg"),
)


class AvatarObjectError(OSError):
    """Internal avatar-storage failure whose message is safe from host-path disclosure."""


class AvatarObjectMissingError(FileNotFoundError):
    """Internal signal that never includes the resolved host path in its message."""


@dataclass(frozen=True, slots=True)
class StoredAvatar:
    object_key: str
    content_type: str
    sha256: str
    size_bytes: int


class AvatarStorageService:
    """Bounded local storage for plaintext profile images, under opaque keys.

    Deliberately a separate root from `FileStorageService`: avatars are the one thing here
    that is stored unencrypted, and keeping them out of the ciphertext directory means no
    key confusion, no accidental inclusion in an encrypted backup set, and no object key
    that could address one tree from the other.
    """

    def __init__(self, *, settings: Settings) -> None:
        self.settings = settings
        self.object_root = settings.AVATAR_DIR.resolve(strict=False)

    @staticmethod
    def allocate_object_key(
        user_uuid: UUID,
        extension: str,
        *,
        random_id: UUID | None = None,
    ) -> str:
        return f"{user_uuid}/{random_id or uuid4()}.{extension}"

    async def store(self, upload: UploadFile, *, user_uuid: UUID) -> StoredAvatar:
        """Validate the image, then publish it under a fresh key.

        The bytes are held in memory rather than streamed to a staging file: the ceiling is
        512 KiB and the format check needs the head of the payload before anything is
        written, so there is nothing to gain from a two-phase publish here.
        """
        payload = await self._read_bounded(upload)
        content_type, extension = self._identify(payload, declared=upload.content_type)
        object_key = self.allocate_object_key(user_uuid, extension)
        await run_in_threadpool(self._write, self._object_path(object_key), payload)
        return StoredAvatar(
            object_key=object_key,
            content_type=content_type,
            sha256=hashlib.sha256(payload).hexdigest(),
            size_bytes=len(payload),
        )

    def read_bytes(self, object_key: str) -> bytes:
        path = self._object_path(object_key)
        try:
            return path.read_bytes()
        except FileNotFoundError as exc:
            raise AvatarObjectMissingError("The stored avatar is missing") from exc
        except OSError as exc:
            raise AvatarObjectError("Unable to read the stored avatar") from exc

    def delete(self, object_key: str | None) -> None:
        if not object_key:
            return
        path = self._object_path(object_key)
        self._unlink_if_present(path)
        self._prune_empty_parent(path)

    async def _read_bounded(self, upload: UploadFile) -> bytes:
        max_bytes = self.settings.AVATAR_MAX_BYTES
        # `size` is the client's claim, so it is a cheap early refusal and never the only
        # one; the running total below is what actually bounds the read.
        if upload.size is not None and upload.size > max_bytes:
            raise AvatarTooLargeError()

        chunks: list[bytes] = []
        total = 0
        while chunk := await upload.read(_READ_CHUNK):
            total += len(chunk)
            if total > max_bytes:
                raise AvatarTooLargeError()
            chunks.append(chunk)
        if total == 0:
            raise AvatarInvalidError("The avatar image is empty")
        return b"".join(chunks)

    @staticmethod
    def _identify(payload: bytes, *, declared: str | None) -> tuple[str, str]:
        for magic, content_type, extension in _SIGNATURES:
            if payload.startswith(magic):
                break
        else:
            raise AvatarInvalidError()

        # A mismatch means the request contradicts itself, which is worth refusing rather
        # than silently correcting. A browser that declines to type the part at all, or
        # calls it opaque bytes, is not contradicting anything.
        if declared not in {None, "", "application/octet-stream", content_type}:
            raise AvatarInvalidError("The declared content type does not match the image bytes")
        return content_type, extension

    def _write(self, path: Path, payload: bytes) -> None:
        temporary = path.with_name(f".{path.name}.partial")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
            except BaseException:
                with suppress(OSError):
                    temporary.unlink()
                raise
            # The key contains a fresh UUID, so the destination cannot already exist; the
            # rename is here to keep a reader from ever seeing a partial image.
            os.replace(temporary, path)
        except OSError as exc:
            if isinstance(exc, AvatarObjectError):
                raise
            raise AvatarObjectError("Unable to store the avatar image") from exc

    def _object_path(self, object_key: str) -> Path:
        key = PurePosixPath(object_key)
        if (
            key.is_absolute()
            or len(key.parts) != 2
            or any(
                segment in {"", ".", ".."} or not _OBJECT_SEGMENT_RE.fullmatch(segment)
                for segment in key.parts
            )
        ):
            raise AvatarObjectError("Invalid avatar object key")
        path = self.object_root.joinpath(*key.parts).resolve(strict=False)
        try:
            path.relative_to(self.object_root)
        except ValueError as exc:
            raise AvatarObjectError("The avatar object escaped its configured root") from exc
        return path

    def _prune_empty_parent(self, path: Path) -> None:
        """Remove the per-account directory once its image is gone.

        Best effort by design, for the same reason as the encrypted-object root: `rmdir`
        refuses a non-empty directory, which is exactly the interlock wanted if a
        concurrent upload has just written a sibling, and a directory that cannot be
        removed is inert.
        """
        parent = path.parent
        if parent == self.object_root:
            return
        with suppress(OSError, ValueError):
            parent.relative_to(self.object_root)
            parent.rmdir()

    @staticmethod
    def _unlink_if_present(path: Path) -> None:
        try:
            path.unlink()
        except FileNotFoundError:
            return
        except OSError as exc:
            raise AvatarObjectError("Unable to remove the stored avatar") from exc
