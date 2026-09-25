from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = BACKEND_ROOT / "scripts"


def _load(name: str):
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


checkpoint = _load("audit_checkpoint")
monitor = _load("ops_monitor")
KEY = b"k" * 32
NOW = datetime(2026, 9, 25, 3, 0, tzinfo=UTC)


def _record(log_id: int, when: datetime = NOW):
    return checkpoint.build_record(
        last_log_id=log_id,
        current_hash="a" * 64,
        schema_revision="0006_chacha20_poly1305",
        created_at=when,
        key=KEY,
    )


def test_checkpoint_hmac_round_trip_and_tamper_rejection() -> None:
    record = _record(42)

    payload = checkpoint.verify_record(record, KEY)
    assert payload["last_log_id"] == 42
    assert set(payload) == {
        "format",
        "created_at_utc",
        "last_log_id",
        "current_hash",
        "schema_revision",
    }

    record["payload"]["last_log_id"] = 43
    with pytest.raises(checkpoint.CheckpointError, match="HMAC"):
        checkpoint.verify_record(record, KEY)


def test_checkpoint_contains_no_application_payload_fields() -> None:
    encoded = json.dumps(_record(7), sort_keys=True)
    forbidden = [
        "filename",
        "plaintext",
        "passphrase",
        "private_key",
        "token",
        "email",
        "description",
        "metadata",
    ]
    assert all(name not in encoded.lower() for name in forbidden)


def test_checkpoint_directory_verification_rejects_rollback(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("AUDIT_CHECKPOINT_HMAC_KEY", KEY.decode())
    newer_time = NOW + timedelta(hours=1)
    first = tmp_path / "audit-checkpoint-20260925T030000Z-10.json"
    second = tmp_path / "audit-checkpoint-20260925T040000Z-9.json"
    first.write_text(json.dumps(_record(10, NOW)), encoding="utf-8")
    second.write_text(json.dumps(_record(9, newer_time)), encoding="utf-8")

    with pytest.raises(checkpoint.CheckpointError, match="moved backwards"):
        checkpoint.verify_path(tmp_path)


def test_local_checkpoint_publish_uses_private_permissions(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    source.write_text("{}\n", encoding="utf-8")
    destination = tmp_path / "remote"

    location = checkpoint.publish_file(source, str(destination))

    copied = Path(location)
    assert copied.read_text(encoding="utf-8") == "{}\n"
    assert copied.stat().st_mode & 0o777 == 0o600


def test_monitor_parses_only_fixed_security_counter_shape() -> None:
    text = """
# HELP secureview_security_events_total x
secureview_security_events_total{category="auth",event="rate_limited",outcome="blocked"} 25
secureview_http_requests_total{method="GET",route="/secret",status_class="2xx"} 99
"""
    values = monitor.parse_metrics(text)
    assert values == {("auth", "rate_limited", "blocked"): 25}


def test_monitor_thresholds_use_deltas_and_handle_counter_reset() -> None:
    key = ("auth", "rate_limited", "blocked")
    violations = monitor.evaluate_deltas({key: 25}, {key: 4})
    assert violations == [{"counter": "auth_rate_limited_5m", "delta": 21, "threshold": 20}]

    # Process restart/reset: current < previous, so current becomes the fresh-window delta.
    assert monitor.evaluate_deltas({key: 3}, {key: 100}) == []


def test_monitor_state_contains_only_numeric_counters(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    counters = {("storage", "unavailable", "failed"): 2}
    monitor._save_state(state, counters)

    payload = json.loads(state.read_text(encoding="utf-8"))
    assert payload["counters"] == {"storage\tunavailable\tfailed": 2}
    assert state.stat().st_mode & 0o777 == 0o640
    assert monitor._load_state(state) == counters
    assert "secret" not in state.read_text(encoding="utf-8").lower()
