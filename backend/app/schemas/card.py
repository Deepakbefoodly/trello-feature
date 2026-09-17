from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import CardDescription, CardTitle, ORMModel


class CardCreate(BaseModel):
    title: CardTitle
    description: CardDescription = None


class CardUpdate(BaseModel):
    """Partial update.

    Unlike boards and lists, a card has two independently editable fields, so
    both are optional and only the keys actually present in the request body are
    applied (see routes/cards.py using exclude_unset). That keeps an explicit
    `"description": null` — meaning 'clear it' — distinguishable from omitting
    the key entirely.
    """

    title: CardTitle | None = None
    description: CardDescription = None

    @model_validator(mode="after")
    def _reject_explicit_null_title(self) -> "CardUpdate":
        """Omitting `title` means "leave it alone"; sending null does not.

        A card must always have a title, so an explicit null is a client error
        rather than an instruction to clear the column.
        """
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("title must not be null")
        return self


class CardMove(BaseModel):
    target_list_id: UUID
    position: int = Field(ge=0)


class CardOut(ORMModel):
    id: UUID
    list_id: UUID
    title: str
    description: str | None
    position: int
    created_at: datetime
    updated_at: datetime
