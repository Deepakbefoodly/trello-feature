from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKey


class User(Base, UUIDPrimaryKey):
    __tablename__ = "users"

    # Emails are lowercased and trimmed by the request schema before they reach
    # here, so a plain unique index is sufficient for case-insensitive identity.
    # 320 is the maximum length of an RFC 5321 address.
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
