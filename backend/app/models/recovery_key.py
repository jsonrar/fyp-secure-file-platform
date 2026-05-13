from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RecoveryKey(Base):
    __tablename__ = "recovery_keys"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)

    public_key_pem: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False, default="RSA-OAEP-SHA256", server_default="RSA-OAEP-SHA256")
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    status: Mapped[str] = mapped_column(
        Enum("ACTIVE", "REVOKED", name="recovery_key_status_enum"),
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    file_key_wrappings = relationship("FileKeyWrapping", back_populates="recovery_key")
