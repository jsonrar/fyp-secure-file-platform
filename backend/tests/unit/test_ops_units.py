"""Static checks on the server-only ops units and scripts (issues #57 and #59).

None of these files can be exercised in CI -- they drive systemd, docker and the staging
host's own paths -- so the facts the staging runbooks rely on are pinned here instead.
"""

from __future__ import annotations

import re
from pathlib import Path

SERVER = Path(__file__).resolve().parents[3] / "deployment" / "server"


def _read(name: str) -> str:
    return (SERVER / name).read_text(encoding="utf-8")


def _directives(name: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for line in _read(name).splitlines():
        if line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        found.setdefault(key.strip(), []).append(value.strip())
    return found


def test_reconcile_runs_as_the_app_account_on_the_real_storage_root() -> None:
    unit = _directives("mcs21-reconcile.service")

    assert unit["User"] == ["fypapp"] and unit["Group"] == ["fypapp"]
    assert unit["ReadWritePaths"] == ["/var/lib/fyp-secure-file-platform"]
    assert unit["EnvironmentFile"] == ["/etc/fyp-secure-file-platform/backend.env"]
    assert unit["ProtectSystem"] == ["strict"]
    assert unit["OnFailure"] == ["mcs21-alert@%n.service"]
    assert "mcs21-backup.service" in unit["After"][0].split()
    (exec_start,) = unit["ExecStart"]
    assert "scripts/reconcile.py --apply --max-deletions " in exec_start


def test_reconcile_refuses_to_start_without_a_recent_same_host_backup() -> None:
    (pre,) = _directives("mcs21-reconcile.service")["ExecStartPre"]

    assert pre.startswith("+/bin/sh -c ")
    assert "flock -w" in pre and "/run/lock/mcs21-backup.lock" in pre
    assert "/var/backups/mcs21-daily" in pre and "-mmin -180" in pre
    # `$$` is systemd's escape for a literal `$`; a bare `$(` would be expanded by systemd.
    assert "$$(find" in pre and re.search(r"(?<!\$)\$\(", pre) is None


def test_reconcile_timer_fires_after_the_daily_backup_window() -> None:
    timer = _directives("mcs21-reconcile.timer")

    assert timer["OnCalendar"] == ["*-*-* 05:00:00 Asia/Kuala_Lumpur"]
    assert "RandomizedDelaySec" not in timer


def test_every_ops_job_alerts_on_failure() -> None:
    for name in (
        "mcs21-reconcile.service",
        "mcs21-offsite-backup.service",
        "mcs21-observe.service",
        "mcs21-audit-checkpoint.service",
        "mcs21-backup.service.d/alert.conf",
        "mcs21-backup-verify.service.d/alert.conf",
    ):
        assert _directives(name).get("OnFailure") == ["mcs21-alert@%n.service"], name
    # The alert unit itself must not alert, or a broken mail setup would loop.
    assert "OnFailure" not in _directives("mcs21-alert@.service")


def test_the_alert_never_puts_the_api_key_on_a_command_line_or_journal_in_email() -> None:
    script = _read("mcs21-alert")

    assert (SERVER / "mcs21-alert").stat().st_mode & 0o111
    assert '--header @"$work/headers"' in script
    assert re.search(r"curl[^\n]*RESEND_API_KEY|curl[^\n]*\$api_key", script) is None
    assert "unset api_key" in script
    assert "source " not in script and "\n. " not in script
    assert "journalctl --no-pager --output" not in script
    assert "Journal output is intentionally withheld from email" in script
    assert "Inspect locally: sudo journalctl -u" in script


def test_observability_watcher_is_redacted_hardened_and_thresholded() -> None:
    unit = _directives("mcs21-observe.service")
    source = _read("mcs21-observe.service")
    timer = _directives("mcs21-observe.timer")

    assert unit["User"] == ["fypapp"] and unit["Group"] == ["fypapp"]
    assert unit["StateDirectory"] == ["mcs21-observe"]
    assert unit["ProtectSystem"] == ["strict"]
    assert unit["NoNewPrivileges"] == ["true"]
    assert unit["OnFailure"] == ["mcs21-alert@%n.service"]
    for expected in (
        "--max-auth-rate-limited 5",
        "--max-auth-failures 50",
        "--max-storage-failures 3",
        "--max-integrity-failures 3",
        "--max-unhandled-errors 3",
        "--max-disk-percent 85",
        "--max-checkpoint-age-seconds 7200",
    ):
        assert expected in source
    assert timer["OnCalendar"] == ["*:0/5"]
    assert timer["Persistent"] == ["true"]


def test_audit_checkpoint_key_stays_out_of_the_app_process() -> None:
    unit = _directives("mcs21-audit-checkpoint.service")
    source = _read("mcs21-audit-checkpoint.service")
    timer = _directives("mcs21-audit-checkpoint.timer")

    assert unit["User"] == ["root"] and unit["Group"] == ["root"]
    assert unit["ProtectSystem"] == ["strict"]
    assert unit["NoNewPrivileges"] == ["true"]
    assert unit["OnFailure"] == ["mcs21-alert@%n.service"]
    assert unit["EnvironmentFile"] == [
        "/etc/fyp-secure-file-platform/backup.env",
        "/etc/fyp-secure-file-platform/audit-checkpoint.env",
    ]
    assert "audit-checkpoint.key" in source
    assert "backend.env" not in source
    assert "--allow-local-dest" not in source
    assert timer["OnCalendar"] == ["*-*-* *:15:00"]
    assert timer["Persistent"] == ["true"]


def test_trusted_proxy_and_internal_metrics_stay_on_loopback() -> None:
    deploy = _read("mcs21-deploy")
    nginx = _read("nginx-secureview.conf")

    assert "--proxy-headers --forwarded-allow-ips=127.0.0.1" in deploy
    assert "--host 127.0.0.1" in deploy
    assert "--forwarded-allow-ips=*" not in deploy
    assert "proxy_pass http://127.0.0.1:8000" in nginx
    assert "/internal/metrics" not in nginx
    assert "location /internal" not in nginx


def test_backup_verify_derives_its_expectations() -> None:
    script = _read("mcs21-backup-verify")

    assert "0002_auth_identity_sessions" not in script
    assert "-m alembic heads" in script
    assert 'expected="$live_tables|$expected_version|1"' in script
    assert "CHECK TABLE" in script
