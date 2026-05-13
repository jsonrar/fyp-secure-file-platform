from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FileKeyWrapping(Base):
    __tablename__ = "file_key_wrappings"

    wrapping_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.file_id"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    key_id: Mapped[int | None] = mapped_column(ForeignKey("user_keys.key_id"), nullable=True)
    wrapped_file_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    wrapping_algorithm: Mapped[str] = mapped_column(String(50), default="RSA-OAEP-SHA256", nullable=False)
    wrapping_type: Mapped[str] = mapped_column(String(30), default="user", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
    revoked_at: Mapped[str | None] = mapped_column(DateTime, nullable=True)
