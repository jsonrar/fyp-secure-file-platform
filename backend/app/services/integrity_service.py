from app.utils.file_utils import sha256_file


class IntegrityService:
    def check_file_hash(self, storage_path: str, expected_sha256: str) -> dict:
        actual = sha256_file(storage_path)
        return {
            "status": "VALID" if actual == expected_sha256 else "MODIFIED",
            "expected_hash": expected_sha256,
            "actual_hash": actual,
        }
