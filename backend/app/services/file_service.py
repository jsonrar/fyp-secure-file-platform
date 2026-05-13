from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.services.crypto_service import CryptoService
from app.utils.file_utils import ensure_dir, sha256_file


class FileService:
    def __init__(self):
        self.crypto = CryptoService()

    def encrypt_uploaded_bytes_draft(self, filename: str, content: bytes) -> dict:
        """Draft upload encryption flow.

        Real implementation should save metadata and wrapped keys into database.
        """
        ensure_dir(settings.ENCRYPTED_FILE_DIR)
        result = self.crypto.encrypt_bytes(content)
        stored_filename = f"{uuid4().hex}.enc"
        storage_path = Path(settings.ENCRYPTED_FILE_DIR) / stored_filename
        storage_path.write_bytes(result.ciphertext)

        return {
            "original_filename": filename,
            "stored_filename": stored_filename,
            "storage_path": str(storage_path),
            "iv_hex": result.iv.hex(),
            "auth_tag_hex": result.auth_tag.hex(),
            "encrypted_sha256": sha256_file(storage_path),
            "file_key_hex_for_demo_only": result.file_key.hex(),
        }
