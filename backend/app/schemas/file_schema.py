from uuid import UUID

from pydantic import BaseModel


class FileOut(BaseModel):
    file_id: UUID
    original_filename: str
    file_size: int
    status: str


class IntegrityCheckOut(BaseModel):
    file_id: UUID
    status: str
    expected_hash: str | None = None
    actual_hash: str | None = None
