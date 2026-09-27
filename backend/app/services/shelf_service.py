from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.time import to_api_utc, to_second_resolution_utc, utc_now
from app.domain.auth import ActorContext, RequestContext
from app.domain.errors import (
    FileResourceNotFoundError,
    ShelfNameUnavailableError,
    ShelfNotFoundError,
)
from app.models.file import File
from app.models.shelf import Shelf
from app.schemas.shelf_schema import ShelfDeleteOut, ShelfListOut, ShelfOut
from app.services.audit_log_service import AuditLogService


class ShelfService:
    """Transaction owner for owner-scoped shelves and for filing owned uploads into them.

    Every method is confined to the acting owner, and the only file column a move writes is
    `shelf_id`. Shelves are not an access-control mechanism: they grant nothing, they hold
    no key material, and a recipient of a shared file never sees which shelf its owner keeps
    it on. That is why nothing here touches ciphertext, wrappings, grants, or file identity.
    """

    def __init__(
        self,
        *,
        db: Session,
        audit_service: AuditLogService | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.db = db
        self.audit = audit_service or AuditLogService(db, clock=clock)
        self.clock = clock

    def list_shelves(self, *, actor: ActorContext) -> ShelfListOut:
        shelves = self.db.scalars(
            select(Shelf)
            .where(Shelf.owner_id == actor.user_id)
            .order_by(Shelf.name.asc(), Shelf.id.asc())
        ).all()
        return ShelfListOut(shelves=[self._shelf_out(shelf) for shelf in shelves])

    def create(self, *, actor: ActorContext, name: str, context: RequestContext) -> ShelfOut:
        now = self._now()
        shelf = Shelf(
            shelf_uuid=str(uuid4()),
            owner_id=actor.user_id,
            name=name,
            created_at=now,
            updated_at=now,
            revision=1,
        )
        try:
            self.db.add(shelf)
            # Flushed before the audit append so a duplicate name is refused without
            # leaving an entry in the chain for something that never happened.
            self.db.flush()
            self.audit.append(
                action="SHELF_CREATED",
                result="SUCCESS",
                actor_user_id=actor.user_id,
                target_user_id=actor.user_id,
                resource_type="SHELF",
                resource_id=shelf.shelf_uuid,
                context_ip_address=context.ip_address,
                context_user_agent=context.user_agent,
            )
            result = self._shelf_out(shelf)
            self.db.commit()
            return result
        except IntegrityError as exc:
            self.db.rollback()
            raise ShelfNameUnavailableError() from exc
        except Exception:
            self.db.rollback()
            raise

    def rename(
        self,
        *,
        actor: ActorContext,
        shelf_id: UUID,
        name: str,
        context: RequestContext,
    ) -> ShelfOut:
        try:
            shelf = self._lock_owned_shelf(actor.user_id, shelf_id)
            if shelf.name != name:
                shelf.name = name
                shelf.updated_at = self._now()
                shelf.revision += 1
                self.audit.append(
                    action="SHELF_RENAMED",
                    result="SUCCESS",
                    actor_user_id=actor.user_id,
                    target_user_id=actor.user_id,
                    resource_type="SHELF",
                    resource_id=shelf.shelf_uuid,
                    context_ip_address=context.ip_address,
                    context_user_agent=context.user_agent,
                )
            result = self._shelf_out(shelf)
            self.db.commit()
            return result
        except IntegrityError as exc:
            self.db.rollback()
            raise ShelfNameUnavailableError() from exc
        except Exception:
            self.db.rollback()
            raise

    def delete(
        self,
        *,
        actor: ActorContext,
        shelf_id: UUID,
        context: RequestContext,
    ) -> ShelfDeleteOut:
        """Remove a shelf. Its files return to the root; none of them are deleted."""
        try:
            shelf = self._lock_owned_shelf(actor.user_id, shelf_id)
            public_id = UUID(shelf.shelf_uuid)
            now = self._now()
            # The foreign key would do this on its own, but doing it explicitly is what
            # lets `updated_at` and `revision` move on the rows that actually changed, and
            # reports how many files the caller will now find at the root.
            returned = self._clear_shelf_assignments(
                shelf_pk=shelf.id,
                owner_id=actor.user_id,
                now=now,
            )
            self.audit.append(
                action="SHELF_DELETED",
                result="SUCCESS",
                actor_user_id=actor.user_id,
                target_user_id=actor.user_id,
                resource_type="SHELF",
                resource_id=shelf.shelf_uuid,
                context_ip_address=context.ip_address,
                context_user_agent=context.user_agent,
                metadata={"files_returned_to_root": returned},
            )
            self.db.delete(shelf)
            self.db.commit()
            return ShelfDeleteOut(shelf_id=public_id, files_returned_to_root=returned)
        except Exception:
            self.db.rollback()
            raise

    def move_file(
        self,
        *,
        actor: ActorContext,
        file_id: UUID,
        shelf_id: UUID | None,
        context: RequestContext,
    ) -> UUID | None:
        """File an owned upload onto a shelf, or back to the root. Returns the shelf id.

        Only the owner may move a file, and only onto a shelf they also own -- a share
        recipient has no shelves in someone else's account to move it to, and being able to
        reorganise a file you were merely given access to would rearrange the owner's
        library from outside.
        """
        try:
            file_record = self.db.scalar(
                select(File)
                .where(File.file_uuid == str(file_id), File.owner_id == actor.user_id)
                .with_for_update()
            )
            if file_record is None or file_record.status == "DELETED":
                raise FileResourceNotFoundError()

            target_shelf_pk: int | None = None
            target_shelf_id: UUID | None = None
            if shelf_id is not None:
                shelf = self._lock_owned_shelf(actor.user_id, shelf_id)
                target_shelf_pk = shelf.id
                target_shelf_id = UUID(shelf.shelf_uuid)

            if file_record.shelf_id != target_shelf_pk:
                file_record.shelf_id = target_shelf_pk
                file_record.updated_at = self._now()
                file_record.revision += 1
                self.audit.append(
                    action="FILE_MOVED",
                    result="SUCCESS",
                    actor_user_id=actor.user_id,
                    resource_type="FILE",
                    resource_id=str(file_id),
                    context_ip_address=context.ip_address,
                    context_user_agent=context.user_agent,
                    metadata={
                        "shelf_id": str(target_shelf_id) if target_shelf_id else None,
                    },
                )
            self.db.commit()
            return target_shelf_id
        except Exception:
            self.db.rollback()
            raise

    def resolve_owned_shelf_pk(self, *, owner_id: int, shelf_id: UUID) -> int:
        """Translate a public shelf id into its row id, refusing another owner's shelf."""
        shelf_pk = self.db.scalar(
            select(Shelf.id).where(
                Shelf.shelf_uuid == str(shelf_id),
                Shelf.owner_id == owner_id,
            )
        )
        if shelf_pk is None:
            raise ShelfNotFoundError()
        return int(shelf_pk)

    def _clear_shelf_assignments(self, *, shelf_pk: int, owner_id: int, now: datetime) -> int:
        result = self.db.execute(
            update(File)
            .where(File.shelf_id == shelf_pk, File.owner_id == owner_id)
            .values(shelf_id=None, updated_at=now, revision=File.revision + 1)
        )
        return int(result.rowcount or 0)

    def _lock_owned_shelf(self, owner_id: int, shelf_id: UUID) -> Shelf:
        shelf = self.db.scalar(
            select(Shelf)
            .where(Shelf.shelf_uuid == str(shelf_id), Shelf.owner_id == owner_id)
            .with_for_update()
        )
        if shelf is None:
            raise ShelfNotFoundError()
        return shelf

    @staticmethod
    def _shelf_out(shelf: Shelf) -> ShelfOut:
        return ShelfOut(
            shelf_id=UUID(str(shelf.shelf_uuid)),
            name=shelf.name,
            created_at=to_api_utc(shelf.created_at),
            updated_at=to_api_utc(shelf.updated_at),
        )

    def _now(self) -> datetime:
        return to_second_resolution_utc(self.clock())
