"""Poll SecureView's loopback health/metrics endpoints and fail on actionable deltas.

The monitor stores only numeric counters in its state file and prints only fixed metric names,
deltas, and thresholds. It never consumes request bodies, audit descriptions, filenames,
tokens, passphrases, private keys, or other user content.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

_METRIC_RE = re.compile(
    r'^secureview_security_events_total\{category="([^"]+)",event="([^"]+)",'
    r'outcome="([^"]+)"\}\s+([0-9]+(?:\.[0-9]+)?)$'
)

MetricKey = tuple[str, str, str]


@dataclass(frozen=True, slots=True)
class Threshold:
    key: MetricKey
    delta: int
    name: str


THRESHOLDS: tuple[Threshold, ...] = (
    Threshold(("auth", "rate_limited", "blocked"), 20, "auth_rate_limited_5m"),
    Threshold(("storage", "unavailable", "failed"), 1, "storage_unavailable"),
    Threshold(("storage", "integrity_rejected", "blocked"), 1, "integrity_rejected"),
    Threshold(("schema", "mismatch", "failed"), 1, "schema_mismatch"),
    Threshold(("database", "unavailable", "failed"), 1, "database_unavailable"),
    Threshold(("application", "unhandled", "failed"), 1, "unhandled_application_error"),
    Threshold(("recovery", "operation", "rejected"), 5, "recovery_rejections_5m"),
)


class MonitorError(Exception):
    pass


def parse_metrics(text: str) -> dict[MetricKey, int]:
    values: dict[MetricKey, int] = {}
    for line in text.splitlines():
        match = _METRIC_RE.fullmatch(line.strip())
        if match is None:
            continue
        category, event, outcome, value = match.groups()
        values[(category, event, outcome)] = int(float(value))
    return values


def evaluate_deltas(
    current: dict[MetricKey, int],
    previous: dict[MetricKey, int],
) -> list[dict[str, int | str]]:
    violations: list[dict[str, int | str]] = []
    for threshold in THRESHOLDS:
        current_value = current.get(threshold.key, 0)
        previous_value = previous.get(threshold.key, 0)
        # A backend restart resets in-memory counters. Treat that as a fresh baseline instead of
        # manufacturing a negative delta or replaying old failures.
        delta = current_value - previous_value if current_value >= previous_value else current_value
        if delta >= threshold.delta:
            violations.append(
                {
                    "counter": threshold.name,
                    "delta": delta,
                    "threshold": threshold.delta,
                }
            )
    return violations


def _read_json(url: str, timeout: float) -> dict[str, object]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read(64 * 1024)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise MonitorError(f"endpoint unavailable: {url}") from exc
    try:
        value = json.loads(body)
    except ValueError as exc:
        raise MonitorError(f"endpoint returned invalid JSON: {url}") from exc
    if not isinstance(value, dict):
        raise MonitorError(f"endpoint returned a non-object: {url}")
    return value


def _read_text(url: str, timeout: float) -> str:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.read(1024 * 1024).decode("utf-8", errors="strict")
    except (urllib.error.URLError, TimeoutError, OSError, UnicodeError) as exc:
        raise MonitorError(f"endpoint unavailable: {url}") from exc


def _load_state(path: Path) -> dict[MetricKey, int]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise MonitorError("monitor state is unreadable") from exc
    counters = payload.get("counters", {}) if isinstance(payload, dict) else {}
    if not isinstance(counters, dict):
        raise MonitorError("monitor state counters are invalid")
    result: dict[MetricKey, int] = {}
    for encoded, value in counters.items():
        parts = str(encoded).split("\t")
        if len(parts) != 3 or not isinstance(value, int) or value < 0:
            raise MonitorError("monitor state contains an invalid counter")
        result[(parts[0], parts[1], parts[2])] = value
    return result


def _save_state(path: Path, counters: dict[MetricKey, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
    checked_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    payload = {
        "checked_at_utc": checked_at,
        "counters": {"\t".join(key): value for key, value in sorted(counters.items())},
    }
    fd, temporary_name = tempfile.mkstemp(prefix=".ops-monitor-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o640)
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def run(*, base_url: str, state_path: Path, timeout: float) -> int:
    ready = _read_json(f"{base_url.rstrip('/')}/health/ready", timeout)
    if ready.get("status") != "ready":
        raise MonitorError(f"readiness failed: {ready.get('reason', 'unknown')}")
    metrics_url = f"{base_url.rstrip('/')}/internal/metrics"
    current = parse_metrics(_read_text(metrics_url, timeout))
    previous = _load_state(state_path)
    violations = evaluate_deltas(current, previous)
    _save_state(state_path, current)
    summary = {
        "event": "ops_monitor",
        "status": "alert" if violations else "ok",
        "violations": violations,
    }
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 1 if violations else 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--state",
        default="/var/lib/fyp-secure-file-platform/ops-monitor/state.json",
    )
    parser.add_argument("--timeout", type=float, default=5.0)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        return run(base_url=args.base_url, state_path=Path(args.state), timeout=args.timeout)
    except MonitorError as exc:
        print(
            json.dumps(
                {"event": "ops_monitor", "status": "failed", "reason": str(exc)},
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
