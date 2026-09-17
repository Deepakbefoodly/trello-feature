from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Positioned, Timestamps, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.board_list import BoardList


class Card(Base, UUIDPrimaryKey, Timestamps, Positioned):
    __tablename__ = "cards"
    __table_args__ = (
        # See the note on BoardList: the deferred check is what allows the
        # sibling shift to be one bulk UPDATE.
        UniqueConstraint(
            "list_id",
            "position",
            name="uq_cards_list_position",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint("position >= 0", name="ck_cards_position_non_negative"),
    )

    list_id: Mapped[UUID] = mapped_column(
        ForeignKey("lists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    list: Mapped["BoardList"] = relationship(back_populates="cards")
