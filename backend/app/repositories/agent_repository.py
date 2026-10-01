from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.file import File
from app.models.integrity_check import IntegrityCheck
from app.models.recovery_request import RecoveryRequest
from app.models.user import User

# A runaway log must not turn one report into an unbounded read. The newest events win, because
# a burst that is still going on is the one worth seeing.
EVENT_READ_LIMIT = 20_000


@dataclass(frozen=True, slots=True)
class AuditEventRow:
    action: str
    created_at: datetime
    actor_username: str | None
    ip_address: str | None


@dataclass(frozen=True, slots=True)
class DamagedFileHistory:
    file_uuid: str
    filename: str
    owner_username: str
    status: str
    uploaded_at: datetime
    # Newest first: (result, when). The service reads the current run of failures off the top.
    checks: tuple[tuple[str, datetime], ...]


class AgentRepository:
    """Read-only queries for the security agent. It writes nothing and returns metadata only.

    Nothing here selects file contents, keys, ciphertext, request bodies, user agents or
    audit metadata: event type, time, account name and source address are all the rules use.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def audit_events(self, actions: Sequence[str], *, since: datetime) -> list[AuditEventRow]:
        rows = self.db.execute(
            select(
                AuditLog.action,
                AuditLog.created_at,
                User.username,
                AuditLog.ip_address,
            )
            .outerjoin(User, User.id == AuditLog.actor_user_id)
            .where(AuditLog.action.in_(tuple(actions)), AuditLog.created_at >= since)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(EVENT_READ_LIMIT)
        )
        return [AuditEventRow(*row) for row in rows]

    def count_recovery_requests_pending_before(self, cutoff: datetime) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(RecoveryRequest)
                .where(RecoveryRequest.status == "PENDING", RecoveryRequest.created_at < cutoff)
            )
            or 0
        )

    def damaged_file_histories(self, *, limit: int) -> list[DamagedFileHistory]:
        """Files that are CORRUPTED or whose newest check failed, with their check history."""
        newest = (
            select(func.max(IntegrityCheck.id))
            .where(IntegrityCheck.file_id == File.id)
            .correlate(File)
            .scalar_subquery()
        )
        files = self.db.execute(
            select(
                File.id,
                File.file_uuid,
                File.original_filename,
                File.status,
                File.created_at,
                User.username,
            )
            .join(User, User.id == File.owner_id)
            .outerjoin(IntegrityCheck, IntegrityCheck.id == newest)
            .where(
                File.status != "DELETED",
                (File.status == "CORRUPTED")
                | IntegrityCheck.result.in_(("MODIFIED", "MISSING", "ERROR")),
            )
            .order_by(File.updated_at.desc(), File.id.desc())
            .limit(limit)
        ).all()
        if not files:
            return []
        history: dict[int, list[tuple[str, datetime]]] = defaultdict(list)
        for file_id, result, at in self.db.execute(
            select(IntegrityCheck.file_id, IntegrityCheck.result, IntegrityCheck.created_at)
            .where(IntegrityCheck.file_id.in_([row[0] for row in files]))
            .order_by(IntegrityCheck.created_at.desc(), IntegrityCheck.id.desc())
        ):
            history[file_id].append((result, at))
        return [
            DamagedFileHistory(
                file_uuid=file_uuid,
                filename=filename,
                owner_username=username,
                status=status,
                uploaded_at=created_at,
                checks=tuple(history.get(file_id, ())),
            )
            for file_id, file_uuid, filename, status, created_at, username in files
        ]
