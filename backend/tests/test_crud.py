"""Board, list and card CRUD, and the input constraints on each."""

import pytest

from tests.api import Api

BLANK_TITLES = ["", "   ", "\t\n"]


# --- boards -----------------------------------------------------------------


def test_create_and_read_a_board(api: Api) -> None:
    created = api.make_board("Roadmap")

    assert created["title"] == "Roadmap"
    assert api.board(created["id"])["lists"] == []


def test_board_list_is_empty_for_a_new_user(api: Api) -> None:
    assert api.get("/api/boards").json() == []


def test_rename_a_board(api: Api) -> None:
    board = api.make_board("Old")

    response = api.patch(f"/api/boards/{board['id']}", {"title": "New"})

    assert response.status_code == 200
    assert response.json()["title"] == "New"


def test_deleting_a_board_removes_its_lists_and_cards(api: Api) -> None:
    board = api.make_board()
    board_list = api.make_list(board["id"])
    card = api.make_card(board_list["id"])

    assert api.delete(f"/api/boards/{board['id']}").status_code == 204

    assert api.get(f"/api/boards/{board['id']}").status_code == 404
    assert api.get(f"/api/cards/{card['id']}").status_code == 404


def test_board_titles_are_trimmed(api: Api) -> None:
    assert api.make_board("  Padded  ")["title"] == "Padded"


@pytest.mark.parametrize("title", BLANK_TITLES, ids=["empty", "spaces", "whitespace"])
def test_blank_board_title_is_rejected(api: Api, title: str) -> None:
    response = api.post("/api/boards", {"title": title})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_overlong_board_title_is_rejected(api: Api) -> None:
    assert api.post("/api/boards", {"title": "a" * 101}).status_code == 400


# --- lists ------------------------------------------------------------------


def test_create_and_rename_a_list(api: Api) -> None:
    board = api.make_board()
    created = api.make_list(board["id"], "Backlog")

    renamed = api.patch(f"/api/lists/{created['id']}", {"title": "Icebox"})

    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Icebox"
    assert renamed.json()["position"] == 0


@pytest.mark.parametrize("title", BLANK_TITLES, ids=["empty", "spaces", "whitespace"])
def test_blank_list_title_is_rejected(api: Api, title: str) -> None:
    board = api.make_board()

    assert api.post(f"/api/boards/{board['id']}/lists", {"title": title}).status_code == 400


# --- cards ------------------------------------------------------------------


def test_create_a_card_with_a_description(api: Api) -> None:
    board = api.make_board()
    board_list = api.make_list(board["id"])

    response = api.post(
        f"/api/lists/{board_list['id']}/cards",
        {"title": "Ship it", "description": "With tests."},
    )

    assert response.status_code == 201
    assert response.json()["description"] == "With tests."
    assert response.json()["position"] == 0


def test_a_card_without_a_description_stores_null(api: Api) -> None:
    board = api.make_board()
    card = api.make_card(api.make_list(board["id"])["id"])

    assert card["description"] is None


def test_blank_description_is_stored_as_null(api: Api) -> None:
    """One representation of 'no description' rather than both "" and null."""
    board = api.make_board()
    board_list = api.make_list(board["id"])

    response = api.post(
        f"/api/lists/{board_list['id']}/cards", {"title": "T", "description": "   "}
    )

    assert response.json()["description"] is None


def test_overlong_card_fields_are_rejected(api: Api) -> None:
    board = api.make_board()
    board_list = api.make_list(board["id"])

    too_long_title = api.post(f"/api/lists/{board_list['id']}/cards", {"title": "a" * 201})
    too_long_body = api.post(
        f"/api/lists/{board_list['id']}/cards", {"title": "O", "description": "a" * 5001}
    )

    assert too_long_title.status_code == 400
    assert too_long_body.status_code == 400


# --- partial card updates ---------------------------------------------------


def test_updating_only_the_description_keeps_the_title(api: Api) -> None:
    board = api.make_board()
    card = api.make_card(api.make_list(board["id"])["id"], "Keep me")

    response = api.patch(f"/api/cards/{card['id']}", {"description": "Added later"})

    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == "Keep me"
    assert updated["description"] == "Added later"
    assert updated["position"] == card["position"]


def test_explicit_null_description_clears_it(api: Api) -> None:
    board = api.make_board()
    board_list = api.make_list(board["id"])
    created = api.post(
        f"/api/lists/{board_list['id']}/cards", {"title": "T", "description": "Remove me"}
    ).json()

    response = api.patch(f"/api/cards/{created['id']}", {"description": None})

    assert response.status_code == 200
    assert response.json()["description"] is None


def test_explicit_null_title_is_rejected(api: Api) -> None:
    """Omitting title means 'leave it'; sending null is a client error, since a
    card must always have one."""
    board = api.make_board()
    card = api.make_card(api.make_list(board["id"])["id"])

    response = api.patch(f"/api/cards/{card['id']}", {"title": None})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_empty_patch_leaves_the_card_unchanged(api: Api) -> None:
    board = api.make_board()
    card = api.make_card(api.make_list(board["id"])["id"], "Untouched")

    response = api.patch(f"/api/cards/{card['id']}", {})

    assert response.status_code == 200
    assert response.json() == card
