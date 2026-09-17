"""Declarative base and the column mixins shared by every table."""

from datetime import datetime
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.orm.attributes import InstrumentedAttribute


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

    A subclass names the foreign key that scopes its ordering — `list_id` for
    cards, `board_id` for lists. Exposing it through `scope_id` / `scope_column`
    lets one generic implementation serve both tables without callers passing
    the column name around as a string they could get wrong.
    """

    __scope_attr__: ClassVar[str]

    position: Mapped[int] = mapped_column(Integer, nullable=False)

    @classmethod
    def scope_column(cls) -> InstrumentedAttribute[UUID]:
        return getattr(cls, cls.__scope_attr__)

    @property
    def scope_id(self) -> UUID:
        return getattr(self, self.__scope_attr__)

    @scope_id.setter
    def scope_id(self, value: UUID) -> None:
        setattr(self, self.__scope_attr__, value)
