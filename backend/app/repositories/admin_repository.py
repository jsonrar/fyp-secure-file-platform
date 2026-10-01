from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums import SystemRole
from app.models.audit_log import AuditLog
from app.models.file import File
from app.models.file_access_grant import FileAccessGrant
from app.models.integrity_check import IntegrityCheck
from app.models.recovery_request import RecoveryRequest
from app.models.user import User


class AdminRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_users(self, *, limit: int, offset: int) -> list[User]:
        return list(
            self.db.scalars(
                select(User)
                .order_by(User.created_at.desc(), User.id.desc())
                .offset(offset)
                .limit(limit)
            )
        )

    def list_files(self, *, limit: int, offset: int) -> list[tuple[File, User]]:
        rows = self.db.execute(
            select(File, User)
            .join(User, User.id == File.owner_id)
            .order_by(File.created_at.desc(), File.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return [row._tuple() for row in rows]

    # --- dashboard counts -------------------------------------------------------------------
    # Every method below is a single aggregate query that returns numbers, never rows, so the
    # dashboard cannot become a way to read file names, keys or addresses.

    def user_counts_by_status(self) -> dict[str, int]:
        rows = self.db.execute(select(User.status, func.count()).group_by(User.status))
        return {str(getattr(status, "value", status)): count for status, count in rows}

    def count_administrators(self) -> int:
        return self._count(
            select(func.count()).select_from(User).where(User.role == SystemRole.ADMIN)
        )

    def count_users_created_since(self, since: datetime) -> int:
        return self._count(select(func.count()).select_from(User).where(User.created_at >= since))

    def count_users_signed_in_since(self, since: datetime) -> int:
        return self._count(
            select(func.count()).select_from(User).where(User.last_login_at >= since)
        )

    def file_counts_by_status(self) -> dict[str, int]:
        rows = self.db.execute(select(File.status, func.count()).group_by(File.status))
        return {str(status): count for status, count in rows}

    def count_files_uploaded_since(self, since: datetime) -> int:
        return self._count(select(func.count()).select_from(File).where(File.created_at >= since))

    def stored_totals(self) -> tuple[int, int]:
        """Original and stored (ciphertext) bytes across files that still exist."""
        row = self.db.execute(
            select(
                func.coalesce(func.sum(File.file_size_bytes), 0),
                func.coalesce(func.sum(File.encrypted_size_bytes), 0),
            ).where(File.status != "DELETED")
        ).one()
        return int(row[0]), int(row[1])

    def file_counts_by_algorithm(self) -> dict[str, int]:
        rows = self.db.execute(
            select(File.encryption_algorithm, func.count())
            .where(File.status != "DELETED")
            .group_by(File.encryption_algorithm)
        )
        return {str(algorithm): count for algorithm, count in rows}

    def share_counts(self) -> tuple[int, int]:
        """(live grants held by someone other than the owner, distinct files they cover)."""
        row = self.db.execute(
            select(func.count(), func.count(func.distinct(FileAccessGrant.file_id)))
            .select_from(FileAccessGrant)
            .join(File, File.id == FileAccessGrant.file_id)
            .where(
                FileAccessGrant.status == "ACTIVE",
                FileAccessGrant.user_id != File.owner_id,
                File.status != "DELETED",
            )
        ).one()
        return int(row[0]), int(row[1])

    def integrity_check_counts_since(self, since: datetime) -> tuple[int, int]:
        """(checks run, checks that did not come back VALID) since the cutoff."""
        row = self.db.execute(
            select(
                func.count(),
                func.coalesce(func.sum(IntegrityCheck.result != "VALID"), 0),
            ).where(IntegrityCheck.created_at >= since)
        ).one()
        return int(row[0]), int(row[1])

    def count_pending_recovery_requests(self) -> int:
        return self._count(
            select(func.count())
            .select_from(RecoveryRequest)
            .where(RecoveryRequest.status == "PENDING")
        )

    def audit_counts(self, since: datetime) -> tuple[int, int, int]:
        """(all events, events since the cutoff, FAIL events since the cutoff)."""
        row = self.db.execute(
            select(
                func.count(),
                func.coalesce(func.sum(AuditLog.created_at >= since), 0),
                func.coalesce(
                    func.sum((AuditLog.created_at >= since) & (AuditLog.result == "FAIL")), 0
                ),
            )
        ).one()
        return int(row[0]), int(row[1]), int(row[2])

    def recent_audit_failures(self, *, limit: int) -> list[tuple[str, str, datetime, str | None]]:
        """The newest FAIL events as (action, result, when, actor username) and nothing more."""
        rows = self.db.execute(
            select(AuditLog.action, AuditLog.result, AuditLog.created_at, User.username)
            .outerjoin(User, User.id == AuditLog.actor_user_id)
            .where(AuditLog.result == "FAIL")
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit)
        )
        return [
            (action, result, created_at, username) for action, result, created_at, username in rows
        ]

    def _count(self, statement) -> int:
        return int(self.db.scalar(statement) or 0)

    def lock_user_by_uuid(self, user_uuid: UUID) -> User | None:
        return self.db.scalar(
            select(User)
            .where(User.user_uuid == str(user_uuid))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
