from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def to_database_utc(value: datetime) -> datetime:
    """Convert an instant to the naive UTC representation used by MySQL DATETIME."""
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def to_api_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
