"""Invariant 6: one user can never reach another user's data.

Every case asserts 404 rather than 403. Returning 403 would confirm that the id
exists, leaking the presence of other users' boards; "not found" and "not yours"
are deliberately indistinguishable.
"""

from collections.abc import Callable
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from tests.api import Api


@pytest.fixture
def owned(api: Api) -> SimpleNamespace:
    """A board, list and card belonging to the primary user."""
    board = api.make_board("Private")
    board_list = api.make_list(board["id"], "Private list")
    card = api.make_card(board_list["id"], "Private card")
    return SimpleNamespace(board=board, list=board_list, card=card)


# Each entry is a request made by the *other* user against the primary user's
# resources. Covers read, update, delete and both move endpoints.
INTRUSIONS: dict[str, Callable[[Api, SimpleNamespace], httpx.Response]] = {
    "get board": lambda other, own: other.get(f"/api/boards/{own.board['id']}"),
    "update board": lambda other, own: other.patch(
        f"/api/boards/{own.board['id']}", {"title": "Hijacked"}
    ),
    "delete board": lambda other, own: other.delete(f"/api/boards/{own.board['id']}"),
    "create list on board": lambda other, own: other.post(
        f"/api/boards/{own.board['id']}/lists", {"title": "Intruder list"}
    ),
    "update list": lambda other, own: other.patch(
        f"/api/lists/{own.list['id']}", {"title": "Hijacked"}
    ),
    "delete list": lambda other, own: other.delete(f"/api/lists/{own.list['id']}"),
    "move list": lambda other, own: other.move_list(own.list["id"], 0),
    "create card in list": lambda other, own: other.post(
        f"/api/lists/{own.list['id']}/cards", {"title": "Intruder card"}
    ),
    "get card": lambda other, own: other.get(f"/api/cards/{own.card['id']}"),
    "update card": lambda other, own: other.patch(
        f"/api/cards/{own.card['id']}", {"title": "Hijacked"}
    ),
    "delete card": lambda other, own: other.delete(f"/api/cards/{own.card['id']}"),
    "move card": lambda other, own: other.move_card(own.card["id"], own.list["id"], 0),
}


@pytest.mark.parametrize("intrusion", INTRUSIONS.values(), ids=list(INTRUSIONS))
def test_another_users_resources_are_not_found(
    other_api: Api,
    owned: SimpleNamespace,
    intrusion: Callable[[Api, SimpleNamespace], httpx.Response],
) -> None:
    response = intrusion(other_api, owned)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_a_failed_intrusion_changes_nothing(
    api: Api, other_api: Api, owned: SimpleNamespace
) -> None:
    before = api.board(owned.board["id"])

    for intrusion in INTRUSIONS.values():
        intrusion(other_api, owned)

    assert api.board(owned.board["id"]) == before


def test_board_list_only_shows_your_own_boards(
    api: Api, other_api: Api, owned: SimpleNamespace
) -> None:
    other_api.make_board("Mine")

    boards = other_api.get("/api/boards").json()

    assert [board["title"] for board in boards] == ["Mine"]


def test_unknown_ids_are_also_not_found(api: Api) -> None:
    """The same 404 as an owned-by-someone-else id, by construction."""
    missing = uuid4()

    assert api.get(f"/api/boards/{missing}").status_code == 404
    assert api.get(f"/api/cards/{missing}").status_code == 404
    assert api.move_list(missing, 0).status_code == 404


def test_malformed_uuid_is_a_validation_error(api: Api) -> None:
    response = api.get("/api/boards/not-a-uuid")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
