from __future__ import annotations

from datetime import datetime

from sqlalchemy import CHAR, DateTime, Enum, ForeignKey, Index, Text, UniqueConstraint, func
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RecoveryRequest(Base):
    __tablename__ = "recovery_requests"
    __table_args__ = (
        UniqueConstraint("request_uuid", name="uq_recovery_requests_request_uuid"),
        Index("idx_recovery_requests_file_id", "file_id"),
        Index("idx_recovery_requests_requested_by", "requested_by"),
        Index("idx_recovery_requests_approved_by", "approved_by"),
        Index("idx_recovery_requests_status", "status"),
        Index("idx_recovery_requests_created_at", "created_at"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)

    request_uuid: Mapped[str] = mapped_column(CHAR(36), nullable=False)

    file_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey(
            "files.id",
            name="fk_recovery_requests_file",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )

    requested_by: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            name="fk_recovery_requests_requested_by",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    approved_by: Mapped[int | None] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey(
            "users.id",
            name="fk_recovery_requests_approved_by",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        nullable=True,
    )

    reason: Mapped[str] = mapped_column(Text, nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        Enum(
            "PENDING",
            "APPROVED",
            "REJECTED",
            "EXECUTED",
            "CANCELLED",
            name="recovery_request_status_enum",
        ),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    file = relationship("File", back_populates="recovery_requests")
    requester = relationship(
        "User", back_populates="requested_recovery_requests", foreign_keys=[requested_by]
    )
    approver = relationship(
        "User", back_populates="approved_recovery_requests", foreign_keys=[approved_by]
    )
