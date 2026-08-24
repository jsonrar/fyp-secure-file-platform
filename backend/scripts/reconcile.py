"""Remove the rows and storage objects that nothing will ever read again.

Four tables grow without bound today. Sessions, refresh tokens, throttle buckets and
verification codes are all written on ordinary traffic and none of them is ever deleted:
a failed login leaves a throttle bucket behind for good, and every sign-in leaves a
session row that stays there long after the session stopped being usable. Nothing reads
them once they lapse -- expiry is decided from the timestamps at request time, never from
a stored flag -- so they are pure accumulation.

Storage has the mirror problem. A process that dies between publishing a ciphertext object
and committing its row leaves an object no row names, and a `delete` whose unlink failed
leaves an object whose row already says `DELETED`. Neither is reachable through the API
and neither is ever cleaned up.

Run from `backend/` with the deployment environment loaded:

    .venv/bin/python scripts/reconcile.py                  # report only
    .venv/bin/python scripts/reconcile.py --apply          # actually delete

Reporting is the default on purpose. The first run on a real deployment should be read,
not trusted, and a reconciler is exactly the kind of job whose bugs are discovered by
what it removed.

What this never touches, deliberately:

* `audit_logs` and `audit_chain_heads` -- append-only by design, covered by a hash chain
  that `POST /audit-logs/verify-chain` recomputes from the stored rows. Deleting from the
  middle of a hash chain destroys the property the table exists to provide, and the
  runtime grant is `SELECT, INSERT` precisely so this cannot happen by accident.
* `files`, `file_access_grants`, `file_key_wrappings`, `integrity_checks` -- a deleted
  file is a soft delete that stays queryable, and the integrity history is evidence.
* `users`, `user_keys`, and the key-custody tables -- an account's key material outlives
  the account's activity, and a key still wraps files uploaded under it.
* `recovery_requests` -- an expired request records that someone asked for a file and
  nobody acted on it, which is accountability information rather than debris.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.time import to_second_resolution_utc, utc_now
from app.models.auth_login_throttle import AuthLoginThrottle
from app.models.email_verification_code import EmailVerificationCode
from app.models.file import File
from app.models.session_refresh_token import SessionRefreshToken
from app.models.user_session import UserSession

DEFAULT_RETAIN_DAYS = 30
DEFAULT_STORAGE_GRACE_MINUTES = 60


@dataclass
class Finding:
    what: str
    count: int
    detail: str = ""


@dataclass
class Report:
    cutoff: datetime
    storage_cutoff: datetime
    applied: bool
    findings: list[Finding] = field(default_factory=list)

    def add(self, what: str, count: int, detail: str = "") -> None:
        self.findings.append(Finding(what=what, count=count, detail=detail))

    @property
    def total(self) -> int:
        return sum(finding.count for finding in self.findings)


def _expired_refresh_tokens(db: Session, cutoff: datetime, *, apply: bool) -> int:
    """Tokens that expired, were consumed, or were revoked before the cutoff.

    A refresh token is single use: once consumed it is only ever compared against, never
    honoured, and the rotation chain that would want it is itself long gone by the cutoff.
    """
    condition = (
        (SessionRefreshToken.expires_at < cutoff)
        | (SessionRefreshToken.consumed_at < cutoff)
        | (SessionRefreshToken.revoked_at < cutoff)
    )
    count = int(
        db.scalar(select(func.count()).select_from(SessionRefreshToken).where(condition)) or 0
    )
    if apply and count:
        db.execute(delete(SessionRefreshToken).where(condition))
    return count


def _expired_sessions(db: Session, cutoff: datetime, *, apply: bool) -> int:
    """Sessions past their absolute expiry, or revoked, before the cutoff.

    Expiry is derived from `absolute_expires_at` at request time rather than from the
    stored status, so a lapsed session is unusable regardless of what its status column
    says. Refresh tokens reference sessions, so they go first.
    """
    condition = (UserSession.absolute_expires_at < cutoff) | (UserSession.revoked_at < cutoff)
    doomed = select(UserSession.id).where(condition).subquery()
    count = int(db.scalar(select(func.count()).select_from(UserSession).where(condition)) or 0)
    if apply and count:
        db.execute(
            delete(SessionRefreshToken).where(
                SessionRefreshToken.session_id.in_(select(doomed.c.id))
            )
        )
        db.execute(delete(UserSession).where(condition))
    return count


def _lapsed_throttles(db: Session, cutoff: datetime, *, apply: bool) -> int:
    """Buckets whose counting window and any block have both lapsed.

    Removing a bucket resets its counter, so a bucket that still blocks somebody must
    survive: `blocked_until` is checked as well as the window, and a NULL block counts as
    lapsed only because the window already has.
    """
    condition = (AuthLoginThrottle.window_started_at < cutoff) & (
        (AuthLoginThrottle.blocked_until.is_(None)) | (AuthLoginThrottle.blocked_until < cutoff)
    )
    count = int(
        db.scalar(select(func.count()).select_from(AuthLoginThrottle).where(condition)) or 0
    )
    if apply and count:
        db.execute(delete(AuthLoginThrottle).where(condition))
    return count


def _expired_verification_codes(db: Session, cutoff: datetime, *, apply: bool) -> int:
    """Codes past their expiry. Only the keyed digest was ever stored, never the code."""
    condition = EmailVerificationCode.expires_at < cutoff
    count = int(
        db.scalar(select(func.count()).select_from(EmailVerificationCode).where(condition)) or 0
    )
    if apply and count:
        db.execute(delete(EmailVerificationCode).where(condition))
    return count


def _storage_objects(
    db: Session, storage_cutoff_epoch: float, *, apply: bool
) -> tuple[int, int, int]:
    """Ciphertext objects and staged files that no live row accounts for.

    The grace period is the important part. `publish` writes the object before the
    transaction commits, so an object younger than the grace may belong to a request still
    in flight; removing it would destroy a file that is about to become real. Only objects
    older than the cutoff are considered, and only when the database says nothing needs
    them.
    """
    settings = get_settings()
    object_root = settings.ENCRYPTED_FILE_DIR
    staging_root = settings.TEMP_FILE_DIR

    live_keys = set(
        db.scalars(select(File.storage_object_key).where(File.status != "DELETED")).all()
    )
    # Compared as epoch seconds throughout. `st_mtime` is epoch, and calling `.timestamp()`
    # on the naive UTC datetime used for the row cutoffs would read it as local time --
    # which on a UTC+10 host moves the cutoff ten hours and quietly makes this find
    # nothing at all.
    cutoff_stamp = storage_cutoff_epoch

    orphans: list[Path] = []
    if object_root.is_dir():
        for path in object_root.rglob("*.ciphertext"):
            relative = str(path.relative_to(object_root))
            if relative in live_keys:
                continue
            if path.stat().st_mtime >= cutoff_stamp:
                continue
            orphans.append(path)

    staged: list[Path] = []
    if staging_root.is_dir():
        for path in staging_root.glob("*.staging"):
            if path.stat().st_mtime < cutoff_stamp:
                staged.append(path)

    removed_dirs = 0
    if apply:
        for path in orphans:
            path.unlink(missing_ok=True)
        for path in staged:
            path.unlink(missing_ok=True)
        # A published object lives in a directory of its own; once it is gone the
        # directory is inert. rmdir refuses a non-empty one, which is the interlock
        # wanted against a concurrent publish.
        if object_root.is_dir():
            for directory in sorted(object_root.iterdir(), reverse=True):
                if not directory.is_dir():
                    continue
                try:
                    directory.rmdir()
                except OSError:
                    continue
                removed_dirs += 1
    elif object_root.is_dir():
        removed_dirs = sum(1 for d in object_root.iterdir() if d.is_dir() and not any(d.iterdir()))

    return len(orphans), len(staged), removed_dirs


def reconcile(*, retain_days: int, storage_grace_minutes: int, apply: bool) -> Report:
    instant = utc_now()
    now = to_second_resolution_utc(instant)
    cutoff = now - timedelta(days=retain_days)
    storage_cutoff_epoch = (instant - timedelta(minutes=storage_grace_minutes)).timestamp()
    report = Report(
        cutoff=cutoff,
        storage_cutoff=now - timedelta(minutes=storage_grace_minutes),
        applied=apply,
    )

    with SessionLocal() as db:
        try:
            report.add("expired refresh tokens", _expired_refresh_tokens(db, cutoff, apply=apply))
            report.add("expired sessions", _expired_sessions(db, cutoff, apply=apply))
            report.add("lapsed throttle buckets", _lapsed_throttles(db, cutoff, apply=apply))
            report.add(
                "expired verification codes", _expired_verification_codes(db, cutoff, apply=apply)
            )
            orphans, staged, dirs = _storage_objects(db, storage_cutoff_epoch, apply=apply)
            report.add("orphaned ciphertext objects", orphans)
            report.add("stale staged uploads", staged)
            report.add("empty per-file directories", dirs)
            if apply:
                db.commit()
            else:
                db.rollback()
        except Exception:
            db.rollback()
            raise
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete. Without it the script only reports what it would remove.",
    )
    parser.add_argument(
        "--retain-days",
        type=int,
        default=DEFAULT_RETAIN_DAYS,
        help=f"Keep lapsed rows this long before removing them (default {DEFAULT_RETAIN_DAYS}).",
    )
    parser.add_argument(
        "--storage-grace-minutes",
        type=int,
        default=DEFAULT_STORAGE_GRACE_MINUTES,
        help=(
            "Ignore storage objects younger than this, so an upload still in flight is "
            f"never mistaken for an orphan (default {DEFAULT_STORAGE_GRACE_MINUTES})."
        ),
    )
    args = parser.parse_args()
    if args.retain_days < 1:
        parser.error("--retain-days must be at least 1")
    if args.storage_grace_minutes < 5:
        parser.error("--storage-grace-minutes must be at least 5, to stay clear of live uploads")
    return args


def main() -> int:
    args = parse_args()
    report = reconcile(
        retain_days=args.retain_days,
        storage_grace_minutes=args.storage_grace_minutes,
        apply=args.apply,
    )

    print("removed" if report.applied else "would remove (pass --apply to act)")
    print(f"  rows lapsed before   {report.cutoff.isoformat()}Z")
    print(f"  storage older than   {report.storage_cutoff.isoformat()}Z")
    print()
    for finding in report.findings:
        print(f"  {finding.count:>8}  {finding.what}")
    print()
    print(f"  {report.total:>8}  total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
