from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.security import PasswordManager
from app.core.time import utc_now
from app.domain.auth import ActorContext, RequestContext
from app.domain.enums import UserStatus
from app.domain.errors import (
    AuthenticationError,
    InvalidCurrentPasswordError,
    StorageUnavailableError,
)
from app.repositories.auth_repository import AuthRepository
from app.repositories.file_repository import FileRepository
from app.services.audit_log_service import AuditLogService
from app.services.avatar_storage_service import AvatarStorageService
from app.services.file_storage_service import FileStorageService, StorageObjectError


class AccountDeletionResult:
    """What closing the account actually removed, for the response and the audit entry."""

    def __init__(self, *, files_deleted: int, sessions_revoked: int) -> None:
        self.files_deleted = files_deleted
        self.sessions_revoked = sessions_revoked


class AccountDeletionService:
    """Close an account and destroy what it owns.

    This exists because a forgotten encryption passphrase is unrecoverable by design. The
    offline recovery workflow cannot recover one, and `POST /keys/me/rewrap` cannot set a new
    one without the account master key -- which is exactly what the forgotten passphrase
    protects. So the honest remaining path for someone locked out of their own files is to
    start again, and that needs to be something they can do themselves rather than something
    they ask a teammate to do in the database.

    Deletion is deliberately not reversible and does not try to be. What it is careful about
    is order: the database commit lands before any ciphertext is unlinked, matching
    `FileService.delete`, so a process that dies midway leaves rows marked DELETED with their
    objects still present -- recoverable by the reconcile job -- rather than live rows whose
    ciphertext has already gone.
    """

    def __init__(
        self,
        *,
        db: Session,
        passwords: PasswordManager,
        storage: FileStorageService,
        avatar_storage: AvatarStorageService | None = None,
        auth_repository: AuthRepository | None = None,
        file_repository: FileRepository | None = None,
        audit_service: AuditLogService | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.db = db
        self.passwords = passwords
        self.storage = storage
        self.avatar_storage = avatar_storage
        self.auth = auth_repository or AuthRepository(db)
        self.files = file_repository or FileRepository(db)
        self.audit = audit_service or AuditLogService(db)
        self._clock = clock

    def delete_account(
        self,
        *,
        actor: ActorContext,
        password: str,
        context: RequestContext,
    ) -> AccountDeletionResult:
        """Verify the password, then close the account.

        The password is required even though the caller already holds a valid session. This
        is the one action in the application that cannot be undone, and a session left open
        on an unattended machine should not be enough to trigger it.
        """
        now = self._clock()
        object_keys: list[str] = []
        avatar_object_key: str | None = None

        try:
            user = self.auth.lock_user(actor.user_id)
            if user is None or user.status is not UserStatus.ACTIVE:
                raise AuthenticationError()

            if not self.passwords.verify(password, user.password_hash):
                raise InvalidCurrentPasswordError()

            # Captured before identifiers are released: the row will no longer name the
            # object after commit, and the only safe moment to unlink is afterwards.
            avatar_object_key = getattr(user, "avatar_object_key", None)

            owned = self.files.lock_owned_files(user.id)
            for file_record in owned:
                object_keys.append(file_record.storage_object_key)
                file_record.status = "DELETED"
                file_record.deleted_at = now
                file_record.updated_at = now
                if hasattr(file_record, "revision"):
                    file_record.revision += 1
                # Revoking the grants matters as much as marking the file: a share handed to
                # someone else must not outlive the account that granted it.
                self.files.revoke_file_access_rows(file_record.id, revoked_at=now)

            sessions_revoked = self.auth.revoke_all_session_families(
                user.id,
                now=now,
                reason="account_deleted",
            )

            # Recorded against the still-real username, before it is released.
            self.audit.append(
                action="ACCOUNT_DELETED",
                result="SUCCESS",
                actor_user_id=user.id,
                target_user_id=user.id,
                resource_type="USER",
                resource_id=str(actor.user_public_id),
                context_ip_address=context.ip_address,
                context_user_agent=context.user_agent,
                metadata={
                    "files_deleted": len(owned),
                    "sessions_revoked": sessions_revoked,
                    "username": user.username,
                },
            )

            user.status = UserStatus.DELETED
            # Clear avatar columns with the account so a resurrected UUID cannot claim them.
            if hasattr(user, "avatar_object_key"):
                user.avatar_object_key = None
                user.avatar_content_type = None
                user.avatar_sha256 = None
                user.avatar_bytes = None
                user.avatar_updated_at = None
            self.auth.release_identifiers(user, tombstone=uuid4().hex)

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        # After the durable commit, for the same reason FileService.delete does it here.
        for object_key in object_keys:
            try:
                self.storage.delete_object(object_key)
            except StorageObjectError as exc:
                raise StorageUnavailableError() from exc

        if avatar_object_key and self.avatar_storage is not None:
            self.avatar_storage.delete(avatar_object_key)

        return AccountDeletionResult(
            files_deleted=len(object_keys),
            sessions_revoked=sessions_revoked,
        )
