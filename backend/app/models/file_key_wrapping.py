from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.mysql import BIGINT, VARBINARY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FileKeyWrapping(Base):
    __tablename__ = "file_key_wrappings"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)

    file_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("files.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    recipient_type: Mapped[str] = mapped_column(
        Enum("USER", "RECOVERY", name="file_key_recipient_type_enum"),
        nullable=False,
    )

    recipient_user_id: Mapped[int | None] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=True,
    )
    user_key_id: Mapped[int | None] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("user_keys.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    recovery_key_id: Mapped[int | None] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("recovery_keys.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )

    wrapped_file_key: Mapped[bytes] = mapped_column(VARBINARY(1024), nullable=False)
    wrapping_algorithm: Mapped[str] = mapped_column(String(50), nullable=False, default="RSA-OAEP-SHA256", server_default="RSA-OAEP-SHA256")

    status: Mapped[str] = mapped_column(
        Enum("ACTIVE", "REVOKED", name="file_key_wrapping_status_enum"),
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    file = relationship("File", back_populates="key_wrappings")
    recipient_user = relationship("User", back_populates="key_wrappings", foreign_keys=[recipient_user_id])
    user_key = relationship("UserKey", back_populates="file_key_wrappings")
    recovery_key = relationship("RecoveryKey", back_populates="file_key_wrappings")
