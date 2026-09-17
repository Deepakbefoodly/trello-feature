"""Declarative base and the column mixins shared by every table."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UUIDPrimaryKey:
    """UUIDv4 primary key, generated client-side.

    Generating the id in Python rather than the database means a new object has
    its identity before it is flushed, which keeps the ordering code in
    app/ordering.py free of flush-ordering subtleties.
    """

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Positioned:
    """Marks a row as ordered within a parent scope.

    Every table carrying this column is managed exclusively by app/ordering.py,
    which is the single owner of the contiguity invariant (spec invariants 1-2).
    """

    position: Mapped[int] = mapped_column(Integer, nullable=False)
