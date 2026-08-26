from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, and_, func, select, update
from sqlalchemy.orm import Session

from app.models.file import File
from app.models.file_access_grant import FileAccessGrant
from app.models.file_key_wrapping import FileKeyWrapping
from app.models.integrity_check import IntegrityCheck
from app.models.recovery_key import RecoveryKey
from app.models.user_key import UserKey


@dataclass(frozen=True, slots=True)
class FileAccessRecord:
    file: File
    grant: FileAccessGrant
    wrapping: FileKeyWrapping
    user_key: UserKey


class FileRepository:
    """SQLAlchemy persistence adapter for encrypted-file use cases.

    The repository deliberately never commits. Transaction ownership remains in the
    application service so a published storage object can be compensated on DB failure.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def flush(self) -> None:
        self.db.flush()

    def add_file(self, file_record: File) -> None:
        self.db.add(file_record)

    def add_grant(self, grant: FileAccessGrant) -> None:
        self.db.add(grant)

    def add_wrapping(self, wrapping: FileKeyWrapping) -> None:
        self.db.add(wrapping)

    def add_integrity_check(self, check: IntegrityCheck) -> None:
        self.db.add(check)

    def file_uuid_exists(self, file_id: UUID) -> bool:
        return (
            self.db.scalar(select(File.id).where(File.file_uuid == str(file_id)).limit(1))
            is not None
        )

    def get_file_by_uuid(self, file_id: UUID, *, include_deleted: bool = False) -> File | None:
        statement = select(File).where(File.file_uuid == str(file_id))
        if not include_deleted:
            statement = statement.where(File.status != "DELETED")
        return self.db.scalar(statement.limit(1))

    def lock_owned_file(self, file_id: UUID, owner_id: int) -> File | None:
        return self.db.scalar(
            select(File)
            .where(File.file_uuid == str(file_id), File.owner_id == owner_id)
            .with_for_update()
        )

    def get_active_user_key(self, user_id: int, key_id: UUID) -> UserKey | None:
        key_uuid_column = getattr(UserKey, "key_uuid", None)
        if key_uuid_column is None:  # pragma: no cover - guarded by current schema migration
            raise RuntimeError("The user_keys.key_uuid migration is required")
        return self.db.scalar(
            select(UserKey)
            .where(
                UserKey.user_id == user_id,
                key_uuid_column == str(key_id),
                UserKey.status == "ACTIVE",
            )
            .limit(1)
        )

    def get_active_recovery_key(self, key_id: UUID) -> RecoveryKey | None:
        return self.db.scalar(
            select(RecoveryKey)
            .where(
                RecoveryKey.key_uuid == str(key_id),
                RecoveryKey.status == "ACTIVE",
            )
            .limit(1)
        )

    @staticmethod
    def _latest_active_wrapping_ids(user_id: int):
        """One active, usable wrapping per file, even for migrated wrapping history."""
        return (
            select(
                FileKeyWrapping.file_id.label("file_id"),
                func.max(FileKeyWrapping.id).label("wrapping_id"),
            )
            .join(UserKey, UserKey.id == FileKeyWrapping.user_key_id)
            .where(
                FileKeyWrapping.recipient_type == "USER",
                FileKeyWrapping.recipient_user_id == user_id,
                FileKeyWrapping.status == "ACTIVE",
                UserKey.user_id == user_id,
                UserKey.status == "ACTIVE",
            )
            .group_by(FileKeyWrapping.file_id)
            .subquery()
        )

    @classmethod
    def _active_access_statement(cls, user_id: int) -> Select:
        wrapping_ids = cls._latest_active_wrapping_ids(user_id)
        return (
            select(File, FileAccessGrant, FileKeyWrapping, UserKey)
            .join(
                FileAccessGrant,
                and_(
                    FileAccessGrant.file_id == File.id,
                    FileAccessGrant.user_id == user_id,
                ),
            )
            .join(wrapping_ids, wrapping_ids.c.file_id == File.id)
            .join(FileKeyWrapping, FileKeyWrapping.id == wrapping_ids.c.wrapping_id)
            .join(UserKey, UserKey.id == FileKeyWrapping.user_key_id)
            .where(
                # CORRUPTED is reachable on purpose. Hiding a damaged file removes the only
                # route its owner has to see the damage, re-check it, or delete it, and the
                # ciphertext is often still intact. Download stays protected by the
                # verification that runs on the way out, not by this filter.
                File.status.in_(("ACTIVE", "CORRUPTED")),
                FileAccessGrant.status == "ACTIVE",
                FileKeyWrapping.status == "ACTIVE",
                UserKey.status == "ACTIVE",
            )
        )

    def get_active_access(self, file_id: UUID, user_id: int) -> FileAccessRecord | None:
        row = self.db.execute(
            self._active_access_statement(user_id).where(File.file_uuid == str(file_id)).limit(1)
        ).one_or_none()
        if row is None:
            return None
        return FileAccessRecord(
            file=row[0],
            grant=row[1],
            wrapping=row[2],
            user_key=row[3],
        )

    @staticmethod
    def _filename_contains(search: str):
        """A LIKE predicate over the filename, with the wildcards taken literally.

        `%` and `_` are LIKE metacharacters, so an unescaped search for `_` matches every
        single character and a search for `%` matches everything. Both are ordinary
        characters in a filename and a user typing one means it literally. The column
        collates `utf8mb4_unicode_ci`, so matching is already case- and accent-insensitive
        without lowering either side and losing the index.
        """
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return File.original_filename.like(f"%{escaped}%", escape="\\")

    def list_active_access(
        self,
        user_id: int,
        *,
        offset: int,
        limit: int,
        search: str | None = None,
    ) -> tuple[list[FileAccessRecord], int]:
        access_statement = self._active_access_statement(user_id)
        if search:
            access_statement = access_statement.where(self._filename_contains(search))
        count_statement = select(func.count()).select_from(
            access_statement.with_only_columns(File.id).order_by(None).subquery()
        )
        total = int(self.db.scalar(count_statement) or 0)
        rows = self.db.execute(
            access_statement.order_by(File.created_at.desc(), File.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return (
            [
                FileAccessRecord(
                    file=row[0],
                    grant=row[1],
                    wrapping=row[2],
                    user_key=row[3],
                )
                for row in rows
            ],
            total,
        )

    def lock_owned_files(self, owner_id: int) -> list[File]:
        """Every file this account still owns, locked for deletion.

        Used only by account deletion, which has to reach files the owner may never have
        opened in this session, so it cannot go one `lock_owned_file` at a time from a list
        the client supplied.
        """
        return list(
            self.db.scalars(
                select(File)
                .where(File.owner_id == owner_id, File.status != "DELETED")
                .with_for_update()
            ).all()
        )

    def revoke_file_access_rows(self, file_pk: int, *, revoked_at: datetime) -> None:
        grant_values: dict[str, object] = {
            "status": "REVOKED",
            "revoked_at": revoked_at,
        }
        if hasattr(FileAccessGrant, "updated_at"):
            grant_values["updated_at"] = revoked_at
        if hasattr(FileAccessGrant, "revision"):
            grant_values["revision"] = FileAccessGrant.revision + 1
        self.db.execute(
            update(FileAccessGrant)
            .where(FileAccessGrant.file_id == file_pk, FileAccessGrant.status == "ACTIVE")
            .values(**grant_values)
        )

        wrapping_values: dict[str, object] = {
            "status": "REVOKED",
            "revoked_at": revoked_at,
        }
        if hasattr(FileKeyWrapping, "updated_at"):
            wrapping_values["updated_at"] = revoked_at
        if hasattr(FileKeyWrapping, "revision"):
            wrapping_values["revision"] = FileKeyWrapping.revision + 1
        self.db.execute(
            update(FileKeyWrapping)
            .where(FileKeyWrapping.file_id == file_pk, FileKeyWrapping.status == "ACTIVE")
            .values(**wrapping_values)
        )
