from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.card import CardOut
from app.schemas.common import BoardTitle, ListTitle, ORMModel


class BoardCreate(BaseModel):
    title: BoardTitle


class BoardUpdate(BaseModel):
    # Title is the only mutable field on a board, so it is required rather than
    # optional: an omitted-title PATCH would be a no-op request with no caller.
    title: BoardTitle


class BoardOut(ORMModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ListWithCards(ORMModel):
    id: UUID
    board_id: UUID
    title: ListTitle
    position: int
    cards: list[CardOut]


class BoardDetail(BoardOut):
    """A board with its full contents.

    Lists and cards arrive already ordered by position via the relationship
    order_by, so the client renders them in array order without re-sorting.
    """

    lists: list[ListWithCards]
