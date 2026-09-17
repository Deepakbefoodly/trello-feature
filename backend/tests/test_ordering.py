"""The reindex algorithm.

Every test asserts both the resulting order and the contiguity invariants
(spec invariants 1-2), because an order that looks right while leaving a gap or
a duplicate is still broken.
"""

from types import SimpleNamespace

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tests.api import Api, assert_contiguous, card_titles, positions


@pytest.fixture
def board(api: Api) -> SimpleNamespace:
    """A board with two lists; 'todo' holds c0..c3 and 'done' is empty."""
    created = api.make_board("Sprint")
    todo = api.make_list(created["id"], "Todo")
    done = api.make_list(created["id"], "Done")
    cards = api.make_cards(todo["id"], 4)
    return SimpleNamespace(id=created["id"], todo=todo, done=done, cards=cards)


def _card(board: SimpleNamespace, title: str) -> dict:
    return next(card for card in board.cards if card["title"] == title)


# --- creation ---------------------------------------------------------------


def test_new_items_are_appended_to_the_end(api: Api, board: SimpleNamespace) -> None:
    assert positions(api.board(board.id), 0) == [0, 1, 2, 3]
    assert card_titles(api.board(board.id), 0) == ["c0", "c1", "c2", "c3"]


# --- moving a card within its list ------------------------------------------


@pytest.mark.parametrize(
    ("title", "target", "expected"),
    [
        ("c0", 2, ["c1", "c2", "c0", "c3"]),
        ("c3", 1, ["c0", "c3", "c1", "c2"]),
        ("c2", 0, ["c2", "c0", "c1", "c3"]),
        ("c0", 3, ["c1", "c2", "c3", "c0"]),
        ("c1", 1, ["c0", "c1", "c2", "c3"]),
    ],
    ids=["down", "up", "to first", "to last", "to its own position"],
)
def test_move_within_a_list(
    api: Api, board: SimpleNamespace, title: str, target: int, expected: list[str]
) -> None:
    response = api.move_card(_card(board, title)["id"], board.todo["id"], target)

    assert response.status_code == 200
    result = response.json()
    assert card_titles(result, 0) == expected
    assert_contiguous(result)


def test_moving_a_card_to_its_current_position_writes_nothing(
    api: Api, board: SimpleNamespace
) -> None:
    """The no-op branch must not touch the row.

    updated_at is the evidence: SQLAlchemy only emits an UPDATE when an
    attribute actually changes, so an unchanged timestamp proves no write.
    """
    card = _card(board, "c2")
    before = api.get(f"/api/cards/{card['id']}").json()

    api.move_card(card["id"], board.todo["id"], 2)

    after = api.get(f"/api/cards/{card['id']}").json()
    assert after["updated_at"] == before["updated_at"]
    assert after["position"] == 2


# --- moving a card to another list ------------------------------------------


def test_move_to_another_list_closes_the_source_gap(api: Api, board: SimpleNamespace) -> None:
    response = api.move_card(_card(board, "c1")["id"], board.done["id"], 0)

    assert response.status_code == 200
    result = response.json()
    assert card_titles(result, 0) == ["c0", "c2", "c3"]
    assert card_titles(result, 1) == ["c1"]
    assert_contiguous(result)


@pytest.mark.parametrize(
    ("target", "expected_done"),
    [
        (0, ["c0", "d0", "d1"]),
        (1, ["d0", "c0", "d1"]),
        (2, ["d0", "d1", "c0"]),
    ],
    ids=["at first", "in the middle", "appended at the end"],
)
def test_move_into_a_populated_list(
    api: Api, board: SimpleNamespace, target: int, expected_done: list[str]
) -> None:
    """position == len(target) is legal on a cross-list move and means append."""
    api.make_card(board.done["id"], "d0")
    api.make_card(board.done["id"], "d1")

    response = api.move_card(_card(board, "c0")["id"], board.done["id"], target)

    assert response.status_code == 200
    result = response.json()
    assert card_titles(result, 1) == expected_done
    assert card_titles(result, 0) == ["c1", "c2", "c3"]
    assert_contiguous(result)


# --- moving lists -----------------------------------------------------------


@pytest.mark.parametrize(
    ("list_index", "target", "expected"),
    [
        (2, 0, ["Archive", "Todo", "Done"]),
        (0, 2, ["Done", "Archive", "Todo"]),
        (0, 1, ["Done", "Todo", "Archive"]),
    ],
    ids=["left to first", "right to last", "right by one"],
)
def test_move_a_list(
    api: Api, board: SimpleNamespace, list_index: int, target: int, expected: list[str]
) -> None:
    api.make_list(board.id, "Archive")
    lists = api.board(board.id)["lists"]

    response = api.move_list(lists[list_index]["id"], target)

    assert response.status_code == 200
    result = response.json()
    assert [lst["title"] for lst in result["lists"]] == expected
    assert_contiguous(result)


def test_moving_a_list_keeps_its_cards(api: Api, board: SimpleNamespace) -> None:
    response = api.move_list(board.todo["id"], 1)

    result = response.json()
    moved = next(lst for lst in result["lists"] if lst["title"] == "Todo")
    assert card_titles(result, moved["position"]) == ["c0", "c1", "c2", "c3"]
    assert_contiguous(result)


# --- deletion ---------------------------------------------------------------


def test_deleting_a_card_from_the_middle_closes_the_gap(api: Api, board: SimpleNamespace) -> None:
    assert api.delete(f"/api/cards/{_card(board, 'c1')['id']}").status_code == 204

    result = api.board(board.id)
    assert card_titles(result, 0) == ["c0", "c2", "c3"]
    assert positions(result, 0) == [0, 1, 2]
    assert_contiguous(result)


def test_deleting_a_list_removes_its_cards_and_closes_the_gap(
    api: Api, board: SimpleNamespace
) -> None:
    api.make_list(board.id, "Archive")

    assert api.delete(f"/api/lists/{board.todo['id']}").status_code == 204

    result = api.board(board.id)
    assert [lst["title"] for lst in result["lists"]] == ["Done", "Archive"]
    assert_contiguous(result)
    # The cards went with the list rather than being orphaned.
    assert api.get(f"/api/cards/{board.cards[0]['id']}").status_code == 404


# --- rejected moves ---------------------------------------------------------


@pytest.mark.parametrize("target", [4, 99], ids=["one past the end", "far out of range"])
def test_same_list_move_beyond_the_last_index_is_rejected(
    api: Api, board: SimpleNamespace, target: int
) -> None:
    """Within its own list the card already occupies a slot, so n-1 is the
    highest valid index."""
    response = api.move_card(_card(board, "c0")["id"], board.todo["id"], target)

    assert response.status_code == 400
    assert response.json()["error"]["details"]["field"] == "position"


def test_cross_list_move_beyond_append_position_is_rejected(
    api: Api, board: SimpleNamespace
) -> None:
    response = api.move_card(_card(board, "c0")["id"], board.done["id"], 1)

    assert response.status_code == 400


def test_negative_position_is_rejected(api: Api, board: SimpleNamespace) -> None:
    response = api.move_card(_card(board, "c0")["id"], board.todo["id"], -1)

    assert response.status_code == 400


def test_rejected_move_leaves_the_board_untouched(api: Api, board: SimpleNamespace) -> None:
    """Invariant 7: a rejected move changes nothing."""
    before = api.board(board.id)

    api.move_card(_card(board, "c0")["id"], board.todo["id"], 99)

    assert api.board(board.id) == before


def test_card_cannot_move_to_a_list_on_another_board(api: Api, board: SimpleNamespace) -> None:
    """Invariant 3: cards never cross boards.

    The other board belongs to the same user, so ownership alone does not stop
    this; it is reported as 404 so it is indistinguishable from naming a list
    that does not exist.
    """
    other_board = api.make_board("Other")
    foreign_list = api.make_list(other_board["id"], "Elsewhere")
    before = api.board(board.id)

    response = api.move_card(_card(board, "c0")["id"], foreign_list["id"], 0)

    assert response.status_code == 404
    assert api.board(board.id) == before
    assert api.board(other_board["id"])["lists"][0]["cards"] == []


# --- property test ----------------------------------------------------------


@settings(
    max_examples=15,
    deadline=None,
    # The database fixture is function-scoped and intentionally shared across
    # examples; each example works on its own freshly created board.
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    operations=st.lists(
        st.tuples(
            st.sampled_from(["add", "move_card", "delete", "move_list"]),
            st.integers(min_value=0, max_value=50),
            st.integers(min_value=0, max_value=50),
        ),
        min_size=1,
        max_size=12,
    )
)
def test_random_operation_sequences_preserve_contiguity(
    api: Api, operations: list[tuple[str, int, int]]
) -> None:
    """Fuzz the four shift branches.

    The enumerated cases above check the paths that were thought of; this checks
    the ones that were not. Indices are taken modulo the live counts so every
    generated operation is a legal request.
    """
    created = api.make_board("Property")
    for index in range(2):
        api.make_list(created["id"], f"L{index}")

    for kind, first, second in operations:
        state = api.board(created["id"])
        lists = state["lists"]
        cards = [card for board_list in lists for card in board_list["cards"]]

        if kind == "add" or not cards:
            api.make_card(lists[first % len(lists)]["id"], "x")
        elif kind == "move_card":
            card = cards[first % len(cards)]
            target = lists[second % len(lists)]
            same_list = target["id"] == card["list_id"]
            highest = len(target["cards"]) - (1 if same_list else 0)
            api.move_card(card["id"], target["id"], second % (highest + 1))
        elif kind == "delete":
            api.delete(f"/api/cards/{cards[first % len(cards)]['id']}")
        else:
            api.move_list(lists[first % len(lists)]["id"], second % len(lists))

        assert_contiguous(api.board(created["id"]))
