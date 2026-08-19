from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import SystemRole, UserStatus


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AdminUserOut(_StrictModel):
    user_id: UUID
    username: str
    role: SystemRole
    status: UserStatus
    created_at: datetime
    last_login_at: datetime | None = None


class AdminUserListResponse(_StrictModel):
    users: list[AdminUserOut]
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    has_more: bool


class AdminFileOut(_StrictModel):
    file_id: UUID
    owner_id: UUID
    owner_username: str
    original_filename: str
    mime_type: str | None = None
    file_size: int
    encrypted_size: int | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class AdminFileListResponse(_StrictModel):
    files: list[AdminFileOut]
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    has_more: bool


class AdminUserStatusResponse(_StrictModel):
    user_id: UUID
    status: UserStatus
    changed: bool
    revoked_sessions: int = Field(ge=0)
