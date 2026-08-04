from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.dialects.mysql import BIGINT, VARBINARY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FileKeyWrapping(Base):
    __tablename__ = "file_key_wrappings"
    __table_args__ = (
        Index("idx_file_key_wrappings_file_id", "file_id"),
        Index("idx_file_key_wrappings_recipient_type", "recipient_type"),
        Index("idx_file_key_wrappings_recipient_user_id", "recipient_user_id"),
        Index("idx_file_key_wrappings_user_key_id", "user_key_id"),
        Index("idx_file_key_wrappings_recovery_key_id", "recovery_key_id"),
        Index("idx_file_key_wrappings_status", "status"),
        Index("idx_file_key_wrappings_created_at", "created_at"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)

    file_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey(
            "files.id",
            name="fk_file_key_wrappings_file",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    recipient_type: Mapped[str] = mapped_column(
        Enum("USER", "RECOVERY", name="file_key_recipient_type_enum"),
        nullable=False,
    )

    recipient_user_id: Mapped[int | None] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            name="fk_file_key_wrappings_recipient_user",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=True,
    )
    user_key_id: Mapped[int | None] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey(
            "user_keys.id",
            name="fk_file_key_wrappings_user_key",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        nullable=True,
    )
    recovery_key_id: Mapped[int | None] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey(
            "recovery_keys.id",
            name="fk_file_key_wrappings_recovery_key",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        nullable=True,
    )

    wrapped_file_key: Mapped[bytes] = mapped_column(VARBINARY(1024), nullable=False)
    wrapping_algorithm: Mapped[str] = mapped_column(
        String(50), nullable=False, default="RSA-OAEP-SHA256", server_default="RSA-OAEP-SHA256"
    )

    status: Mapped[str] = mapped_column(
        Enum("ACTIVE", "REVOKED", name="file_key_wrapping_status_enum"),
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    file = relationship("File", back_populates="key_wrappings")
    recipient_user = relationship(
        "User", back_populates="key_wrappings", foreign_keys=[recipient_user_id]
    )
    user_key = relationship("UserKey", back_populates="file_key_wrappings")
    recovery_key = relationship("RecoveryKey", back_populates="file_key_wrappings")
