from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AuditLogOut(_StrictModel):
    action: str
    resource_type: str
    resource_id: str | None = None
    actor_user_id: UUID | None = None
    target_user_id: UUID | None = None
    result: str
    description: str | None = None
    metadata: dict[str, Any]
    created_at: datetime


class AuditLogListResponse(_StrictModel):
    logs: list[AuditLogOut]
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    has_more: bool


class FileAuditLogListResponse(AuditLogListResponse):
    file_id: UUID


class AuditChainVerificationResponse(_StrictModel):
    status: str
    valid: bool
    checked_entries: int = Field(ge=0)
    first_invalid_position: int | None = Field(default=None, ge=1)
