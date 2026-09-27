from __future__ import annotations

import asyncio
import hashlib
from io import BytesIO
from uuid import UUID

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.config import Settings
from app.domain.errors import AvatarInvalidError, AvatarTooLargeError
from app.services.avatar_storage_service import (
    JPEG_MAGIC,
    PNG_MAGIC,
    AvatarObjectError,
    AvatarObjectMissingError,
    AvatarStorageService,
)

USER_ID = UUID("11111111-1111-4111-8111-111111111111")
OBJECT_ID = UUID("22222222-2222-4222-8222-222222222222")


def _settings(tmp_path, *, max_bytes: int = 512 * 1024) -> Settings:
    return Settings(
        _env_file=None,
        APP_ENV="test",
        APP_DEBUG=False,
        SECRET_KEY="test-secret-key-that-is-long-enough",
        AVATAR_DIR=tmp_path / "avatars",
        AVATAR_MAX_BYTES=max_bytes,
    )


def _upload(content: bytes, media_type: str | None = "image/png") -> UploadFile:
    headers = Headers({"content-type": media_type} if media_type else {})
    return UploadFile(filename="avatar.bin", file=BytesIO(content), headers=headers)


def _png(body: bytes = b"decoy pixels") -> bytes:
    return PNG_MAGIC + body


def _jpeg(body: bytes = b"decoy pixels") -> bytes:
    return JPEG_MAGIC + body


def test_a_png_is_stored_under_an_opaque_key_and_read_back_unchanged(tmp_path) -> None:
    storage = AvatarStorageService(settings=_settings(tmp_path))
    payload = _png()

    stored = asyncio.run(storage.store(_upload(payload), user_uuid=USER_ID))

    assert stored.content_type == "image/png"
    assert stored.object_key.startswith(f"{USER_ID}/")
    assert stored.object_key.endswith(".png")
    assert stored.size_bytes == len(payload)
    assert stored.sha256 == hashlib.sha256(payload).hexdigest()
    assert storage.read_bytes(stored.object_key) == payload


def test_the_content_type_comes_from_the_magic_bytes_not_the_declared_part(tmp_path) -> None:
    """A JPEG announced as a PNG is still a JPEG, and the row has to say so."""
    storage = AvatarStorageService(settings=_settings(tmp_path))

    # A part the browser declined to type, or typed as opaque bytes, contradicts nothing.
    for declared in (None, "application/octet-stream"):
        stored = asyncio.run(storage.store(_upload(_jpeg(), declared), user_uuid=USER_ID))
        assert stored.content_type == "image/jpeg"
        assert stored.object_key.endswith(".jpg")

    # An explicit, wrong claim is a request that contradicts itself.
    with pytest.raises(AvatarInvalidError):
        asyncio.run(storage.store(_upload(_jpeg(), "image/png"), user_uuid=USER_ID))


@pytest.mark.parametrize(
    ("label", "payload"),
    [
        ("a GIF", b"GIF89a" + b"\x00" * 32),
        ("an SVG", b"<svg xmlns='http://www.w3.org/2000/svg'><script/></svg>"),
        ("a Windows executable", b"MZ\x90\x00" + b"\x00" * 32),
        ("HTML", b"<!DOCTYPE html><html><body>hello</body></html>"),
        ("a truncated PNG signature", PNG_MAGIC[:-1]),
        ("a truncated JPEG signature", JPEG_MAGIC[:-1]),
        ("plain text named like an image", b"this is not an image at all"),
    ],
)
def test_anything_that_is_not_a_png_or_jpeg_is_refused(tmp_path, label, payload) -> None:
    """Content-Type is attacker-chosen, so the leading bytes are what decide.

    An SVG is the case that matters most: browsers execute script in one, and it would sail
    through a check that only read the declared part.
    """
    storage = AvatarStorageService(settings=_settings(tmp_path))

    with pytest.raises(AvatarInvalidError):
        asyncio.run(storage.store(_upload(payload, "image/png"), user_uuid=USER_ID))
    assert list((tmp_path / "avatars").glob("**/*")) == [], label


def test_an_empty_part_is_refused(tmp_path) -> None:
    storage = AvatarStorageService(settings=_settings(tmp_path))

    with pytest.raises(AvatarInvalidError):
        asyncio.run(storage.store(_upload(b""), user_uuid=USER_ID))


def test_an_image_over_the_ceiling_is_refused_without_leaving_a_file(tmp_path) -> None:
    storage = AvatarStorageService(settings=_settings(tmp_path, max_bytes=64))

    with pytest.raises(AvatarTooLargeError):
        asyncio.run(storage.store(_upload(_png(b"x" * 64)), user_uuid=USER_ID))
    assert list((tmp_path / "avatars").glob("**/*")) == []

    # Exactly at the ceiling is still accepted.
    at_limit = _png(b"x" * (64 - len(PNG_MAGIC)))
    stored = asyncio.run(storage.store(_upload(at_limit), user_uuid=USER_ID))
    assert stored.size_bytes == 64


def test_an_oversize_part_is_refused_from_its_declared_size_before_it_is_read(
    tmp_path,
) -> None:
    storage = AvatarStorageService(settings=_settings(tmp_path, max_bytes=64))
    body = BytesIO(_png(b"x" * 1024))
    upload = UploadFile(
        filename="avatar.bin",
        file=body,
        headers=Headers({"content-type": "image/png"}),
        size=4096,
    )

    with pytest.raises(AvatarTooLargeError):
        asyncio.run(storage.store(upload, user_uuid=USER_ID))

    # Nothing was consumed: the declared size alone was enough to refuse the request.
    assert body.tell() == 0


@pytest.mark.parametrize(
    "object_key",
    [
        "../outside.png",
        "/etc/passwd",
        f"{USER_ID}/../../outside.png",
        f"{USER_ID}/sub/dir/image.png",
        f"{USER_ID}",
        f"{USER_ID}/.hidden.png",
    ],
)
def test_a_key_that_is_not_exactly_one_account_directory_and_one_file_is_refused(
    tmp_path,
    object_key,
) -> None:
    storage = AvatarStorageService(settings=_settings(tmp_path))

    with pytest.raises(AvatarObjectError):
        storage.read_bytes(object_key)
    with pytest.raises(AvatarObjectError):
        storage.delete(object_key)


def test_reading_a_key_whose_file_is_gone_is_distinguishable_from_a_bad_key(tmp_path) -> None:
    storage = AvatarStorageService(settings=_settings(tmp_path))
    object_key = storage.allocate_object_key(USER_ID, "png", random_id=OBJECT_ID)

    with pytest.raises(AvatarObjectMissingError):
        storage.read_bytes(object_key)


def test_deleting_an_image_removes_its_account_directory_and_repeats_cleanly(tmp_path) -> None:
    storage = AvatarStorageService(settings=_settings(tmp_path))
    stored = asyncio.run(storage.store(_upload(_png()), user_uuid=USER_ID))
    account_directory = (tmp_path / "avatars" / str(USER_ID)).resolve()
    assert account_directory.is_dir()

    storage.delete(stored.object_key)
    storage.delete(stored.object_key)
    storage.delete(None)

    assert not account_directory.exists()
    assert (tmp_path / "avatars").resolve().is_dir()


def test_replacing_an_image_leaves_no_partial_file_behind(tmp_path) -> None:
    storage = AvatarStorageService(settings=_settings(tmp_path))

    first = asyncio.run(storage.store(_upload(_png(b"first")), user_uuid=USER_ID))
    second = asyncio.run(
        storage.store(_upload(_jpeg(b"second"), "image/jpeg"), user_uuid=USER_ID)
    )

    assert first.object_key != second.object_key
    account_directory = tmp_path / "avatars" / str(USER_ID)
    assert sorted(path.name for path in account_directory.iterdir()) == sorted(
        [first.object_key.split("/")[1], second.object_key.split("/")[1]]
    )
