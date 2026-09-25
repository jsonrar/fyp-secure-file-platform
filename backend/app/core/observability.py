from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_REDACTED = "[REDACTED]"
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_SENSITIVE_NAME_RE = re.compile(
    r"(?i)(authorization|cookie|password|passphrase|secret|token|api[_-]?key|private[_-]?key|"
    r"plaintext|content|filename)"
)
_TEXT_REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
            re.IGNORECASE | re.DOTALL,
        ),
        "[REDACTED PRIVATE KEY]",
    ),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer [REDACTED]"),
    (
        re.compile(
            r"(?i)\b(password|passphrase|secret|token|api[_-]?key|private[_-]?key)\s*[:=]\s*"
            r"[^\s,;]+"
        ),
        r"\1=[REDACTED]",
    ),
)
_STANDARD_LOG_ATTRS = frozenset(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}
_ALLOWED_EXTRA_FIELDS = frozenset(
    {
        "event",
        "category",
        "outcome",
        "error_code",
        "method",
        "route",
        "status_code",
        "duration_ms",
        "request_id",
        "client_ip",
        "actor_role",
        "unit",
        "action",
        "result",
        "commit",
        "reason",
        "counter",
        "delta",
        "threshold",
    }
)


def redact_text(value: str) -> str:
    """Redact common credential material from a log string.

    Operational events should still use allow-listed structured fields and never pass request
    bodies, filenames, or user content here. This is a final defence for messages emitted by
    libraries and older call sites, not permission to log sensitive payloads.
    """

    redacted = value
    for pattern, replacement in _TEXT_REDACTIONS:
        redacted = pattern.sub(replacement, redacted)
    return redacted[:4096]


def _safe_extra_value(name: str, value: Any) -> str | int | float | bool | None:
    if _SENSITIVE_NAME_RE.search(name):
        return _REDACTED
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return redact_text(str(value))[:512]


class RedactingJsonFormatter(logging.Formatter):
    """One-line JSON formatter with a deliberately small extra-field allow-list."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        payload: dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": redact_text(record.getMessage()),
        }
        for name, value in record.__dict__.items():
            if name in _STANDARD_LOG_ATTRS or name not in _ALLOWED_EXTRA_FIELDS:
                continue
            payload[name] = _safe_extra_value(name, value)
        if record.exc_info:
            # Deliberately retain only the exception class. Tracebacks can contain local
            # variables or user-supplied values and therefore do not belong in the security log.
            exception_type = record.exc_info[0]
            if exception_type is not None:
                payload["exception_type"] = exception_type.__name__
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def configure_application_logging(level: str) -> None:
    """Install one redacting handler and disable raw Uvicorn request-line logging."""

    application_logger = logging.getLogger("app")
    application_logger.setLevel(level)
    application_logger.propagate = False
    for handler in list(application_logger.handlers):
        if getattr(handler, "_secureview_redacting_handler", False):
            application_logger.removeHandler(handler)
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(RedactingJsonFormatter())
    handler._secureview_redacting_handler = True  # type: ignore[attr-defined]
    application_logger.addHandler(handler)

    # Uvicorn's default access line contains the raw path *and query string*. Search terms can
    # contain a plaintext filename, so retain nginx's query-free access log instead and suppress
    # this duplicate source at application startup regardless of the service CLI flags.
    logging.getLogger("uvicorn.access").disabled = True


def emit_security_event(
    logger: logging.Logger,
    level: int,
    *,
    event: str,
    category: str,
    outcome: str,
    **fields: Any,
) -> None:
    extra: dict[str, Any] = {
        "event": event,
        "category": category,
        "outcome": outcome,
    }
    for name, value in fields.items():
        if name in _ALLOWED_EXTRA_FIELDS:
            extra[name] = value
    logger.log(level, event, extra=extra)


def _escape_metric_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


class SecurityMetrics:
    """Small in-process counters for operator polling; no user-controlled labels are accepted."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._http: Counter[tuple[str, str, str]] = Counter()
        self._events: Counter[tuple[str, str, str]] = Counter()
        self._duration_ms_sum = 0.0
        self._duration_count = 0

    def record_http(
        self,
        *,
        method: str,
        route: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        status_class = f"{status_code // 100}xx"
        with self._lock:
            self._http[(method, route, status_class)] += 1
            self._duration_ms_sum += duration_ms
            self._duration_count += 1

    def record_event(self, *, category: str, event: str, outcome: str) -> None:
        with self._lock:
            self._events[(category, event, outcome)] += 1

    def event_count(self, *, category: str, event: str, outcome: str) -> int:
        with self._lock:
            return self._events[(category, event, outcome)]

    def render_prometheus(self) -> str:
        with self._lock:
            http = dict(self._http)
            events = dict(self._events)
            duration_sum = self._duration_ms_sum
            duration_count = self._duration_count
        lines = [
            "# HELP secureview_http_requests_total HTTP requests by route template/status class.",
            "# TYPE secureview_http_requests_total counter",
        ]
        for (method, route, status_class), count in sorted(http.items()):
            labels = (
                f'method="{_escape_metric_label(method)}",'
                f'route="{_escape_metric_label(route)}",'
                f'status_class="{_escape_metric_label(status_class)}"'
            )
            lines.append(f"secureview_http_requests_total{{{labels}}} {count}")
        lines += [
            "# HELP secureview_security_events_total Security/operations events by category.",
            "# TYPE secureview_security_events_total counter",
        ]
        for (category, event, outcome), count in sorted(events.items()):
            labels = (
                f'category="{_escape_metric_label(category)}",'
                f'event="{_escape_metric_label(event)}",'
                f'outcome="{_escape_metric_label(outcome)}"'
            )
            lines.append(f"secureview_security_events_total{{{labels}}} {count}")
        lines += [
            "# HELP secureview_http_request_duration_ms_sum Sum of request durations.",
            "# TYPE secureview_http_request_duration_ms_sum counter",
            f"secureview_http_request_duration_ms_sum {duration_sum:.3f}",
            "# HELP secureview_http_request_duration_ms_count Number of request durations.",
            "# TYPE secureview_http_request_duration_ms_count counter",
            f"secureview_http_request_duration_ms_count {duration_count}",
        ]
        return "\n".join(lines) + "\n"


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return str(path) if path else "unmatched"


def _request_id(request: Request) -> str:
    candidate = request.headers.get("x-request-id", "")
    return candidate if _REQUEST_ID_RE.fullmatch(candidate) else uuid.uuid4().hex


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Collect bounded metrics and emit payload-free security events.

    The application intentionally does **not** parse ``X-Forwarded-For``. Production Uvicorn
    accepts proxy headers only from the loopback nginx peer; ``request.client`` is therefore the
    already-vetted address. See docs/OBSERVABILITY_AND_INCIDENT_RESPONSE.md.
    """

    def __init__(self, app, *, registry: SecurityMetrics) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self.registry = registry
        self.logger = logging.getLogger("app.security")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        started = time.monotonic()
        request_id = _request_id(request)
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = (time.monotonic() - started) * 1000
            route = _route_template(request)
            method = request.method.upper()
            status_code = response.status_code if response is not None else 500
            client_ip = request.client.host[:45] if request.client is not None else None
            self.registry.record_http(
                method=method,
                route=route,
                status_code=status_code,
                duration_ms=duration_ms,
            )
            if route.startswith("/api/v1/recovery"):
                outcome = "success" if status_code < 400 else "rejected"
                self.registry.record_event(
                    category="recovery",
                    event="operation",
                    outcome=outcome,
                )
                emit_security_event(
                    self.logger,
                    logging.INFO if outcome == "success" else logging.WARNING,
                    event="recovery_operation",
                    category="recovery",
                    outcome=outcome,
                    method=method,
                    route=route,
                    status_code=status_code,
                    request_id=request_id,
                    client_ip=client_ip,
                    duration_ms=round(duration_ms, 3),
                )
            if route.startswith("/api/v1/auth") and status_code == 429:
                self.registry.record_event(
                    category="auth",
                    event="rate_limited",
                    outcome="blocked",
                )
                emit_security_event(
                    self.logger,
                    logging.WARNING,
                    event="auth_rate_limited",
                    category="auth",
                    outcome="blocked",
                    method=method,
                    route=route,
                    status_code=status_code,
                    request_id=request_id,
                    client_ip=client_ip,
                )
            if response is None or status_code >= 500:
                self.registry.record_event(
                    category="http",
                    event="server_error",
                    outcome="failed",
                )
                emit_security_event(
                    self.logger,
                    logging.ERROR,
                    event="request_failed",
                    category="http",
                    outcome="failed",
                    method=method,
                    route=route,
                    status_code=status_code,
                    request_id=request_id,
                    client_ip=client_ip,
                )
            if response is not None:
                response.headers["X-Request-ID"] = request_id
