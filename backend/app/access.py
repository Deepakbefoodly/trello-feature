"""Ownership-scoped loaders.

Every board-scoped resource is fetched through here. Ownership is expressed as
part of the WHERE clause rather than as a check after loading, so "does not
exist" and "belongs to someone else" produce the identical empty result and the
identical 404. That makes invariant 6 a property of the query itself: there is
no code path that loads a row first and forgets to check who owns it.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.errors import ApiError
from app.models import Board, BoardList, Card, User


def get_board(session: Session, board_id: UUID, user: User) -> Board:
    board = session.scalar(select(Board).where(Board.id == board_id, Board.owner_id == user.id))
    if board is None:
        raise ApiError.not_found("Board")
    return board


def get_board_detail(session: Session, board_id: UUID, user: User) -> Board:
    """A board with lists and cards eager-loaded, each ordered by position.

    selectinload issues one query per level instead of the N+1 that lazy loading
    would produce while serialising the response.
    """
    board = session.scalar(
        select(Board)
        .where(Board.id == board_id, Board.owner_id == user.id)
        .options(selectinload(Board.lists).selectinload(BoardList.cards))
    )
    if board is None:
        raise ApiError.not_found("Board")
    return board


def list_boards(session: Session, user: User) -> list[Board]:
    return list(
        session.scalars(select(Board).where(Board.owner_id == user.id).order_by(Board.created_at))
    )


def get_list(session: Session, list_id: UUID, user: User) -> BoardList:
    board_list = session.scalar(
        select(BoardList)
        .join(Board, BoardList.board_id == Board.id)
        .where(BoardList.id == list_id, Board.owner_id == user.id)
    )
    if board_list is None:
        raise ApiError.not_found("List")
    return board_list


def get_card(session: Session, card_id: UUID, user: User) -> Card:
    """Load a card, eager-loading its list so `card.board_id` costs no query."""
    card = session.scalar(
        select(Card)
        .join(BoardList, Card.list_id == BoardList.id)
        .join(Board, BoardList.board_id == Board.id)
        .where(Card.id == card_id, Board.owner_id == user.id)
        .options(joinedload(Card.list))
    )
    if card is None:
        raise ApiError.not_found("Card")
    return card
