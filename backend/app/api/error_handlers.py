import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.responses import AUTH_NO_STORE_HEADERS, error, fail
from app.domain.errors import (
    AppError,
    AuthenticationError,
    AuthenticationRateLimitedError,
    AuthorizationError,
    ConflictError,
    EmailDeliveryFailedError,
    FileTooLargeError,
    InputError,
    IntegrityVerificationError,
    ResourceNotFoundError,
    StorageUnavailableError,
)

logger = logging.getLogger(__name__)

_STATUS_BY_ERROR_TYPE: dict[type[AppError], int] = {
    AuthenticationRateLimitedError: 429,
    AuthenticationError: 401,
    AuthorizationError: 403,
    ResourceNotFoundError: 404,
    ConflictError: 409,
    FileTooLargeError: 413,
    InputError: 422,
    StorageUnavailableError: 503,
    EmailDeliveryFailedError: 503,
    IntegrityVerificationError: 409,
}


def _response_headers(request: Request, error_value: AppError | None = None) -> dict[str, str]:
    headers: dict[str, str] = {}
    app_settings = getattr(request.app.state, "settings", None)
    api_prefix = getattr(app_settings, "API_PREFIX", "/api/v1").rstrip("/")
    sensitive_prefixes = tuple(
        f"{api_prefix}/{segment}"
        for segment in ("auth", "keys", "files", "audit-logs", "recovery", "admin")
    )
    route = request.scope.get("route")
    route_tags = getattr(route, "tags", ())
    is_sensitive_route = bool(
        {"Auth", "Keys", "Files", "Sharing", "Recovery", "Audit Logs", "Admin"}.intersection(
            route_tags
        )
    )
    is_sensitive_path = any(
        request.url.path == prefix or request.url.path.startswith(f"{prefix}/")
        for prefix in sensitive_prefixes
    )
    if is_sensitive_route or is_sensitive_path:
        headers.update(AUTH_NO_STORE_HEADERS)
    if error_value is not None:
        headers.update(error_value.headers)
    return headers


def _status_for(error_value: AppError) -> int:
    for error_type, status_code in _STATUS_BY_ERROR_TYPE.items():
        if isinstance(error_value, error_type):
            return status_code
    return 400


def _safe_validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    """Return useful validation details without echoing secret request input."""
    return [
        {
            "location": list(item.get("loc", ())),
            "message": item.get("msg", "Invalid value"),
            "type": item.get("type", "value_error"),
        }
        for item in exc.errors()
    ]


def register_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return fail(
            message=exc.message,
            data={"error_code": exc.code, "details": exc.details},
            code=_status_for(exc),
            headers=_response_headers(request, exc),
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return fail(
            message="Request validation failed",
            data={
                "error_code": "request_validation_failed",
                "details": _safe_validation_errors(exc),
            },
            code=422,
            headers=_response_headers(request),
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled application error",
            extra={
                "error_type": type(exc).__name__,
                "method": request.method,
                "path": request.url.path,
            },
        )
        return error(
            message="Internal server error",
            data={"error_code": "internal_error"},
            code=500,
            headers=_response_headers(request),
        )
