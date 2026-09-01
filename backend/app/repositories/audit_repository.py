from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, aliased

from app.models.audit_chain_head import AuditChainHead
from app.models.audit_log import AuditLog
from app.models.file import File
from app.models.file_access_grant import FileAccessGrant
from app.models.file_key_wrapping import FileKeyWrapping
from app.models.user import User

_FILE_RECOVERY_ACTIONS = (
    "RECOVERY_REQUEST_CREATED",
    "RECOVERY_REQUEST_APPROVED",
    "RECOVERY_REQUEST_REJECTED",
    "RECOVERY_REQUEST_CANCELLED",
    "RECOVERY_REQUEST_EXECUTED",
)


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_logs(
        self,
        *,
        actor_user_id: int | None,
        admin: bool,
        limit: int,
        offset: int,
        resource_id: str | None = None,
    ) -> list[tuple[AuditLog, User | None, User | None]]:
        actor_user = aliased(User)
        target_user = aliased(User)
        statement = (
            select(AuditLog, actor_user, target_user)
            .outerjoin(actor_user, actor_user.id == AuditLog.actor_user_id)
            .outerjoin(target_user, target_user.id == AuditLog.target_user_id)
        )
        # One rule, applied the same way whether or not a file was named:
        #
        #   you see what you did, what was done to you, and everything done to a file you
        #   own.
        #
        # The file-scoped query used to skip this filter entirely on the reasoning that
        # AuditQueryService had already checked entitlement. But entitlement is not
        # ownership: a recipient holds an ACTIVE grant, so any recipient could read the
        # whole trail -- learning that other recipients existed and when each of them
        # downloaded. Owning the file is what earns the right to see who touched it.
        if not admin:
            owned_files = select(File.file_uuid).where(File.owner_id == actor_user_id)
            statement = statement.where(
                or_(
                    AuditLog.actor_user_id == actor_user_id,
                    AuditLog.target_user_id == actor_user_id,
                    AuditLog.resource_id.in_(owned_files),
                )
            )
        if resource_id is not None:
            statement = statement.where(
                AuditLog.resource_id == resource_id,
                or_(
                    AuditLog.resource_type.in_(("FILE", "SHARE", "INTEGRITY")),
                    and_(
                        AuditLog.resource_type == "RECOVERY",
                        AuditLog.action.in_(_FILE_RECOVERY_ACTIONS),
                    ),
                ),
            )
        rows = self.db.execute(
            statement.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return [row._tuple() for row in rows]

    def can_access_file(self, user_id: int, file_uuid: UUID) -> bool:
        return (
            self.db.scalar(
                select(File.id)
                .join(
                    FileAccessGrant,
                    (FileAccessGrant.file_id == File.id)
                    & (FileAccessGrant.user_id == user_id)
                    & (FileAccessGrant.status == "ACTIVE"),
                )
                .join(
                    FileKeyWrapping,
                    (FileKeyWrapping.file_id == File.id)
                    & (FileKeyWrapping.recipient_user_id == user_id)
                    & (FileKeyWrapping.status == "ACTIVE"),
                )
                .where(File.file_uuid == str(file_uuid), File.status != "DELETED")
                .limit(1)
            )
            is not None
        )

    def chain_rows(self) -> tuple[list[AuditLog], AuditChainHead | None]:
        logs = list(self.db.scalars(select(AuditLog).order_by(AuditLog.id.asc())))
        head = self.db.scalar(select(AuditChainHead).where(AuditChainHead.id == 1))
        return logs, head
