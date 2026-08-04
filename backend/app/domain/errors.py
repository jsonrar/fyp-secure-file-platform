from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar


class AppError(Exception):
    """Expected application failure that is safe to translate at the API edge."""

    code: ClassVar[str] = "application_error"
    public_message: ClassVar[str] = "The request could not be completed"
    default_headers: ClassVar[Mapping[str, str]] = {}

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.message = message or self.public_message
        self.details = details
        self.headers = {**self.default_headers, **(headers or {})}
        super().__init__(self.message)


class AuthenticationError(AppError):
    code = "authentication_required"
    public_message = "Authentication is required"
    default_headers: ClassVar[Mapping[str, str]] = {"WWW-Authenticate": "Bearer"}


class InvalidCredentialsError(AuthenticationError):
    code = "invalid_credentials"
    public_message = "Invalid username or password"


class InvalidRefreshTokenError(AuthenticationError):
    code = "invalid_refresh_token"
    public_message = "The refresh token is invalid or expired"


class AuthorizationError(AppError):
    code = "access_denied"
    public_message = "You do not have permission to perform this action"


class ResourceNotFoundError(AppError):
    code = "resource_not_found"
    public_message = "The requested resource was not found"


class ConflictError(AppError):
    code = "conflict"
    public_message = "The request conflicts with the current resource state"


class AccountIdentifierUnavailableError(ConflictError):
    code = "account_identifier_unavailable"
    public_message = "The username or email is unavailable"


class InputError(AppError):
    code = "invalid_input"
    public_message = "The request input is invalid"


class PasswordUnchangedError(InputError):
    code = "password_unchanged"
    public_message = "The new password must be different from the current password"


class WeakPasswordError(InputError):
    code = "weak_password"
    public_message = "The password does not meet the security requirements"


class InvalidCurrentPasswordError(InputError):
    code = "invalid_current_password"
    public_message = "The current password is invalid"


class SessionNotFoundError(ResourceNotFoundError):
    code = "session_not_found"
    public_message = "The requested session was not found"


class AuthenticationRateLimitedError(AppError):
    code = "auth_rate_limited"
    public_message = "Too many authentication attempts; please try again later"

    def __init__(
        self,
        message: str | None = None,
        *,
        retry_after_seconds: int | None = None,
        details: dict[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        response_headers = dict(headers or {})
        if retry_after_seconds is not None:
            response_headers["Retry-After"] = str(max(0, retry_after_seconds))
        super().__init__(message, details=details, headers=response_headers)


class FeatureNotImplementedError(AppError):
    code = "feature_not_implemented"
    public_message = "This API feature has not been implemented yet"
