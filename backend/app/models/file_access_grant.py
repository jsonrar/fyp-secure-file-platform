from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FileAccessGrant(Base):
    __tablename__ = "file_access_grants"
    __table_args__ = (
        UniqueConstraint("file_id", "user_id", name="uq_file_access_grants_file_user"),
    )

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)

    file_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("files.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    granted_by: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
    )

    permission_level: Mapped[str] = mapped_column(
        Enum("OWNER", "VIEWER", "EDITOR", name="file_permission_level_enum"),
        nullable=False,
        default="VIEWER",
        server_default="VIEWER",
    )

    can_download: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    can_share: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    can_revoke: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    can_manage: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")

    status: Mapped[str] = mapped_column(
        Enum("ACTIVE", "REVOKED", name="file_access_grant_status_enum"),
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    file = relationship("File", back_populates="access_grants")
    user = relationship("User", back_populates="access_grants", foreign_keys=[user_id])
    grantor = relationship("User", back_populates="granted_accesses", foreign_keys=[granted_by])
