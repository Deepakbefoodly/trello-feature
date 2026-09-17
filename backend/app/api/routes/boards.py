from uuid import UUID

from fastapi import APIRouter

from app import access
from app.api.deps import CurrentUser, DbSession
from app.models import Board
from app.schemas.board import BoardCreate, BoardDetail, BoardOut, BoardUpdate

router = APIRouter(prefix="/boards", tags=["boards"])


@router.get("", response_model=list[BoardOut])
def list_boards(session: DbSession, user: CurrentUser) -> list[Board]:
    return access.list_boards(session, user)


@router.post("", response_model=BoardOut, status_code=201)
def create_board(payload: BoardCreate, session: DbSession, user: CurrentUser) -> Board:
    board = Board(owner_id=user.id, title=payload.title)
    session.add(board)
    session.flush()
    return board


@router.get("/{board_id}", response_model=BoardDetail)
def get_board(board_id: UUID, session: DbSession, user: CurrentUser) -> Board:
    return access.get_board_detail(session, board_id, user)


@router.patch("/{board_id}", response_model=BoardOut)
def update_board(
    board_id: UUID, payload: BoardUpdate, session: DbSession, user: CurrentUser
) -> Board:
    board = access.get_board(session, board_id, user)
    board.title = payload.title
    session.flush()
    return board


@router.delete("/{board_id}", status_code=204)
def delete_board(board_id: UUID, session: DbSession, user: CurrentUser) -> None:
    # Lists and cards go with it through ON DELETE CASCADE; no position
    # bookkeeping is needed because boards are not themselves ordered.
    session.delete(access.get_board(session, board_id, user))
