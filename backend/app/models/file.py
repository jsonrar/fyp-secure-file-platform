from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class File(Base):
    __tablename__ = "files"
    __table_args__ = (
        UniqueConstraint("file_uuid", name="uq_files_file_uuid"),
        UniqueConstraint("stored_filename", name="uq_files_stored_filename"),
        UniqueConstraint("storage_object_key", name="uq_files_storage_object_key"),
        CheckConstraint(
            "envelope_version >= 1 AND aad_version >= 1 AND revision >= 1",
            name="ck_files_versions",
        ),
        CheckConstraint(
            "file_size_bytes >= 0 AND (encrypted_size_bytes IS NULL OR encrypted_size_bytes >= 0)",
            name="ck_files_nonnegative_sizes",
        ),
        CheckConstraint(
            "encryption_algorithm COLLATE utf8mb4_bin IN "
            "('AES-128-GCM', 'AES-192-GCM', 'AES-256-GCM', 'ChaCha20-Poly1305') "
            "AND OCTET_LENGTH(iv) = 12 AND OCTET_LENGTH(auth_tag) = 16",
            name="ck_files_encryption_envelope",
        ),
        CheckConstraint(
            "encrypted_sha256 REGEXP '^[0-9a-f]{64}$'",
            name="ck_files_encrypted_sha256",
        ),
        CheckConstraint(
            "encrypted_manifest IS NULL OR OCTET_LENGTH(encrypted_manifest) <= 65535",
            name="ck_files_encrypted_manifest_size",
        ),
        CheckConstraint(
            "(status = 'DELETED' AND deleted_at IS NOT NULL) OR "
            "(status IN ('ACTIVE', 'CORRUPTED') AND deleted_at IS NULL)",
            name="ck_files_status_deleted_at",
        ),
        Index("idx_files_owner_id", "owner_id"),
        Index("idx_files_owner_status_created", "owner_id", "status", "created_at", "id"),
        # Serves the shelf and root listings, which are always scoped to one owner.
        Index("idx_files_owner_shelf", "owner_id", "shelf_id"),
        # Declared rather than left to MySQL: a foreign key needs its column as an index's
        # leftmost prefix, and idx_files_owner_shelf does not provide that, so the server
        # would otherwise invent an index whose name and shape nothing here records.
        Index("idx_files_shelf_id", "shelf_id"),
        Index("idx_files_status", "status"),
        Index("idx_files_created_at", "created_at"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )

    id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True
    )

    file_uuid: Mapped[str] = mapped_column(CHAR(36), nullable=False)
    owner_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            name="fk_files_owner",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    # Owner-only organisation. SET NULL rather than CASCADE: deleting a shelf must return
    # its files to the root, never take them with it.
    shelf_id: Mapped[int | None] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey(
            "shelves.id",
            name="fk_files_shelf",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        nullable=True,
    )

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_object_key: Mapped[str] = mapped_column(String(500), nullable=False)

    mime_type: Mapped[str | None] = mapped_column(String(150), nullable=True)

    file_size_bytes: Mapped[int] = mapped_column(mysql.BIGINT(unsigned=True), nullable=False)
    encrypted_size_bytes: Mapped[int | None] = mapped_column(
        mysql.BIGINT(unsigned=True), nullable=True
    )

    envelope_version: Mapped[int] = mapped_column(
        mysql.SMALLINT(unsigned=True), nullable=False, default=1, server_default="1"
    )
    aad_version: Mapped[int] = mapped_column(
        mysql.SMALLINT(unsigned=True), nullable=False, default=1, server_default="1"
    )

    encryption_algorithm: Mapped[str] = mapped_column(
        String(50), nullable=False, default="AES-256-GCM", server_default="AES-256-GCM"
    )

    iv: Mapped[bytes] = mapped_column(mysql.VARBINARY(32), nullable=False)
    auth_tag: Mapped[bytes] = mapped_column(mysql.VARBINARY(32), nullable=False)

    encrypted_sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    encrypted_manifest: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

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
    revision: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True), nullable=False, default=1, server_default="1"
    )

    owner = relationship("User", back_populates="owned_files", foreign_keys=[owner_id])
    shelf = relationship("Shelf", back_populates="files")
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
