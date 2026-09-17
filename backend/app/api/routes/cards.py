from uuid import UUID

from fastapi import APIRouter

from app import access, ordering
from app.api.deps import CurrentUser, DbSession
from app.errors import ApiError
from app.models import Board, Card
from app.schemas.board import BoardDetail
from app.schemas.card import CardCreate, CardMove, CardOut, CardUpdate

router = APIRouter(tags=["cards"])


@router.post("/lists/{list_id}/cards", response_model=CardOut, status_code=201)
def create_card(
    list_id: UUID, payload: CardCreate, session: DbSession, user: CurrentUser
) -> Card:
    board_list = access.get_list(session, list_id, user)
    ordering.lock_board(session, board_list.board_id)

    card = Card(
        list_id=board_list.id,
        title=payload.title,
        description=payload.description,
        position=ordering.next_position(session, Card, board_list.id),
    )
    session.add(card)
    session.flush()
    return card


@router.get("/cards/{card_id}", response_model=CardOut)
def get_card(card_id: UUID, session: DbSession, user: CurrentUser) -> Card:
    return access.get_card(session, card_id, user)


@router.patch("/cards/{card_id}", response_model=CardOut)
def update_card(
    card_id: UUID, payload: CardUpdate, session: DbSession, user: CurrentUser
) -> Card:
    card = access.get_card(session, card_id, user)

    # exclude_unset keeps an omitted key from overwriting a stored value, while
    # still allowing an explicit `"description": null` to clear the field.
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(card, field, value)

    session.flush()
    return card


@router.delete("/cards/{card_id}", status_code=204)
def delete_card(card_id: UUID, session: DbSession, user: CurrentUser) -> None:
    card = access.get_card(session, card_id, user)
    ordering.lock_board(session, card.board_id)

    list_id, removed_position = card.list_id, card.position

    session.delete(card)
    session.flush()
    ordering.close_gap(session, Card, list_id, removed_position)


@router.post("/cards/{card_id}/move", response_model=BoardDetail)
def move_card(
    card_id: UUID, payload: CardMove, session: DbSession, user: CurrentUser
) -> Board:
    card = access.get_card(session, card_id, user)
    # Captured before the move: afterwards the card points at its new list.
    board_id = card.board_id
    ordering.lock_board(session, board_id)

    target_list = access.get_list(session, payload.target_list_id, user)
    if target_list.board_id != board_id:
        # A list on another of this user's boards exists and is theirs, so the
        # ownership query above lets it through — but moving a card across
        # boards would break invariant 3. Reported as not-found so the response
        # is identical to naming a list that does not exist at all.
        raise ApiError.not_found("List")

    ordering.move(session, card, target_list.id, payload.position)

    return access.get_board_detail(session, board_id, user)
