"""Gathering the evidence for the security agent: the right window, the right grouping, no write."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy.dialects import mysql

from app.domain.auth import ActorContext
from app.domain.enums import SystemRole, UserStatus
from app.domain.errors import AuthorizationError
from app.repositories.agent_repository import (
    AgentRepository,
    AuditEventRow,
    DamagedFileHistory,
)
from app.services.security_agent_service import (
    BOUNDARIES,
    SecurityAgentService,
    current_failure_run,
)

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)
NAIVE_NOW = NOW.replace(tzinfo=None)


def _actor(role: SystemRole = SystemRole.ADMIN) -> ActorContext:
    return ActorContext(
        user_id=7,
        user_public_id=UUID("22222222-2222-4222-8222-222222222222"),
        session_id=8,
        session_public_id=UUID("33333333-3333-4333-8333-333333333333"),
        role=role,
        status=UserStatus.ACTIVE,
        access_token_hash="a" * 64,
    )


class FakeAgentRepository:
    def __init__(self, events=(), histories=(), pending_old=0) -> None:
        self.events = list(events)
        self.histories = list(histories)
        self.pending_old = pending_old
        self.asked: dict = {}

    def audit_events(self, actions, *, since):
        self.asked["actions"] = set(actions)
        self.asked["since"] = since
        return [e for e in self.events if e.action in actions and e.created_at >= since]

    def count_recovery_requests_pending_before(self, cutoff):
        self.asked["recovery_cutoff"] = cutoff
        return self.pending_old

    def damaged_file_histories(self, *, limit):
        return self.histories[:limit]


class FakeAdminRepository:
    def __init__(self, last_sweep=NAIVE_NOW - timedelta(hours=2), candidates=5, never=0) -> None:
        self.value = (candidates, never, 3, last_sweep)

    def integrity_coverage(self, since):
        return self.value


class FakeAuditQuery:
    def __init__(self, valid=True, position=None, checked=120) -> None:
        self.result = {
            "valid": valid,
            "status": "VALID" if valid else "INVALID",
            "checked_entries": checked,
            "first_invalid_position": position,
        }

    def verify_chain(self, *, actor):
        return self.result


def _service(repository=None, admin=None, audit=None) -> SecurityAgentService:
    return SecurityAgentService(
        db=SimpleNamespace(),
        repository=repository or FakeAgentRepository(),
        admin_repository=admin or FakeAdminRepository(),
        audit_query=audit or FakeAuditQuery(),
        clock=lambda: NOW,
    )


def _failures(count, *, ip="203.0.113.9", user="alice", seconds=10):
    return [
        AuditEventRow(
            "AUTH_LOGIN_FAILED",
            NAIVE_NOW - timedelta(minutes=30) + timedelta(seconds=seconds * i),
            user,
            ip,
        )
        for i in range(count)
    ]


def test_only_an_administrator_can_ask_and_nothing_is_read_for_anyone_else() -> None:
    class Untouchable:
        def __getattr__(self, name):
            raise AssertionError(f"{name} must not be called for a non-administrator")

    service = SecurityAgentService(
        db=SimpleNamespace(),
        repository=Untouchable(),
        admin_repository=Untouchable(),
        audit_query=Untouchable(),
        clock=lambda: NOW,
    )

    for role in (SystemRole.USER, SystemRole.RECOVERY_OFFICER):
        with pytest.raises(AuthorizationError):
            service.report(actor=_actor(role), window_hours=24)


def test_a_quiet_platform_gives_an_empty_report_that_still_shows_what_was_read() -> None:
    report = _service().report(actor=_actor(), window_hours=24)

    assert report.findings == []
    assert report.counts.model_dump() == {"critical": 0, "high": 0, "medium": 0, "low": 0}
    assert report.inputs.audit_events_read == 0
    assert report.inputs.files_checkable == 5 and report.inputs.audit_chain_entries_verified == 120
    assert report.inputs.last_scan_at is not None
    assert len(report.rules) == 10 and all(rule.findings == 0 for rule in report.rules)
    assert report.boundaries == BOUNDARIES


def test_the_window_is_measured_back_from_now_and_only_watched_events_are_requested() -> None:
    repository = FakeAgentRepository()

    _service(repository).report(actor=_actor(), window_hours=48)

    assert repository.asked["since"] == (NOW - timedelta(hours=48)).replace(tzinfo=None)
    assert repository.asked["actions"] == {
        "AUTH_LOGIN_FAILED",
        "AUTH_REFRESH_REPLAY_DETECTED",
        "FILE_DOWNLOAD_AUTHORIZED",
        "FILE_SHARED",
        "AUTH_PASSWORD_CHANGE_FAILED",
        "RECOVERY_REQUEST_EXECUTED",
    }
    assert repository.asked["recovery_cutoff"] == (NOW - timedelta(hours=24)).replace(tzinfo=None)


def test_a_burst_of_failed_sign_ins_becomes_a_ranked_finding_with_an_action() -> None:
    report = _service(FakeAgentRepository(events=_failures(14))).report(
        actor=_actor(), window_hours=24
    )

    assert report.counts.medium == 2
    source = next(f for f in report.findings if f.rule_id == "LOGIN_GUESSING_SOURCE")
    assert source.priority == "MEDIUM" and "203.0.113.9" in source.title
    assert "fail2ban" in source.recommended_action
    assert report.inputs.audit_events_read == 14


def test_events_outside_the_window_are_ignored() -> None:
    old = [
        AuditEventRow(
            "AUTH_LOGIN_FAILED", NAIVE_NOW - timedelta(days=3, seconds=i), "alice", "198.51.100.5"
        )
        for i in range(40)
    ]

    report = _service(FakeAgentRepository(events=old)).report(actor=_actor(), window_hours=24)

    assert report.findings == [] and report.inputs.audit_events_read == 0


def test_a_failure_run_is_read_from_the_newest_checks_down() -> None:
    history = DamagedFileHistory(
        file_uuid="11111111-1111-4111-8111-111111111111",
        filename="a.pdf",
        owner_username="alice",
        status="CORRUPTED",
        uploaded_at=NAIVE_NOW - timedelta(days=9),
        checks=(
            ("MODIFIED", NAIVE_NOW - timedelta(hours=1)),
            ("MODIFIED", NAIVE_NOW - timedelta(hours=5)),  # the run began here
            ("VALID", NAIVE_NOW - timedelta(hours=29)),  # last known good
            ("MODIFIED", NAIVE_NOW - timedelta(days=4)),  # an older, healed episode
            ("VALID", NAIVE_NOW - timedelta(days=6)),
        ),
    )

    last_valid, began, newest = current_failure_run(history)

    assert last_valid == NAIVE_NOW - timedelta(hours=29)
    assert began == NAIVE_NOW - timedelta(hours=5)
    assert newest == "MODIFIED"


def test_a_file_with_no_passing_check_has_no_known_good_time() -> None:
    history = DamagedFileHistory(
        "x", "a.pdf", "alice", "CORRUPTED", NAIVE_NOW, (("MISSING", NAIVE_NOW),)
    )

    assert current_failure_run(history) == (None, NAIVE_NOW, "MISSING")
    assert current_failure_run(DamagedFileHistory("x", "a", "b", "CORRUPTED", NAIVE_NOW, ())) == (
        None,
        None,
        None,
    )


def test_a_damaged_file_and_a_broken_chain_are_critical_and_listed_first() -> None:
    history = DamagedFileHistory(
        file_uuid="11111111-1111-4111-8111-111111111111",
        filename="report.pdf",
        owner_username="alice",
        status="CORRUPTED",
        uploaded_at=NAIVE_NOW - timedelta(days=9),
        checks=(
            ("MODIFIED", NAIVE_NOW - timedelta(hours=2)),
            ("VALID", NAIVE_NOW - timedelta(days=1)),
        ),
    )
    service = _service(
        FakeAgentRepository(events=_failures(14), histories=[history]),
        audit=FakeAuditQuery(valid=False, position=57, checked=56),
    )

    report = service.report(actor=_actor(), window_hours=24)

    assert report.counts.critical == 2
    assert [f.priority for f in report.findings][:2] == ["CRITICAL", "CRITICAL"]
    damage = next(f for f in report.findings if f.rule_id == "INTEGRITY_DAMAGE")
    assert damage.file_id == UUID("11111111-1111-4111-8111-111111111111")
    assert "certainly hold the original" in damage.recommended_action
    chain = next(f for f in report.findings if f.rule_id == "AUDIT_CHAIN_BROKEN")
    assert "position 57" in " ".join(chain.evidence)


def test_a_stale_scan_is_reported_from_the_coverage_figures() -> None:
    admin = FakeAdminRepository(last_sweep=None, candidates=4, never=4)

    report = _service(admin=admin).report(actor=_actor(), window_hours=24)

    assert [f.rule_id for f in report.findings] == ["SCAN_NOT_RUNNING"]
    assert report.inputs.last_scan_at is None


# --- the SQL: read-only, and metadata only --------------------------------------------------


class _Db:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def _record(self, statement) -> str:
        sql = str(
            statement.compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": True})
        )
        self.statements.append(sql)
        return sql

    def execute(self, statement):
        self._record(statement)

        class _Rows(list):
            def all(self):
                return []

        return _Rows()

    def scalar(self, statement):
        self._record(statement)
        return 0


def test_the_event_query_selects_four_columns_and_never_metadata_or_user_agents() -> None:
    db = _Db()
    AgentRepository(db).audit_events(["AUTH_LOGIN_FAILED"], since=NAIVE_NOW)  # type: ignore[arg-type]

    sql = db.statements[0]
    select_list = sql.split("FROM", maxsplit=1)[0]
    assert "audit_logs.action" in select_list and "users.username" in select_list
    assert "audit_logs.ip_address" in select_list
    for private in (
        "metadata_json",
        "user_agent",
        "description",
        "resource_id",
        "password_hash",
        "email",
    ):
        assert private not in select_list
    assert "audit_logs.action IN ('AUTH_LOGIN_FAILED')" in sql
    assert "audit_logs.created_at >= " in sql and "LIMIT 20000" in sql


def test_the_damaged_file_query_never_selects_keys_nonces_or_ciphertext_columns() -> None:
    db = _Db()
    AgentRepository(db).damaged_file_histories(limit=50)  # type: ignore[arg-type]

    sql = db.statements[0]
    select_list = sql.split("FROM", maxsplit=1)[0]
    for private in ("iv", "auth_tag", "encrypted_manifest", "storage_object_key", "password_hash"):
        assert f".{private}" not in select_list
    assert "files.status != 'DELETED'" in sql


def test_the_agent_modules_have_no_database_write_path() -> None:
    import inspect
    import re

    from app.repositories import agent_repository
    from app.services import security_agent_rules, security_agent_service

    write = re.compile(
        r"\.(add|add_all|delete|merge|flush|commit|rollback)\(|\b(insert|update|delete)\("
    )
    for module in (agent_repository, security_agent_rules, security_agent_service):
        source = inspect.getsource(module)
        assert not write.search(source), f"{module.__name__} can write to the database"
        assert "AuditLogService" not in source, f"{module.__name__} could append to the audit log"
