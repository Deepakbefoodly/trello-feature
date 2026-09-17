from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ListTitle, ORMModel


class ListCreate(BaseModel):
    title: ListTitle


class ListUpdate(BaseModel):
    title: ListTitle


class ListMove(BaseModel):
    # ge=0 rejects negatives here; the upper bound depends on how many siblings
    # exist and is enforced in app/ordering.py, which is the only place that
    # knows the count.
    position: int = Field(ge=0)


class ListOut(ORMModel):
    id: UUID
    board_id: UUID
    title: str
    position: int
    created_at: datetime
    updated_at: datetime
