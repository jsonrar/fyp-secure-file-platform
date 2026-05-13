from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)

    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[str] = mapped_column(
        Enum("USER", "ADMIN", "RECOVERY_OFFICER", name="user_role_enum"),
        nullable=False,
        default="USER",
        server_default="USER",
    )
    status: Mapped[str] = mapped_column(
        Enum("ACTIVE", "DISABLED", "DELETED", name="user_status_enum"),
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
    )

    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    keys = relationship("UserKey", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    owned_files = relationship("File", back_populates="owner", foreign_keys="File.owner_id")

    access_grants = relationship(
        "FileAccessGrant",
        back_populates="user",
        foreign_keys="FileAccessGrant.user_id",
    )
    granted_accesses = relationship(
        "FileAccessGrant",
        back_populates="grantor",
        foreign_keys="FileAccessGrant.granted_by",
    )

    key_wrappings = relationship(
        "FileKeyWrapping",
        back_populates="recipient_user",
        foreign_keys="FileKeyWrapping.recipient_user_id",
    )

    audit_logs = relationship(
        "AuditLog",
        back_populates="actor_user",
        foreign_keys="AuditLog.actor_user_id",
    )
    targeted_audit_logs = relationship(
        "AuditLog",
        back_populates="target_user",
        foreign_keys="AuditLog.target_user_id",
    )

    integrity_checks = relationship(
        "IntegrityCheck",
        back_populates="checked_by_user",
        foreign_keys="IntegrityCheck.checked_by",
    )

    requested_recovery_requests = relationship(
        "RecoveryRequest",
        back_populates="requester",
        foreign_keys="RecoveryRequest.requested_by",
    )
    approved_recovery_requests = relationship(
        "RecoveryRequest",
        back_populates="approver",
        foreign_keys="RecoveryRequest.approved_by",
    )
