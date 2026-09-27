from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.mysql import BIGINT, INTEGER
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Shelf(Base):
    """Owner-scoped folder label. Files keep their encryption and grants when moved."""

    __tablename__ = "shelves"
    __table_args__ = (
        UniqueConstraint("shelf_uuid", name="uq_shelves_shelf_uuid"),
        UniqueConstraint("owner_id", "name", name="uq_shelves_owner_name"),
        CheckConstraint("CHAR_LENGTH(name) >= 1", name="ck_shelves_name_length"),
        CheckConstraint("revision >= 1", name="ck_shelves_revision"),
        Index("idx_shelves_owner_id", "owner_id"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    shelf_uuid: Mapped[str] = mapped_column(
        CHAR(36),
        nullable=False,
        default=lambda: str(uuid4()),
    )
    owner_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.id", name="fk_shelves_owner", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("now()"),
        onupdate=func.now(),
    )
    revision: Mapped[int] = mapped_column(
        INTEGER(unsigned=True), nullable=False, default=1, server_default="1"
    )

    owner = relationship("User", back_populates="shelves")
    files = relationship("File", back_populates="shelf")
