from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class IntegrityCheck(Base):
    __tablename__ = "integrity_checks"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)

    file_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("files.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    checked_by: Mapped[int | None] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )

    expected_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    actual_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    result: Mapped[str] = mapped_column(
        Enum("VALID", "MODIFIED", "MISSING", "ERROR", name="integrity_check_result_enum"),
        nullable=False,
    )

    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    file = relationship("File", back_populates="integrity_checks")
    checked_by_user = relationship("User", back_populates="integrity_checks", foreign_keys=[checked_by])
