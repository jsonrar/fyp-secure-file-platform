from collections.abc import Generator
from typing import Any

import pytest

from app.core import database


class FakeSession:
    def __init__(self) -> None:
        self.rolled_back = False
        self.closed = False

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def _dependency_with(
    monkeypatch: pytest.MonkeyPatch,
    session: FakeSession,
) -> Generator[Any, None, None]:
    monkeypatch.setattr(database, "SessionLocal", lambda: session)
    return database.get_db()


def test_database_dependency_closes_successful_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession()
    dependency = _dependency_with(monkeypatch, session)

    assert next(dependency) is session
    dependency.close()

    assert session.closed is True
    assert session.rolled_back is False


def test_database_dependency_rolls_back_failed_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession()
    dependency = _dependency_with(monkeypatch, session)
    next(dependency)

    with pytest.raises(RuntimeError, match="database operation failed"):
        dependency.throw(RuntimeError("database operation failed"))

    assert session.rolled_back is True
    assert session.closed is True
