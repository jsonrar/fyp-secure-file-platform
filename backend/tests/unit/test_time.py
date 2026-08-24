from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from app.core.time import to_api_utc, to_database_utc, to_second_resolution_utc

INSTANT = datetime(2026, 8, 24, 8, 6, 34, 691352, tzinfo=UTC)


def test_second_resolution_drops_the_fraction_rather_than_letting_mysql_round_it() -> None:
    """A plain DATETIME column rounds; it does not truncate.

    Handing MySQL 12:00:34.691 stored 12:00:35, so the API answered with an instant that
    was never stored and the row sat half a second in the future.
    """
    assert to_second_resolution_utc(INSTANT) == datetime(2026, 8, 24, 8, 6, 34)


def test_second_resolution_only_ever_moves_a_timestamp_backwards() -> None:
    for microsecond in (0, 1, 499_999, 500_000, 500_001, 999_999):
        value = INSTANT.replace(microsecond=microsecond)
        assert to_second_resolution_utc(value) <= to_database_utc(value)


def test_second_resolution_normalizes_a_non_utc_offset_first() -> None:
    melbourne = timezone(timedelta(hours=10))
    value = datetime(2026, 8, 24, 18, 6, 34, 691352, tzinfo=melbourne)

    assert to_second_resolution_utc(value) == datetime(2026, 8, 24, 8, 6, 34)


def test_second_resolution_accepts_an_already_naive_value() -> None:
    assert to_second_resolution_utc(INSTANT.replace(tzinfo=None)) == datetime(2026, 8, 24, 8, 6, 34)


def test_database_utc_still_keeps_microseconds_for_the_hashed_columns() -> None:
    """`audit_logs` and the key-custody tables are DATETIME(6) on purpose.

    Their values are covered by the audit hash chain and the key-custody signatures, so
    they must keep every digit they were hashed with.
    """
    assert to_database_utc(INSTANT).microsecond == 691352


def test_api_utc_round_trips_a_second_resolution_value() -> None:
    stored = to_second_resolution_utc(INSTANT)

    assert to_api_utc(stored) == datetime(2026, 8, 24, 8, 6, 34, tzinfo=UTC)
