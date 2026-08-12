from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.file import File
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

    def lock_user_by_uuid(self, user_uuid: UUID) -> User | None:
        return self.db.scalar(
            select(User)
            .where(User.user_uuid == str(user_uuid))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
