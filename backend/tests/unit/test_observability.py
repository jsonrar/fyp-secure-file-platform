from __future__ import annotations

import io
import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.observability import (
    ObservabilityMiddleware,
    RedactingJsonFormatter,
    SecurityMetrics,
    redact_text,
)
from app.services.email_service import EmailService, OutboundEmail


def test_redacting_formatter_never_emits_credentials_or_private_key() -> None:
    formatter = RedactingJsonFormatter()
    record = logging.LogRecord(
        name="app.test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg=(
            "Authorization: Bearer abc.def.ghi password=hunter2 "
            "-----BEGIN PRIVATE KEY-----top-secret-----END PRIVATE KEY-----"
        ),
        args=(),
        exc_info=None,
    )
    record.event = "test_event"
    record.category = "security"
    record.outcome = "failed"
    record.content = "plaintext file contents"
    record.filename = "secret-plan.txt"

    rendered = formatter.format(record)

    assert "abc.def.ghi" not in rendered
    assert "hunter2" not in rendered
    assert "top-secret" not in rendered
    assert "plaintext file contents" not in rendered
    assert "secret-plan.txt" not in rendered
    payload = json.loads(rendered)
    assert payload["event"] == "test_event"
    assert payload["message"].count("[REDACTED]") >= 2


def test_redact_text_covers_secret_assignment_and_bearer_token() -> None:
    value = redact_text("token=abc123 Bearer xyz789 passphrase:correct-horse")
    assert "abc123" not in value
    assert "xyz789" not in value
    assert "correct-horse" not in value


def test_metrics_use_route_templates_not_user_values() -> None:
    registry = SecurityMetrics()
    registry.record_http(
        method="GET",
        route="/api/v1/files/{file_id}",
        status_code=409,
        duration_ms=12.5,
    )
    registry.record_event(category="storage", event="integrity_rejected", outcome="blocked")

    rendered = registry.render_prometheus()

    assert "/api/v1/files/{file_id}" in rendered
    assert "storage" in rendered
    assert "integrity_rejected" in rendered
    assert "private-file-name.txt" not in rendered


def test_recovery_middleware_records_only_template_and_returns_request_id() -> None:
    app = FastAPI()
    registry = SecurityMetrics()
    app.add_middleware(ObservabilityMiddleware, registry=registry)

    @app.post("/api/v1/recovery/{request_id}/approve")
    def approve(request_id: str):
        return {"request_id": request_id}

    client = TestClient(app)
    response = client.post(
        "/api/v1/recovery/private-user-supplied-id/approve",
        headers={"X-Request-ID": "safe-request-id"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "safe-request-id"
    metrics = registry.render_prometheus()
    assert "private-user-supplied-id" not in metrics
    assert "/api/v1/recovery/{request_id}/approve" in metrics
    assert registry.event_count(category="recovery", event="operation", outcome="success") == 1


def test_console_email_log_suppresses_recipient_subject_and_body() -> None:
    settings = Settings(APP_ENV="test", EMAIL_PROVIDER="console")
    service = EmailService(settings)
    message = OutboundEmail(
        to_address="secret-recipient@example.test",
        subject="Password reset for confidential-account",
        text_body="verification code 123456 and private filename payroll.xlsx",
    )
    logger = logging.getLogger("app.services.email_service")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger.addHandler(handler)
    previous_level = logger.level
    logger.setLevel(logging.WARNING)
    try:
        service.send(message)
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)

    rendered = stream.getvalue()
    assert "secret-recipient@example.test" not in rendered
    assert "confidential-account" not in rendered
    assert "123456" not in rendered
    assert "payroll.xlsx" not in rendered
    assert "message suppressed" in rendered
