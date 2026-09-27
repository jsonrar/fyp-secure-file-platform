from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.time import to_api_utc, to_second_resolution_utc, utc_now
from app.domain.auth import ActorContext, RequestContext
from app.domain.errors import (
    AuthenticationError,
    AvatarNotFoundError,
    AvatarUpdateRateLimitedError,
    StorageUnavailableError,
)
from app.domain.enums import UserStatus
from app.models.user import User
from app.services.audit_log_service import AuditLogService
from app.services.avatar_storage_service import (
    AvatarObjectError,
    AvatarObjectMissingError,
    AvatarStorageService,
)


@dataclass(frozen=True, slots=True)
class AvatarState:
    """What the account's picture is now, for the JSON surfaces."""

    has_avatar: bool
    content_type: str | None = None
    size_bytes: int | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class AvatarImage:
    content_type: str
    sha256: str
    body: bytes


class AvatarService:
    """Transaction owner for the optional account profile picture."""

    def __init__(
        self,
        *,
        db: Session,
        settings: Settings,
        storage: AvatarStorageService | None = None,
        audit_service: AuditLogService | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.db = db
        self.settings = settings
        self.storage = storage or AvatarStorageService(settings=settings)
        self.audit = audit_service or AuditLogService(db, clock=clock)
        self.clock = clock

    async def upload(
        self,
        *,
        actor: ActorContext,
        upload: UploadFile,
        context: RequestContext,
    ) -> AvatarState:
        """Validate and store a new picture, then remove the one it replaced.

        The image is validated and written before any row is locked, as `FileService` does
        with ciphertext. Reading a client-paced multipart body while holding a lock on the
        caller's `users` row would let one slow upload stall that account's own logins and
        refreshes; a rejected request instead costs one bounded write that is unlinked
        immediately below.

        The old object is unlinked only after the commit, also matching `FileService`: an
        orphaned image is inert and reconcilable, whereas a row pointing at an object that
        has already gone would serve nothing for a picture the user believes they have.
        """
        stored = await self.storage.store(upload, user_uuid=actor.user_public_id)
        now = self._now()
        replaced_object_key: str | None = None
        try:
            user = self._require_active_user(actor)
            self._require_interval_elapsed(user, now=now)
            replaced_object_key = user.avatar_object_key
            user.avatar_object_key = stored.object_key
            user.avatar_content_type = stored.content_type
            user.avatar_sha256 = stored.sha256
            user.avatar_bytes = stored.size_bytes
            user.avatar_updated_at = now
            user.updated_at = now
            self.audit.append(
                action="AVATAR_UPLOADED",
                result="SUCCESS",
                actor_user_id=actor.user_id,
                target_user_id=actor.user_id,
                resource_type="USER",
                resource_id=str(actor.user_public_id),
                context_ip_address=context.ip_address,
                context_user_agent=context.user_agent,
                metadata={
                    "content_type": stored.content_type,
                    "size_bytes": stored.size_bytes,
                    "replaced": replaced_object_key is not None,
                },
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            self._discard(stored.object_key)
            raise

        if replaced_object_key is not None:
            self._discard(replaced_object_key)
        return self._state(
            has_avatar=True,
            content_type=stored.content_type,
            size_bytes=stored.size_bytes,
            updated_at=now,
        )

    def get_image(self, *, actor: ActorContext) -> AvatarImage:
        user = self.db.scalar(select(User).where(User.id == actor.user_id))
        if user is None or user.avatar_object_key is None or user.avatar_content_type is None:
            raise AvatarNotFoundError()
        try:
            body = self.storage.read_bytes(user.avatar_object_key)
        except AvatarObjectMissingError as exc:
            # The row survived its object. Reporting this as "no avatar" is the honest
            # answer to the caller and lets them upload a replacement.
            raise AvatarNotFoundError() from exc
        except AvatarObjectError as exc:
            raise StorageUnavailableError() from exc
        return AvatarImage(
            content_type=user.avatar_content_type,
            sha256=user.avatar_sha256 or "",
            body=body,
        )

    def get_state(self, *, actor: ActorContext) -> AvatarState:
        user = self.db.scalar(select(User).where(User.id == actor.user_id))
        if user is None or user.avatar_object_key is None:
            return self._state(has_avatar=False)
        return self._state(
            has_avatar=True,
            content_type=user.avatar_content_type,
            size_bytes=user.avatar_bytes,
            updated_at=user.avatar_updated_at,
        )

    def delete(self, *, actor: ActorContext, context: RequestContext) -> AvatarState:
        user = self._require_active_user(actor)
        removed_object_key = user.avatar_object_key
        if removed_object_key is None:
            # Idempotent: an account with no picture is already in the requested state, and
            # a repeated click should not be an error.
            return self._state(has_avatar=False)

        now = self._now()
        try:
            user.avatar_object_key = None
            user.avatar_content_type = None
            user.avatar_sha256 = None
            user.avatar_bytes = None
            user.avatar_updated_at = None
            user.updated_at = now
            self.audit.append(
                action="AVATAR_DELETED",
                result="SUCCESS",
                actor_user_id=actor.user_id,
                target_user_id=actor.user_id,
                resource_type="USER",
                resource_id=str(actor.user_public_id),
                context_ip_address=context.ip_address,
                context_user_agent=context.user_agent,
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        # After the durable commit, for the same reason as file deletion.
        self._discard(removed_object_key)
        return self._state(has_avatar=False)

    def _require_active_user(self, actor: ActorContext) -> User:
        user = self.db.scalar(select(User).where(User.id == actor.user_id).with_for_update())
        if user is None or user.status != UserStatus.ACTIVE:
            raise AuthenticationError()
        return user

    def _require_interval_elapsed(self, user: User, *, now: datetime) -> None:
        interval = self.settings.AVATAR_MIN_INTERVAL_SECONDS
        if interval <= 0 or user.avatar_updated_at is None:
            return
        available_at = user.avatar_updated_at + timedelta(seconds=interval)
        if available_at > now:
            retry_after = max(1, math.ceil((available_at - now).total_seconds()))
            raise AvatarUpdateRateLimitedError(retry_after_seconds=retry_after)

    def _discard(self, object_key: str) -> None:
        try:
            self.storage.delete(object_key)
        except AvatarObjectError:
            # Preserve the use-case outcome. An image nothing references is inert, and the
            # reconcile job is the place that cleans up after local storage misbehaves.
            return

    @staticmethod
    def _state(
        *,
        has_avatar: bool,
        content_type: str | None = None,
        size_bytes: int | None = None,
        updated_at: datetime | None = None,
    ) -> AvatarState:
        return AvatarState(
            has_avatar=has_avatar,
            content_type=content_type,
            size_bytes=size_bytes,
            updated_at=to_api_utc(updated_at),
        )

    def _now(self) -> datetime:
        return to_second_resolution_utc(self.clock())
