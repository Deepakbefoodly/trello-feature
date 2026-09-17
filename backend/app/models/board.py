from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Timestamps, UUIDPrimaryKey
from app.models.board_list import BoardList


class Board(Base, UUIDPrimaryKey, Timestamps):
    __tablename__ = "boards"

    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)

    # passive_deletes hands cascading to the database's ON DELETE CASCADE rather
    # than loading every child row into the session to delete it one at a time.
    lists: Mapped[list[BoardList]] = relationship(
        back_populates="board",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=BoardList.position,
    )
