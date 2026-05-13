from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RecoveryRequest(Base):
    __tablename__ = "recovery_requests"

    request_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.file_id"), nullable=False)
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
    approved_at: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[str | None] = mapped_column(DateTime, nullable=True)
