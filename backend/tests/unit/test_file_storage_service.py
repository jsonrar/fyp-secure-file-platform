from __future__ import annotations

import asyncio
from io import BytesIO
from uuid import UUID

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.config import Settings
from app.domain.errors import FileEnvelopeInvalidError, FileTooLargeError
from app.services.file_storage_service import FileStorageService, StorageObjectError

FILE_ID = UUID("11111111-1111-4111-8111-111111111111")
OBJECT_ID = UUID("22222222-2222-4222-8222-222222222222")


def _settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        APP_ENV="test",
        APP_DEBUG=False,
        SECRET_KEY="test-secret-key-that-is-long-enough",
        TEMP_FILE_DIR=tmp_path / "staging",
        ENCRYPTED_FILE_DIR=tmp_path / "objects",
    )


def _upload(content: bytes, media_type: str = "application/octet-stream") -> UploadFile:
    return UploadFile(
        filename="ciphertext.bin",
        file=BytesIO(content),
        headers=Headers({"content-type": media_type}),
    )


def test_storage_stages_hashes_publishes_and_streams_ciphertext(tmp_path) -> None:
    storage = FileStorageService(settings=_settings(tmp_path))
    ciphertext = b"already encrypted bytes"

    staged = asyncio.run(storage.stage_upload(_upload(ciphertext), max_size_bytes=1024))
    object_key = storage.allocate_object_key(FILE_ID, random_id=OBJECT_ID)
    storage.publish(staged, object_key)

    verified = storage.open_verified(object_key)
    assert verified.size_bytes == len(ciphertext)
    assert b"".join(verified.iter_chunks(3)) == ciphertext

    storage.delete_object(object_key)
    storage.delete_object(object_key)


def test_storage_rejects_oversized_or_non_ciphertext_uploads_without_staging_leaks(
    tmp_path,
) -> None:
    storage = FileStorageService(settings=_settings(tmp_path))

    with pytest.raises(FileTooLargeError):
        asyncio.run(storage.stage_upload(_upload(b"too large"), max_size_bytes=3))
    assert list(storage.staging_root.glob("*")) == []

    with pytest.raises(FileEnvelopeInvalidError):
        asyncio.run(storage.stage_upload(_upload(b"ciphertext", "text/plain"), max_size_bytes=99))


def test_storage_rejects_path_traversal_object_keys(tmp_path) -> None:
    storage = FileStorageService(settings=_settings(tmp_path))

    with pytest.raises(StorageObjectError):
        storage.delete_object("../outside")


def test_publish_removes_new_object_when_directory_sync_fails(tmp_path, monkeypatch) -> None:
    storage = FileStorageService(settings=_settings(tmp_path))
    staged = asyncio.run(storage.stage_upload(_upload(b"ciphertext"), max_size_bytes=99))
    object_key = storage.allocate_object_key(FILE_ID, random_id=OBJECT_ID)

    def fail_sync(_path) -> None:
        raise OSError("simulated directory sync failure")

    monkeypatch.setattr(storage, "_sync_directory", fail_sync)

    with pytest.raises(StorageObjectError):
        storage.publish(staged, object_key)

    assert not storage._object_path(object_key).exists()
