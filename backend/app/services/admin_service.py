from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.time import to_database_utc, utc_now
from app.domain.auth import ActorContext, RequestContext
from app.domain.enums import SystemRole, UserStatus
from app.domain.errors import AuthorizationError, ConflictError, ResourceNotFoundError
from app.repositories.admin_repository import AdminRepository
from app.repositories.auth_repository import AuthRepository
from app.services.audit_log_service import AuditLogService


class AdminService:
    def __init__(
        self,
        *,
        db: Session,
        repository: AdminRepository | None = None,
        auth_repository: AuthRepository | None = None,
        audit_service: AuditLogService | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.db = db
        self.repository = repository or AdminRepository(db)
        self.auth_repository = auth_repository or AuthRepository(db)
        self.audit = audit_service or AuditLogService(db, clock=clock)
        self.clock = clock

    @staticmethod
    def _require_admin(actor: ActorContext) -> None:
        if actor.role is not SystemRole.ADMIN:
            raise AuthorizationError()

    def list_users(self, *, actor: ActorContext, limit: int, offset: int):
        self._require_admin(actor)
        return self.repository.list_users(limit=limit + 1, offset=offset)

    def list_files(self, *, actor: ActorContext, limit: int, offset: int):
        self._require_admin(actor)
        return self.repository.list_files(limit=limit + 1, offset=offset)

    def set_user_enabled(
        self,
        *,
        actor: ActorContext,
        user_id: UUID,
        enabled: bool,
        context: RequestContext,
    ) -> tuple[object, bool, int]:
        self._require_admin(actor)
        if user_id == actor.user_public_id:
            raise ConflictError("An administrator cannot change their own account status")
        try:
            user = self.repository.lock_user_by_uuid(user_id)
            if user is None or user.status is UserStatus.DELETED:
                raise ResourceNotFoundError()
            desired = UserStatus.ACTIVE if enabled else UserStatus.DISABLED
            changed = user.status is not desired
            revoked_sessions = 0
            now = to_database_utc(self.clock())
            if changed:
                user.status = desired
                user.updated_at = now
                if not enabled:
                    revoked_sessions = self.auth_repository.revoke_all_session_families(
                        user.id,
                        now=now,
                        reason="account_disabled",
                    )
            self.audit.append(
                action="USER_ENABLED" if enabled else "USER_DISABLED",
                result="SUCCESS",
                actor_user_id=actor.user_id,
                target_user_id=user.id,
                resource_type="USER",
                resource_id=str(user_id),
                context_ip_address=context.ip_address,
                context_user_agent=context.user_agent,
                metadata={"changed": changed, "revoked_sessions": revoked_sessions},
            )
            self.db.commit()
            return user, changed, revoked_sessions
        except Exception:
            self.db.rollback()
            raise
