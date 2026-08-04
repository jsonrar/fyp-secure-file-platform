from __future__ import annotations

from datetime import datetime

from sqlalchemy import CHAR, DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserKey(Base):
    __tablename__ = "user_keys"
    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_user_keys_fingerprint"),
        Index("idx_user_keys_user_id", "user_id"),
        Index("idx_user_keys_status", "status"),
        Index("idx_user_keys_created_at", "created_at"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            name="fk_user_keys_user",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    public_key_pem: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm: Mapped[str] = mapped_column(
        String(50), nullable=False, default="RSA-OAEP-SHA256", server_default="RSA-OAEP-SHA256"
    )
    fingerprint: Mapped[str] = mapped_column(CHAR(64), nullable=False)

    status: Mapped[str] = mapped_column(
        Enum("ACTIVE", "REVOKED", name="user_key_status_enum"),
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user = relationship("User", back_populates="keys")
    file_key_wrappings = relationship("FileKeyWrapping", back_populates="user_key")
