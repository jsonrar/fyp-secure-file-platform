from uuid import UUID

from pydantic import BaseModel


class RecoveryRequestCreate(BaseModel):
    file_id: UUID
    reason: str


class RecoveryExecuteRequest(BaseModel):
    recovery_private_key_pem: str
