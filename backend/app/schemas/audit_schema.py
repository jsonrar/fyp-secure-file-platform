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
    # The names cost nothing: the router already has both User rows joined in hand, and a
    # UUID cannot be read by the person looking at their own history. Without them the page
    # can only say "someone", which is the one thing an audit trail must not say.
    actor_username: str | None = None
    target_user_id: UUID | None = None
    target_username: str | None = None
    result: str
    description: str | None = None
    metadata: dict[str, Any]
    created_at: datetime
    # For a row about a file: its original name, and whether the file has since been deleted. A
    # deleted file is a soft delete, so the name is still known; the page labels it "Deleted"
    # instead of asking the file endpoint (which answers 404 for it) one file at a time.
    file_name: str | None = None
    file_deleted: bool = False


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
