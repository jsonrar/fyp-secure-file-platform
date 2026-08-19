from __future__ import annotations

import unicodedata
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.enums import SessionStatus, SystemRole, UserStatus


class _AuthRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _AuthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


def _normalize_password(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    return value


def _normalize_username(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def _validate_username(value: str) -> str:
    allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")
    if any(char not in allowed_chars for char in value):
        raise ValueError("Username can only contain letters, numbers, underscore, dot, and hyphen")
    return value


class AuthUserResponse(_AuthResponse):
    id: UUID
    username: str
    role: SystemRole
    status: UserStatus
    created_at: datetime
    last_login_at: datetime | None = None


class UserRegisterRequest(_AuthRequest):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=15, max_length=128, repr=False)

    _strip_username = field_validator("username", mode="before")(_normalize_username)
    _check_username = field_validator("username")(_validate_username)
    _normalize_password = field_validator("password", mode="before")(_normalize_password)

    @model_validator(mode="before")
    @classmethod
    def discard_legacy_email(cls, value: Any) -> Any:
        """Keep the untouched demo frontend working while removing email from the contract."""
        if isinstance(value, dict) and "email" in value:
            value = {key: item for key, item in value.items() if key != "email"}
        return value


class UserRegisterResponse(_AuthResponse):
    user: AuthUserResponse
    key_id: UUID
    public_key_fingerprint: str


class UserLoginRequest(_AuthRequest):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=1, max_length=128, repr=False)

    _strip_username = field_validator("username", mode="before")(_normalize_username)
    _check_username = field_validator("username")(_validate_username)
    _normalize_password = field_validator("password", mode="before")(_normalize_password)


class UserLoginResponse(_AuthResponse):
    user: AuthUserResponse
    access_token: str = Field(repr=False)
    refresh_token: str = Field(repr=False)
    token_type: Literal["bearer"] = "bearer"
    access_expires_at: datetime
    refresh_expires_at: datetime
    session_id: UUID


class AuthRefreshRequest(_AuthRequest):
    refresh_token: str = Field(min_length=1, max_length=512, repr=False)


class AuthRefreshResponse(_AuthResponse):
    access_token: str = Field(repr=False)
    refresh_token: str = Field(repr=False)
    token_type: Literal["bearer"] = "bearer"
    access_expires_at: datetime
    refresh_expires_at: datetime
    session_id: UUID


class AuthMeResponse(_AuthResponse):
    user: AuthUserResponse


class UserLogoutResponse(_AuthResponse):
    logged_out: bool = True


class UserLogoutAllResponse(_AuthResponse):
    revoked_sessions: int = Field(ge=0)


class ChangePasswordRequest(_AuthRequest):
    current_password: str = Field(min_length=1, max_length=128, repr=False)
    new_password: str = Field(min_length=15, max_length=128, repr=False)

    _normalize_current_password = field_validator("current_password", mode="before")(
        _normalize_password
    )
    _normalize_new_password = field_validator("new_password", mode="before")(_normalize_password)


class ChangePasswordResponse(_AuthResponse):
    password_changed: bool = True
    revoked_sessions: int = Field(ge=0)
    reauthentication_required: bool = True


class AuthSessionResponse(_AuthResponse):
    session_id: UUID = Field(validation_alias=AliasChoices("session_id", "id", "session_uuid"))
    status: SessionStatus
    current: bool
    created_at: datetime
    access_expires_at: datetime
    absolute_expires_at: datetime
    ip_address: str | None = None
    user_agent: str | None = None
    revoked_at: datetime | None = None


class AuthSessionListResponse(_AuthResponse):
    sessions: list[AuthSessionResponse]


class AuthSessionRevokeResponse(_AuthResponse):
    session_id: UUID
    revoked: bool = True
