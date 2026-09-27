from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping

from starlette.responses import JSONResponse
from starlette.types import Message, Receive, Scope, Send

from app.api.responses import AUTH_NO_STORE_HEADERS

ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


class _BodyLimitExceeded(Exception):
    pass


class RequestBodyLimitMiddleware:
    """Bound request bodies before JSON parsing or multipart spooling can exhaust resources."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_upload_bytes: int,
        upload_path: str,
        max_body_bytes: int,
        extra_upload_limits: Mapping[str, int] | None = None,
    ) -> None:
        if max_body_bytes <= 0:
            raise ValueError("max_body_bytes must be positive")
        if max_upload_bytes <= 0:
            raise ValueError("max_upload_bytes must be positive")
        extra = {
            (path.rstrip("/") or "/"): limit
            for path, limit in (extra_upload_limits or {}).items()
        }
        if any(limit <= 0 for limit in extra.values()):
            raise ValueError("every extra upload limit must be positive")
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.max_upload_bytes = max_upload_bytes
        self.upload_path = upload_path.rstrip("/") or "/"
        # Paths that take a multipart body but nothing like an encrypted file. An avatar
        # needs more than the JSON ceiling and far less than the ciphertext ceiling, and
        # giving it the ciphertext ceiling would let one profile request spool 500 MiB.
        self.extra_upload_limits = extra

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        max_bytes, refusal = self._limit_for(scope)
        content_length = self._content_length(scope)
        if content_length is not None and content_length > max_bytes:
            await self._reject(scope, receive, send, message=refusal)
            return

        consumed = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal consumed
            message = await receive()
            if message["type"] == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > max_bytes:
                    raise _BodyLimitExceeded
            return message

        async def tracked_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except _BodyLimitExceeded:
            if response_started:  # pragma: no cover - multipart is parsed before routing
                raise
            await self._reject(scope, receive, send, message=refusal)

    def _limit_for(self, scope: Scope) -> tuple[int, str]:
        """The ceiling for this path, and what to say when a body crosses it.

        Each route gets its own wording because the three ceilings are orders of magnitude
        apart, and "too large" against the wrong one sends the caller looking at the wrong
        setting.
        """
        path = (scope.get("path") or "/").rstrip("/") or "/"
        extra_limit = self.extra_upload_limits.get(path)
        if extra_limit is not None:
            return extra_limit, "The uploaded image is too large"
        if path == self.upload_path:
            return self.max_upload_bytes, "The encrypted upload request is too large"
        return self.max_body_bytes, "The request body is too large"

    def _content_length(self, scope: Scope) -> int | None:
        for raw_name, raw_value in scope.get("headers", ()):
            if raw_name.lower() != b"content-length":
                continue
            try:
                value = int(raw_value)
            except ValueError:
                return None
            return max(value, 0)
        return None

    @staticmethod
    async def _reject(
        scope: Scope,
        receive: Receive,
        send: Send,
        *,
        message: str,
    ) -> None:
        response = JSONResponse(
            status_code=413,
            headers=AUTH_NO_STORE_HEADERS,
            content={
                "success": False,
                "status": "fail",
                "message": message,
                "data": {"error_code": "request_too_large", "details": None},
                "description": None,
                "code": 413,
            },
        )
        await response(scope=scope, receive=receive, send=send)
