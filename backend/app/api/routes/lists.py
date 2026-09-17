from uuid import UUID

from fastapi import APIRouter

from app import access, ordering
from app.api.deps import CurrentUser, DbSession
from app.models import Board, BoardList
from app.schemas.board import BoardDetail
from app.schemas.list import ListCreate, ListMove, ListOut, ListUpdate

router = APIRouter(tags=["lists"])


@router.post("/boards/{board_id}/lists", response_model=ListOut, status_code=201)
def create_list(
    board_id: UUID, payload: ListCreate, session: DbSession, user: CurrentUser
) -> BoardList:
    board = access.get_board(session, board_id, user)
    # Lock before reading the count: without it two concurrent creates could
    # both compute the same next position and collide at commit.
    ordering.lock_board(session, board.id)

    board_list = BoardList(
        board_id=board.id,
        title=payload.title,
        position=ordering.next_position(session, BoardList, board.id),
    )
    session.add(board_list)
    session.flush()
    return board_list


@router.patch("/lists/{list_id}", response_model=ListOut)
def update_list(
    list_id: UUID, payload: ListUpdate, session: DbSession, user: CurrentUser
) -> BoardList:
    board_list = access.get_list(session, list_id, user)
    board_list.title = payload.title
    session.flush()
    return board_list


@router.delete("/lists/{list_id}", status_code=204)
def delete_list(list_id: UUID, session: DbSession, user: CurrentUser) -> None:
    board_list = access.get_list(session, list_id, user)
    ordering.lock_board(session, board_list.board_id)

    # Read these before the delete: the instance is expired afterwards.
    board_id, removed_position = board_list.board_id, board_list.position

    session.delete(board_list)
    session.flush()
    ordering.close_gap(session, BoardList, board_id, removed_position)


@router.post("/lists/{list_id}/move", response_model=BoardDetail)
def move_list(list_id: UUID, payload: ListMove, session: DbSession, user: CurrentUser) -> Board:
    board_list = access.get_list(session, list_id, user)
    board_id = board_list.board_id
    ordering.lock_board(session, board_id)

    # Lists never reparent, so the target scope is the board they are already on.
    ordering.move(session, board_list, board_id, payload.position)

    return access.get_board_detail(session, board_id, user)
