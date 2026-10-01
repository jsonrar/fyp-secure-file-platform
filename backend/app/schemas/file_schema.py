from __future__ import annotations

import base64
import binascii
import re
import unicodedata
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

_MIME_TYPE_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}$"
)
_WRAPPED_KEY_LENGTHS = frozenset({256, 384, 512})

# The suites a file may be encrypted under. Every one is an AEAD with a 12-byte nonce and a
# 16-byte tag, which is why one set of columns and one CHECK constraint serve them all. The
# client commits to the name in the AAD, so ciphertext written under one cannot be
# reinterpreted as another.
#
# ChaCha20-Poly1305 is a different construction rather than another key length: a stream
# cipher authenticated by Poly1305, where AES-GCM is a block cipher authenticated by GHASH.
#
# Deliberately a Literal and not a str: the value is copied into a stored row and handed back
# to every client that later decrypts the file, so the set of legal names is enforced here
# rather than assumed. Nothing unauthenticated may join this list. The account key envelope is
# unaffected and remains AES-256-GCM.
EncryptionAlgorithm = Literal[
    "AES-128-GCM",
    "AES-192-GCM",
    "AES-256-GCM",
    "ChaCha20-Poly1305",
]


def _decode_canonical_base64(value: str, *, field_name: str) -> bytes:
    if not value or value != value.strip() or any(character.isspace() for character in value):
        raise ValueError(f"{field_name} must be canonical base64 without whitespace")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"{field_name} must be valid base64") from exc
    if base64.b64encode(decoded).decode("ascii") != value:
        raise ValueError(f"{field_name} must use canonical padded base64")
    return decoded


def _strict_base64(value: str, *, field_name: str, lengths: set[int] | frozenset[int]) -> str:
    decoded = _decode_canonical_base64(value, field_name=field_name)
    if len(decoded) not in lengths:
        expected = ", ".join(str(length) for length in sorted(lengths))
        raise ValueError(f"{field_name} must decode to {expected} bytes")
    return value


class StrictFileModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class FileUploadMetadata(StrictFileModel):
    """Client-created cryptographic envelope metadata for an encrypted upload."""

    file_id: UUID
    original_filename: Annotated[str, Field(min_length=1, max_length=255)]
    plaintext_size: Annotated[int, Field(ge=0)]
    mime_type: Annotated[str, Field(min_length=3, max_length=150)]
    encryption_algorithm: EncryptionAlgorithm = "AES-256-GCM"
    envelope_version: Literal[1] = 1
    aad_version: Literal[1] = 1
    nonce: str = Field(repr=False)
    auth_tag: str = Field(repr=False)
    owner_key_id: UUID
    key_wrapping_algorithm: Literal["RSA-OAEP-SHA256"] = "RSA-OAEP-SHA256"
    wrapped_file_key: str = Field(repr=False)
    recovery_key_id: UUID
    recovery_wrapped_file_key: str = Field(repr=False)
    encrypted_manifest: Annotated[str | None, Field(max_length=87_380, repr=False)] = None

    @field_validator("file_id", "owner_key_id", "recovery_key_id")
    @classmethod
    def require_rfc4122_uuid(cls, value: UUID) -> UUID:
        if value.variant != "specified in RFC 4122":
            raise ValueError("must be an RFC 4122 UUID")
        return value

    @field_validator("original_filename")
    @classmethod
    def validate_original_filename(cls, value: str) -> str:
        normalized = unicodedata.normalize("NFC", value)
        if normalized != normalized.strip():
            raise ValueError("original_filename must not have surrounding whitespace")
        if normalized in {".", ".."}:
            raise ValueError("original_filename is not a valid filename")
        if any(character in normalized for character in ("/", "\\", "\x00", "\r", "\n")):
            raise ValueError("original_filename must not contain path or control characters")
        if any(unicodedata.category(character) == "Cc" for character in normalized):
            raise ValueError("original_filename must not contain control characters")
        if normalized[-1] in {" ", "."}:
            raise ValueError("original_filename must not end with a space or period")
        return normalized

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, value: str) -> str:
        normalized = value.lower()
        if not _MIME_TYPE_RE.fullmatch(normalized):
            raise ValueError("mime_type must be a valid media type without parameters")
        return normalized

    @field_validator("nonce")
    @classmethod
    def validate_nonce(cls, value: str) -> str:
        return _strict_base64(value, field_name="nonce", lengths={12})

    @field_validator("auth_tag")
    @classmethod
    def validate_auth_tag(cls, value: str) -> str:
        return _strict_base64(value, field_name="auth_tag", lengths={16})

    @field_validator("wrapped_file_key")
    @classmethod
    def validate_wrapped_file_key(cls, value: str) -> str:
        return _strict_base64(
            value,
            field_name="wrapped_file_key",
            lengths=_WRAPPED_KEY_LENGTHS,
        )

    @field_validator("recovery_wrapped_file_key")
    @classmethod
    def validate_recovery_wrapped_file_key(cls, value: str) -> str:
        return _strict_base64(
            value,
            field_name="recovery_wrapped_file_key",
            lengths=_WRAPPED_KEY_LENGTHS,
        )

    @field_validator("encrypted_manifest")
    @classmethod
    def validate_encrypted_manifest(cls, value: str | None) -> str | None:
        if value is None:
            return None
        # The manifest is already encrypted by the client. Its decoded representation is
        # deliberately opaque to the server and is bounded to MySQL BLOB's 65,535 bytes.
        decoded = _decode_canonical_base64(value, field_name="encrypted_manifest")
        if not 1 <= len(decoded) <= 65_535:
            raise ValueError("encrypted_manifest must decode to between 1 and 65535 bytes")
        return value

    def nonce_bytes(self) -> bytes:
        return base64.b64decode(self.nonce, validate=True)

    def auth_tag_bytes(self) -> bytes:
        return base64.b64decode(self.auth_tag, validate=True)

    def wrapped_file_key_bytes(self) -> bytes:
        return base64.b64decode(self.wrapped_file_key, validate=True)

    def recovery_wrapped_file_key_bytes(self) -> bytes:
        return base64.b64decode(self.recovery_wrapped_file_key, validate=True)


class FileSummaryOut(StrictFileModel):
    file_id: UUID
    original_filename: str
    plaintext_size: int
    ciphertext_size: int
    mime_type: str | None
    encryption_algorithm: str
    status: str
    owner: bool
    # Who uploaded it. The listing mixes files you own with files shared with you, and
    # "shared with me" is not much use without saying who by.
    owner_username: str | None = None
    # Organizational metadata belongs to the owner and is never part of the encrypted
    # envelope. Shared rows deliberately expose no folder assignment to recipients.
    folder_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class FileCryptoEnvelopeOut(StrictFileModel):
    encryption_algorithm: EncryptionAlgorithm
    envelope_version: int
    aad_version: int
    nonce: str
    auth_tag: str
    key_id: UUID
    key_wrapping_algorithm: Literal["RSA-OAEP-SHA256"]
    wrapped_file_key: str
    encrypted_manifest: str | None = None


class FileOut(FileSummaryOut):
    crypto_envelope: FileCryptoEnvelopeOut


class FileListOut(StrictFileModel):
    items: list[FileSummaryOut]
    page: int
    page_size: int
    total: int


class FolderNameIn(StrictFileModel):
    name: Annotated[str, Field(min_length=1, max_length=80)]

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = unicodedata.normalize("NFC", value).strip()
        if not normalized:
            raise ValueError("name must contain a visible character")
        if normalized in {".", ".."}:
            raise ValueError("name is reserved")
        if any(character in normalized for character in ("/", "\\", "\x00", "\r", "\n")):
            raise ValueError("name must not contain path or control characters")
        if any(unicodedata.category(character) == "Cc" for character in normalized):
            raise ValueError("name must not contain control characters")
        return normalized


class FileFolderOut(StrictFileModel):
    folder_id: UUID
    name: str
    file_count: int
    created_at: datetime
    updated_at: datetime


class FileFolderListOut(StrictFileModel):
    items: list[FileFolderOut]


class FileMoveIn(StrictFileModel):
    # Strict mode refuses a UUID given as text when FastAPI hands it an already-parsed JSON
    # body ("Input should be an instance of UUID"), and a JSON body can only ever carry text.
    # Moving a file into any folder therefore failed. `strict=False` on this one field lets the
    # string through; it is still validated as a UUID, and `null` still means "unfiled".
    folder_id: Annotated[UUID | None, Field(strict=False)]


class FileMoveOut(StrictFileModel):
    file_id: UUID
    folder_id: UUID | None


class FileFolderDeleteOut(StrictFileModel):
    folder_id: UUID
    files_unfiled: int


class FileDeleteOut(StrictFileModel):
    file_id: UUID
    status: Literal["DELETED"]
    already_deleted: bool


class CiphertextPreviewOut(StrictFileModel):
    """A bounded look at the bytes the server actually stores for a file.

    The sample is the *start of the stored ciphertext*, not of the original file, and it is
    not integrity-checked here (that would mean hashing the whole object): `status` and the
    separate integrity check say whether the stored bytes still match `ciphertext_sha256`.
    """

    file_id: UUID
    encryption_algorithm: str
    plaintext_size: int
    ciphertext_size: int
    ciphertext_sha256: str
    status: str
    sample_offset: int
    sample_length: int
    sample_hex: str


class IntegrityCheckOut(StrictFileModel):
    file_id: UUID
    status: Literal["VALID", "MODIFIED", "MISSING", "ERROR"]
    expected_hash: str
    actual_hash: str | None = None
    checked_at: datetime
