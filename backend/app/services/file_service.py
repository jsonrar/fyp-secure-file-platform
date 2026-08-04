from typing import NoReturn

from app.domain.errors import FeatureNotImplementedError


class FileService:
    def encrypt_uploaded_bytes_draft(
        self,
        filename: str,
        content: bytes,
    ) -> NoReturn:
        """Fail closed until storage staging, key wrapping, and DB UoW exist."""
        raise FeatureNotImplementedError()
