from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# =========================================================
# Shared Auth/User DTOs
# =========================================================

class AuthUserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: Literal["USER", "ADMIN", "RECOVERY_OFFICER"]
    status: Literal["ACTIVE", "DISABLED", "DELETED"]
    email_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }


class AuthSessionResponse(BaseModel):
    token_type: str = "bearer"
    access_token: str
    expires_at: datetime


# =========================================================
# Register
# =========================================================

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Username is required")

        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")
        if any(char not in allowed_chars for char in value):
            raise ValueError(
                "Username can only contain letters, numbers, underscore, dot, and hyphen"
            )

        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> EmailStr:
        return value.lower()


class UserRegisterResponse(BaseModel):
    user: AuthUserResponse
    private_key_pem: str
    private_key_filename: str
    message: str = (
        "Registration successful. Please download and store your private key securely. "
        "The platform does not permanently store your private key."
    )


# =========================================================
# Login
# =========================================================

class UserLoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip()


class UserLoginResponse(BaseModel):
    user: AuthUserResponse
    session: AuthSessionResponse


# =========================================================
# OAuth2-compatible token response
# Used by Swagger Authorize button if needed.
# =========================================================

class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


# =========================================================
# Current User / Me
# =========================================================

class AuthMeResponse(BaseModel):
    user: AuthUserResponse


# =========================================================
# Logout
# =========================================================

class UserLogoutResponse(BaseModel):
    logged_out: bool = True
    message: str = "Logout successful"


# =========================================================
# Session Validation
# =========================================================

class AuthSessionValidateResponse(BaseModel):
    valid: bool
    user: Optional[AuthUserResponse] = None
    expires_at: Optional[datetime] = None