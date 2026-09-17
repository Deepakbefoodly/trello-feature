"""Model package.

Importing every model here guarantees the mapper registry and Alembic's
autogenerate both see the full schema regardless of import order.
"""

from app.models.base import Base
from app.models.board import Board
from app.models.board_list import BoardList
from app.models.card import Card
from app.models.user import User

__all__ = ["Base", "Board", "BoardList", "Card", "User"]
