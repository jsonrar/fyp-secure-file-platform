from __future__ import annotations

from datetime import datetime

from sqlalchemy import CHAR, DateTime, Enum, ForeignKey, Index, String, UniqueConstraint, func, text
from sqlalchemy.dialects.mysql import BIGINT, VARBINARY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class File(Base):
    __tablename__ = "files"
    __table_args__ = (
        UniqueConstraint("file_uuid", name="uq_files_file_uuid"),
        UniqueConstraint("stored_filename", name="uq_files_stored_filename"),
        Index("idx_files_owner_id", "owner_id"),
        Index("idx_files_status", "status"),
        Index("idx_files_created_at", "created_at"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)

    file_uuid: Mapped[str] = mapped_column(CHAR(36), nullable=False)
    owner_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            name="fk_files_owner",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_object_key: Mapped[str] = mapped_column(String(500), nullable=False)

    mime_type: Mapped[str | None] = mapped_column(String(150), nullable=True)

    file_size_bytes: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    encrypted_size_bytes: Mapped[int | None] = mapped_column(BIGINT(unsigned=True), nullable=True)

    encryption_algorithm: Mapped[str] = mapped_column(
        String(50), nullable=False, default="AES-256-GCM", server_default="AES-256-GCM"
    )

    iv: Mapped[bytes] = mapped_column(VARBINARY(32), nullable=False)
    auth_tag: Mapped[bytes] = mapped_column(VARBINARY(32), nullable=False)

    encrypted_sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)

    status: Mapped[str] = mapped_column(
        Enum("ACTIVE", "DELETED", "CORRUPTED", name="file_status_enum"),
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("now()"),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    owner = relationship("User", back_populates="owned_files", foreign_keys=[owner_id])
    key_wrappings = relationship(
        "FileKeyWrapping", back_populates="file", cascade="all, delete-orphan"
    )
    access_grants = relationship(
        "FileAccessGrant", back_populates="file", cascade="all, delete-orphan"
    )
    integrity_checks = relationship(
        "IntegrityCheck", back_populates="file", cascade="all, delete-orphan"
    )
    recovery_requests = relationship(
        "RecoveryRequest", back_populates="file", cascade="all, delete-orphan"
    )
