from __future__ import annotations

import base64
import json
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.file_schema import FileUploadMetadata, FolderNameIn

FILE_ID = UUID("11111111-1111-4111-8111-111111111111")
KEY_ID = UUID("22222222-2222-4222-8222-222222222222")
RECOVERY_KEY_ID = UUID("33333333-3333-4333-8333-333333333333")


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _metadata(**overrides: object) -> FileUploadMetadata:
    values: dict[str, object] = {
        "file_id": str(FILE_ID),
        "original_filename": "report.pdf",
        "plaintext_size": 5,
        "mime_type": "application/pdf",
        "encryption_algorithm": "AES-256-GCM",
        "envelope_version": 1,
        "aad_version": 1,
        "nonce": _b64(b"n" * 12),
        "auth_tag": _b64(b"t" * 16),
        "owner_key_id": str(KEY_ID),
        "key_wrapping_algorithm": "RSA-OAEP-SHA256",
        "wrapped_file_key": _b64(b"w" * 256),
        "recovery_key_id": str(RECOVERY_KEY_ID),
        "recovery_wrapped_file_key": _b64(b"r" * 256),
        "encrypted_manifest": _b64(b"manifest-ciphertext"),
    }
    values.update(overrides)
    return FileUploadMetadata.model_validate_json(json.dumps(values))


def test_upload_metadata_accepts_only_the_versioned_client_envelope() -> None:
    metadata = _metadata(mime_type="APPLICATION/PDF")

    assert metadata.file_id == FILE_ID
    assert metadata.mime_type == "application/pdf"
    assert metadata.nonce_bytes() == b"n" * 12
    assert metadata.auth_tag_bytes() == b"t" * 16
    assert metadata.wrapped_file_key_bytes() == b"w" * 256


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("original_filename", "../secret.txt"),
        ("original_filename", "line\nbreak.txt"),
        ("mime_type", "text/plain; charset=utf-8"),
        ("nonce", _b64(b"short")),
        ("auth_tag", _b64(b"short")),
        ("wrapped_file_key", _b64(b"short")),
        ("recovery_wrapped_file_key", _b64(b"short")),
        ("envelope_version", 2),
        ("encryption_algorithm", "AES-256-CBC"),
    ],
)
def test_upload_metadata_rejects_unsafe_or_unsupported_values(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        _metadata(**{field: value})


def test_upload_metadata_rejects_unknown_fields_and_noncanonical_base64() -> None:
    with pytest.raises(ValidationError):
        _metadata(server_private_key="must never be accepted")

    with pytest.raises(ValidationError):
        _metadata(nonce=f"{_b64(b'n' * 12)}\n")


def test_folder_name_is_normalized_and_rejects_path_syntax() -> None:
    assert FolderNameIn(name="  Coursework  ").name == "Coursework"

    for unsafe in ("..", "work/reports", "work\\reports", "line\nbreak"):
        with pytest.raises(ValidationError):
            FolderNameIn(name=unsafe)
