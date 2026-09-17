from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Positioned, Timestamps, UUIDPrimaryKey
from app.models.card import Card

if TYPE_CHECKING:
    from app.models.board import Board


class BoardList(Base, UUIDPrimaryKey, Timestamps, Positioned):
    """A column on a board. Named BoardList to avoid shadowing the builtin."""

    __tablename__ = "lists"
    __scope_attr__ = "board_id"
    __table_args__ = (
        # DEFERRABLE INITIALLY DEFERRED: the reindex in app/ordering.py shifts a
        # whole range of siblings in one UPDATE, which transiently duplicates a
        # position. Deferring the check to COMMIT lets that be a single bulk
        # statement instead of a carefully ordered row-by-row walk.
        UniqueConstraint(
            "board_id",
            "position",
            name="uq_lists_board_position",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint("position >= 0", name="ck_lists_position_non_negative"),
    )

    board_id: Mapped[UUID] = mapped_column(
        ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)

    board: Mapped["Board"] = relationship(back_populates="lists")
    cards: Mapped[list[Card]] = relationship(
        back_populates="list",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=Card.position,
    )
