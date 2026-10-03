"""The security agent's rules, against fabricated evidence: thresholds, ranking, and advice."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.services.security_agent_rules import (
    RULES,
    AgentInputs,
    DamagedFile,
    Event,
    Priority,
    backup_window_advice,
    evaluate,
    max_in_span,
)

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)


def _events(count: int, *, every: timedelta, actor="mallory", source="203.0.113.7", start=None):
    start = start or NOW - timedelta(hours=1)
    return [Event(at=start + i * every, actor=actor, source=source) for i in range(count)]


def _inputs(**kwargs) -> AgentInputs:
    return AgentInputs(now=NOW, window=timedelta(hours=24), **kwargs)


def _titles(findings):
    return [finding.title for finding in findings]


def _damaged(**over) -> DamagedFile:
    values = {
        "file_id": "11111111-1111-4111-8111-111111111111",
        "filename": "report.pdf",
        "owner": "alice",
        "status": "CORRUPTED",
        "last_result": "MODIFIED",
        "uploaded_at": NOW - timedelta(days=5),
        "last_valid_at": NOW - timedelta(days=2),
        "first_failure_at": NOW - timedelta(hours=3),
    }
    values.update(over)
    return DamagedFile(**values)


def test_a_quiet_system_produces_no_findings_and_says_which_rules_ran() -> None:
    findings, outcomes = evaluate(
        _inputs(chain_valid=True, last_sweep_at=NOW - timedelta(hours=5), checkable_files=4)
    )

    assert findings == []
    assert [outcome.info.rule_id for outcome in outcomes] == [info.rule_id for info, _ in RULES]
    assert all(outcome.findings == 0 for outcome in outcomes)


def test_the_sliding_window_finds_the_densest_stretch_not_the_total() -> None:
    spread = [NOW + timedelta(minutes=10 * i) for i in range(12)]  # 12 events, never 3 in 15 min
    burst = [NOW + timedelta(seconds=5 * i) for i in range(8)]

    assert max_in_span(spread, timedelta(minutes=15))[0] == 2
    peak, began = max_in_span(spread + burst, timedelta(minutes=15))
    assert peak >= 8 and began is not None
    assert max_in_span([], timedelta(minutes=1)) == (0, None)


def test_login_guessing_is_graded_by_how_fast_and_how_many() -> None:
    quiet = _events(9, every=timedelta(minutes=1))
    assert evaluate(_inputs(login_failures=quiet))[0] == []

    medium = _events(12, every=timedelta(minutes=1))
    findings, _ = evaluate(_inputs(login_failures=medium))
    assert [(f.rule_id, f.priority) for f in findings] == [
        ("LOGIN_GUESSING_SOURCE", Priority.MEDIUM)
    ]

    high = _events(35, every=timedelta(seconds=20))
    findings, _ = evaluate(_inputs(login_failures=high))
    assert [(f.rule_id, f.priority) for f in findings] == [("LOGIN_GUESSING_SOURCE", Priority.HIGH)]


def test_one_address_guessing_one_account_is_one_finding_that_names_the_account() -> None:
    findings, _ = evaluate(
        _inputs(login_failures=_events(12, every=timedelta(minutes=1), actor="alice"))
    )

    (finding,) = findings
    assert "Accounts tried: alice" in finding.evidence


def test_the_source_finding_counts_attempts_at_names_that_do_not_exist() -> None:
    events = _events(6, every=timedelta(minutes=1), actor=None) + _events(
        6, every=timedelta(minutes=1), actor="bob"
    )

    (finding,) = evaluate(_inputs(login_failures=events))[0]

    assert "Accounts tried: bob" in finding.evidence
    assert "6 attempts at names with no account" in finding.evidence


def test_an_account_tried_from_many_addresses_is_caught_even_when_no_address_is_busy() -> None:
    spread = [
        Event(
            at=NOW - timedelta(minutes=10) + timedelta(seconds=30 * i),
            actor="alice",
            source=f"198.51.100.{i}",
        )
        for i in range(12)
    ]

    findings, _ = evaluate(_inputs(login_failures=spread))

    assert [f.rule_id for f in findings] == ["LOGIN_GUESSING_ACCOUNT"]
    assert "From 12 addresses" in findings[0].evidence


def test_slow_guessing_that_never_bunches_up_is_not_flagged() -> None:
    slow = _events(40, every=timedelta(minutes=5))  # 40 failures a day, 3 per 15 minutes

    assert evaluate(_inputs(login_failures=slow))[0] == []


def test_guessing_is_attributed_to_the_right_source_and_account() -> None:
    a = _events(12, every=timedelta(minutes=1), actor="alice", source="198.51.100.1")
    b = _events(3, every=timedelta(minutes=1), actor="bob", source="198.51.100.2")

    findings, _ = evaluate(_inputs(login_failures=a + b))

    text = " ".join(" ".join(f.evidence) for f in findings)
    assert "198.51.100.1" in text and "198.51.100.2" not in text
    assert "alice" in text and "bob" not in text


def test_a_modified_file_is_critical_and_names_the_backup_window() -> None:
    findings, outcomes = evaluate(_inputs(damaged=[_damaged()]))

    (finding,) = findings
    assert finding.priority is Priority.CRITICAL and finding.rule_id == "INTEGRITY_DAMAGE"
    assert finding.file_id == "11111111-1111-4111-8111-111111111111"
    assert (
        "scripts/restore_file.py --file-id 11111111-1111-4111-8111-111111111111"
        in finding.recommended_action
    )
    assert "certainly hold the original" in finding.recommended_action
    assert "2026-09-30 12:00 UTC" in finding.recommended_action  # last intact check
    assert "2026-10-02 09:00 UTC" in finding.recommended_action  # damage first seen
    assert next(o for o in outcomes if o.info.rule_id == "INTEGRITY_DAMAGE").findings == 1


def test_missing_and_unreadable_objects_rank_below_modified_ones_and_are_not_called_tampering() -> (
    None
):
    findings, _ = evaluate(
        _inputs(
            damaged=[
                _damaged(file_id="a" * 8 + "-1111-4111-8111-111111111111", last_result="ERROR"),
                _damaged(file_id="b" * 8 + "-1111-4111-8111-111111111111", last_result="MISSING"),
                _damaged(),
            ]
        )
    )

    assert [f.priority for f in findings] == [Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM]
    assert "not evidence of tampering" in findings[2].summary
    assert "proves nothing about the contents" in findings[1].summary


def test_advice_without_a_known_good_check_says_so_and_still_gives_a_starting_point() -> None:
    advice = backup_window_advice(_damaged(last_valid_at=None, first_failure_at=None))

    assert "no passing check on record" in advice
    assert "earliest backup set taken after the upload" in advice
    assert "no set holds it yet" in advice


def test_a_broken_chain_is_critical_and_says_not_to_deploy() -> None:
    findings, _ = evaluate(
        _inputs(chain_valid=False, chain_first_invalid_position=41, chain_checked_entries=40)
    )

    (finding,) = findings
    assert finding.priority is Priority.CRITICAL and finding.rule_id == "AUDIT_CHAIN_BROKEN"
    assert "position 41" in " ".join(finding.evidence)
    assert "Stop deploying" in finding.recommended_action


def test_an_unchecked_chain_is_not_reported_as_broken() -> None:
    assert evaluate(_inputs(chain_valid=None))[0] == []
    assert evaluate(_inputs(chain_valid=True))[0] == []


def test_a_stale_or_missing_scan_is_flagged_only_when_there_is_something_to_scan() -> None:
    assert evaluate(_inputs(last_sweep_at=None, checkable_files=0))[0] == []

    never, _ = evaluate(_inputs(last_sweep_at=None, checkable_files=3, never_checked_files=3))
    assert [f.rule_id for f in never] == ["SCAN_NOT_RUNNING"] and never[
        0
    ].priority is Priority.MEDIUM
    assert "never" in " ".join(never[0].evidence)

    old, _ = evaluate(_inputs(last_sweep_at=NOW - timedelta(hours=40), checkable_files=3))
    assert [f.rule_id for f in old] == ["SCAN_NOT_RUNNING"]
    recent, _ = evaluate(_inputs(last_sweep_at=NOW - timedelta(hours=35), checkable_files=3))
    assert recent == []


def test_a_replayed_session_token_is_high_and_grouped_per_account() -> None:
    replays = [Event(at=NOW - timedelta(minutes=m), actor="alice") for m in (5, 3)] + [
        Event(at=NOW - timedelta(minutes=1), actor=None)
    ]

    findings, _ = evaluate(_inputs(refresh_replays=replays))

    assert [f.priority for f in findings] == [Priority.HIGH, Priority.HIGH]
    assert any("2 replays" in " ".join(f.evidence) for f in findings)
    assert any("Check the Audit chain tab" in f.recommended_action for f in findings)


def test_bulk_downloading_is_medium_then_high() -> None:
    medium = _events(25, every=timedelta(seconds=10), actor="carol")
    high = _events(70, every=timedelta(seconds=5), actor="dave")

    findings, _ = evaluate(_inputs(downloads=medium + high))

    by_actor = {f.title.split()[0]: f.priority for f in findings}
    assert by_actor == {"carol": Priority.MEDIUM, "dave": Priority.HIGH}


def test_sharing_bursts_and_password_guessing_have_their_own_grades() -> None:
    shares = _events(11, every=timedelta(minutes=2), actor="erin")
    password = _events(5, every=timedelta(minutes=1), actor="frank")

    findings, _ = evaluate(_inputs(shares=shares, password_failures=password))

    by_rule = {f.rule_id: f.priority for f in findings}
    assert by_rule == {"SHARE_BURST": Priority.LOW, "PASSWORD_CHANGE_GUESSING": Priority.MEDIUM}


def test_upload_bursts_are_graded_and_a_normal_pace_is_quiet() -> None:
    normal = _events(29, every=timedelta(seconds=20), actor="grace")  # 29 in 10 min: under
    medium = _events(30, every=timedelta(seconds=20), actor="heidi")
    high = _events(100, every=timedelta(seconds=5), actor="ivan")

    findings, _ = evaluate(_inputs(uploads=normal + medium + high))

    by_actor = {f.title.split()[0]: (f.rule_id, f.priority) for f in findings}
    assert by_actor == {
        "heidi": ("UPLOAD_BURST", Priority.MEDIUM),
        "ivan": ("UPLOAD_BURST", Priority.HIGH),
    }


def test_recovery_activity_is_reported_and_old_requests_are_a_low_notice() -> None:
    findings, _ = evaluate(
        _inputs(
            recoveries_executed=[Event(at=NOW - timedelta(hours=2), actor="admin")],
            recoveries_pending_old=2,
        )
    )

    assert [f.priority for f in findings] == [Priority.MEDIUM, Priority.LOW]
    assert "2 recovery requests waiting" in findings[1].title


def test_the_report_is_ordered_most_urgent_first() -> None:
    findings, _ = evaluate(
        _inputs(
            login_failures=_events(12, every=timedelta(minutes=1)),
            damaged=[_damaged()],
            refresh_replays=[Event(at=NOW, actor="alice")],
            shares=_events(11, every=timedelta(minutes=2), actor="erin"),
        )
    )

    priorities = [f.priority for f in findings]
    assert priorities == sorted(
        priorities,
        key=lambda p: [Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM, Priority.LOW].index(p),
    )
    assert priorities[0] is Priority.CRITICAL and priorities[-1] is Priority.LOW


def test_the_same_evidence_always_gives_the_same_report() -> None:
    inputs = _inputs(login_failures=_events(12, every=timedelta(minutes=1)), damaged=[_damaged()])

    assert evaluate(inputs)[0] == evaluate(inputs)[0]


def test_the_agent_only_ever_suggests_the_dry_run_of_a_restore() -> None:
    findings, _ = evaluate(_inputs(damaged=[_damaged()]))

    for finding in findings:
        # "run without --apply first" is the instruction; a command that applies is never given.
        text = finding.recommended_action.replace("without --apply", "")
        assert "--apply" not in text


# --- v2: a sign-in that worked after guessing, and throttle blocks ---------------------------


def _success(at=None, *, actor="victim", source="203.0.113.7", admin=False) -> Event:
    return Event(at=at or NOW - timedelta(minutes=30), actor=actor, source=source, admin=admin)


def _takeovers(findings):
    return [f for f in findings if f.rule_id == "SIGN_IN_AFTER_GUESSING"]


def test_a_sign_in_after_five_failures_on_the_account_is_high_and_four_is_nothing() -> None:
    success = _success()
    start = success.at - timedelta(minutes=5)

    four = _events(
        4, every=timedelta(seconds=30), actor="victim", source="198.51.100.1", start=start
    )
    assert _takeovers(evaluate(_inputs(login_failures=four, login_successes=[success]))[0]) == []

    five = _events(
        5, every=timedelta(seconds=30), actor="victim", source="198.51.100.1", start=start
    )
    (finding,) = _takeovers(evaluate(_inputs(login_failures=five, login_successes=[success]))[0])
    assert finding.priority == Priority.HIGH
    assert finding.title == "victim signed in right after a run of failed sign-ins"
    text = " ".join(finding.evidence)
    assert "5 failed sign-ins" in text and "5 against this account, 0 from the address" in text
    assert "Failures came from 1 address" in text
    assert "from 203.0.113.7" in text  # where the success came from
    assert "disable the account on the Users tab" in finding.recommended_action
    assert "Access Records" in finding.recommended_action


def test_five_failures_from_the_same_address_at_other_accounts_also_fire() -> None:
    # Credential stuffing: one address tries several accounts, then gets into one of them,
    # which itself had no failed attempt.
    success = _success(actor="carol", source="203.0.113.50")
    tried = [
        Event(
            at=success.at - timedelta(minutes=4, seconds=i * 20), actor=name, source="203.0.113.50"
        )
        for i, name in enumerate(["a1", "a2", "a3", "a4", None])
    ]

    (finding,) = _takeovers(evaluate(_inputs(login_failures=tried, login_successes=[success]))[0])
    assert "0 against this account, 5 from the address that then signed in" in " ".join(
        finding.evidence
    )


def test_an_administrator_signing_in_after_guessing_is_critical() -> None:
    success = _success(actor="root-admin", admin=True)
    failures = _events(
        6, every=timedelta(seconds=10), actor="root-admin", start=success.at - timedelta(minutes=2)
    )

    (finding,) = _takeovers(
        evaluate(_inputs(login_failures=failures, login_successes=[success]))[0]
    )
    assert finding.priority == Priority.CRITICAL
    assert "Account: root-admin (administrator)" in finding.evidence


def test_failures_older_than_the_span_or_after_the_success_do_not_count() -> None:
    success = _success()
    old = _events(
        10, every=timedelta(seconds=5), actor="victim", start=success.at - timedelta(minutes=40)
    )
    after = _events(
        10, every=timedelta(seconds=5), actor="victim", start=success.at + timedelta(seconds=5)
    )

    assert (
        _takeovers(evaluate(_inputs(login_failures=old + after, login_successes=[success]))[0])
        == []
    )


def test_failures_elsewhere_are_not_attributed_to_an_unrelated_sign_in() -> None:
    success = _success(actor="bystander", source="192.0.2.200")
    guessing = _events(
        9,
        every=timedelta(seconds=10),
        actor="victim",
        source="203.0.113.7",
        start=success.at - timedelta(minutes=3),
    )

    assert (
        _takeovers(evaluate(_inputs(login_failures=guessing, login_successes=[success]))[0]) == []
    )


def test_signing_in_again_on_the_same_failures_is_one_incident_not_two() -> None:
    first = _success()
    again = _success(first.at + timedelta(minutes=2))
    failures = _events(
        7, every=timedelta(seconds=10), actor="victim", start=first.at - timedelta(minutes=3)
    )

    findings, outcomes = evaluate(_inputs(login_failures=failures, login_successes=[first, again]))
    (finding,) = _takeovers(findings)
    assert "1 more sign-in to this account after that, with no new failures" in finding.evidence
    assert next(o for o in outcomes if o.info.rule_id == "SIGN_IN_AFTER_GUESSING").findings == 1


def test_a_second_run_of_guessing_that_works_again_is_a_second_incident() -> None:
    first = _success()
    later = _success(first.at + timedelta(hours=2))
    failures = _events(
        5, every=timedelta(seconds=10), actor="victim", start=first.at - timedelta(minutes=2)
    )
    failures += _events(
        5, every=timedelta(seconds=10), actor="victim", start=later.at - timedelta(minutes=2)
    )

    assert (
        len(
            _takeovers(
                evaluate(_inputs(login_failures=failures, login_successes=[first, later]))[0]
            )
        )
        == 2
    )


def test_the_takeover_is_added_to_the_guessing_finding_not_a_third_finding_for_it() -> None:
    success = _success()
    failures = _events(
        12, every=timedelta(seconds=10), actor="victim", start=success.at - timedelta(minutes=3)
    )

    findings, _ = evaluate(_inputs(login_failures=failures, login_successes=[success]))
    # That guessing happened (source rule) and that it worked (takeover rule): two facts, two
    # findings. The account rule stays quiet because it was one address.
    assert sorted(f.rule_id for f in findings) == [
        "LOGIN_GUESSING_SOURCE",
        "SIGN_IN_AFTER_GUESSING",
    ]


def test_a_success_with_no_failures_before_it_is_nothing() -> None:
    assert (
        evaluate(_inputs(login_successes=[_success(), _success(actor="x", source=None)]))[0] == []
    )


def test_throttle_blocks_are_counted_and_graded_by_scope() -> None:
    assert evaluate(_inputs())[0] == []

    (accounts_only,) = evaluate(_inputs(throttled_accounts=2, throttle_policy="policy text"))[0]
    assert accounts_only.rule_id == "SIGN_IN_THROTTLE_ACTIVE"
    assert accounts_only.priority == Priority.LOW
    assert "Blocked right now: 0 addresses, 2 accounts" in accounts_only.evidence
    assert "Throttle policy: policy text" in accounts_only.evidence

    (with_address,) = evaluate(_inputs(throttled_addresses=1, throttled_accounts=3))[0]
    assert with_address.priority == Priority.MEDIUM
    assert with_address.title == "The sign-in throttle is blocking 1 address and 3 accounts"
    assert "not in the audit log" in " ".join(with_address.evidence)
