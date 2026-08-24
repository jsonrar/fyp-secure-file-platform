from __future__ import annotations

import importlib.util
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import mysql

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _load_reconcile():
    """Load the script by path: `scripts/` is a command directory, not a package."""
    spec = importlib.util.spec_from_file_location(
        "reconcile_script", BACKEND_ROOT / "scripts" / "reconcile.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


reconcile = _load_reconcile()

CUTOFF = datetime(2026, 7, 25, 12, 0, tzinfo=UTC).replace(tzinfo=None)


def _sql(condition) -> str:
    return str(condition.compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}))


class CountingDb:
    """Records what would be deleted without touching a database."""

    def __init__(self, count: int = 0) -> None:
        self.count = count
        self.deletes: list[str] = []

    def scalar(self, statement) -> int:
        return self.count

    def execute(self, statement) -> None:
        self.deletes.append(str(statement.compile(dialect=mysql.dialect())))

    def scalars(self, statement):
        return SimpleNamespace(all=lambda: [])


# ---------------------------------------------------------------------------
# The predicates. Each decides what is safe to destroy, so each is worth pinning.
# ---------------------------------------------------------------------------


def test_a_throttle_bucket_that_still_blocks_someone_is_never_removed() -> None:
    """The one predicate here that can undo a security control.

    Deleting a bucket resets its counter. A bucket whose window is old but whose block is
    still running belongs to someone currently locked out, and removing it would hand them
    a fresh allowance -- turning a cleanup job into a way to bypass the lockout.
    """
    db = CountingDb(count=1)
    reconcile._lapsed_throttles(db, CUTOFF, apply=True)

    assert len(db.deletes) == 1
    condition = _sql(reconcile.AuthLoginThrottle.window_started_at < CUTOFF)
    assert "window_started_at" in condition
    assert "blocked_until" in db.deletes[0]


def test_throttle_removal_requires_both_the_window_and_the_block_to_have_lapsed() -> None:
    db = CountingDb(count=1)
    reconcile._lapsed_throttles(db, CUTOFF, apply=True)

    statement = db.deletes[0]
    assert "window_started_at <" in statement
    assert "blocked_until IS NULL" in statement
    assert "blocked_until <" in statement


def test_sessions_take_their_refresh_tokens_with_them() -> None:
    """The foreign key would refuse otherwise, and a stranded token outlives its session."""
    db = CountingDb(count=1)
    reconcile._expired_sessions(db, CUTOFF, apply=True)

    assert len(db.deletes) == 2
    assert "session_refresh_tokens" in db.deletes[0]
    assert "user_sessions" in db.deletes[1]


def test_reporting_never_deletes() -> None:
    """The default mode has to be inert, or "let me see what it would do" is a lie."""
    for run in (
        reconcile._expired_refresh_tokens,
        reconcile._expired_sessions,
        reconcile._lapsed_throttles,
        reconcile._expired_verification_codes,
    ):
        db = CountingDb(count=5)
        assert run(db, CUTOFF, apply=False) == 5
        assert db.deletes == []


# ---------------------------------------------------------------------------
# The storage scan, which can destroy a file that is about to become real.
# ---------------------------------------------------------------------------


def _storage_settings(tmp_path: Path):
    from app.core.config import Settings

    return Settings(
        _env_file=None,
        APP_ENV="test",
        APP_DEBUG=False,
        SECRET_KEY="reconcile-test-secret-key-long-enough",
        ENCRYPTED_FILE_DIR=tmp_path / "objects",
        TEMP_FILE_DIR=tmp_path / "staging",
    )


@pytest.fixture
def storage(tmp_path, monkeypatch):
    settings = _storage_settings(tmp_path)
    monkeypatch.setattr(reconcile, "get_settings", lambda: settings)
    settings.ENCRYPTED_FILE_DIR.mkdir(parents=True)
    settings.TEMP_FILE_DIR.mkdir(parents=True)
    return settings


def _object(settings, name: str, *, age_seconds: float) -> Path:
    path = settings.ENCRYPTED_FILE_DIR / name / "object.ciphertext"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"ciphertext")
    stamp = time.time() - age_seconds
    import os

    os.utime(path, (stamp, stamp))
    return path


def test_an_object_younger_than_the_grace_is_left_alone(storage) -> None:
    """`publish` writes the object before the transaction commits.

    An object that appeared moments ago may belong to a request still in flight, and
    deleting it destroys a file that is about to become real. The grace period is the only
    thing standing between this job and that.
    """
    in_flight = _object(storage, "in-flight", age_seconds=5)
    cutoff = time.time() - 3600

    orphans, _, _ = reconcile._storage_objects(CountingDb(), cutoff, apply=True)

    assert orphans == 0
    assert in_flight.exists()


def test_an_old_object_no_row_names_is_removed(storage) -> None:
    orphan = _object(storage, "orphan", age_seconds=7200)
    cutoff = time.time() - 3600

    orphans, _, _ = reconcile._storage_objects(CountingDb(), cutoff, apply=True)

    assert orphans == 1
    assert not orphan.exists()


def test_an_object_a_live_row_names_is_kept_however_old(storage) -> None:
    kept = _object(storage, "referenced", age_seconds=90 * 86400)
    key = str(kept.relative_to(storage.ENCRYPTED_FILE_DIR))

    class DbWithRow(CountingDb):
        def scalars(self, statement):
            return SimpleNamespace(all=lambda: [key])

    orphans, _, _ = reconcile._storage_objects(DbWithRow(), time.time() - 3600, apply=True)

    assert orphans == 0
    assert kept.exists()


def test_a_stale_staged_upload_is_removed_and_a_fresh_one_is_not(storage) -> None:
    import os

    stale = storage.TEMP_FILE_DIR / ".stale.staging"
    stale.write_bytes(b"abandoned")
    os.utime(stale, (time.time() - 7200, time.time() - 7200))
    fresh = storage.TEMP_FILE_DIR / ".fresh.staging"
    fresh.write_bytes(b"in progress")

    _, staged, _ = reconcile._storage_objects(CountingDb(), time.time() - 3600, apply=True)

    assert staged == 1
    assert not stale.exists()
    assert fresh.exists()


def test_the_storage_cutoff_is_compared_in_epoch_seconds(storage) -> None:
    """Guards a bug that made the whole scan silently find nothing.

    `st_mtime` is epoch seconds. Calling `.timestamp()` on the naive UTC datetime used for
    the row cutoffs reads it as *local* time, so on a UTC+10 host the cutoff moved ten
    hours into the past and no object was ever old enough to collect.
    """
    orphan = _object(storage, "orphan", age_seconds=7200)

    orphans, _, _ = reconcile._storage_objects(CountingDb(), time.time() - 3600, apply=False)

    assert orphans == 1
    assert orphan.exists(), "report-only must not delete"
