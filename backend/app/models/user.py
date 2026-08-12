from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import CHAR, Boolean, DateTime, Enum, Index, String, UniqueConstraint, func, text
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums import SystemRole, UserStatus


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("user_uuid", name="uq_users_user_uuid"),
        UniqueConstraint("username", name="uq_users_username"),
        UniqueConstraint("email", name="uq_users_email"),
        Index("idx_users_role", "role"),
        Index("idx_users_status", "status"),
        Index("idx_users_created_at", "created_at"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    user_uuid: Mapped[str] = mapped_column(
        CHAR(36),
        nullable=False,
        default=lambda: str(uuid4()),
    )

    username: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[SystemRole] = mapped_column(
        Enum(SystemRole, name="user_role_enum"),
        nullable=False,
        default=SystemRole.USER,
        server_default=SystemRole.USER.value,
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status_enum"),
        nullable=False,
        default=UserStatus.ACTIVE,
        server_default=UserStatus.ACTIVE.value,
    )

    email_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
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
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    keys = relationship("UserKey", back_populates="user", cascade="all, delete-orphan")
    key_protection_profile = relationship(
        "UserKeyProtectionProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
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
        overlaps="file_key_wrappings,user_key",
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
    executed_recovery_requests = relationship(
        "RecoveryRequest",
        back_populates="executor",
        foreign_keys="RecoveryRequest.executed_by",
    )
