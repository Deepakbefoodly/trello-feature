"""A thin authenticated wrapper over the HTTP API for use in tests.

Keeps tests about behaviour rather than about assembling headers and URLs. The
raw verbs return the Response so error cases can assert on status; the `make_*`
helpers assert success and return the parsed body, because a test that is
arranging fixtures should fail loudly if the arrangement itself breaks.
"""

from typing import Any
from uuid import UUID

import httpx
from fastapi.testclient import TestClient

PASSWORD = "correct-horse-battery"


class Api:
    def __init__(self, client: TestClient, token: str, user: dict[str, Any]) -> None:
        self._client = client
        self._headers = {"Authorization": f"Bearer {token}"}
        self.user = user

    @classmethod
    def register(cls, client: TestClient, email: str, password: str = PASSWORD) -> "Api":
        response = client.post(
            "/api/auth/register", json={"email": email, "password": password}
        )
        assert response.status_code == 201, response.text
        body = response.json()
        return cls(client, body["access_token"], body["user"])

    # --- raw verbs -------------------------------------------------------

    def get(self, path: str) -> httpx.Response:
        return self._client.get(path, headers=self._headers)

    def post(self, path: str, json: dict[str, Any] | None = None) -> httpx.Response:
        return self._client.post(path, json=json, headers=self._headers)

    def patch(self, path: str, json: dict[str, Any]) -> httpx.Response:
        return self._client.patch(path, json=json, headers=self._headers)

    def delete(self, path: str) -> httpx.Response:
        return self._client.delete(path, headers=self._headers)

    # --- arrangement helpers ---------------------------------------------

    def make_board(self, title: str = "Board") -> dict[str, Any]:
        response = self.post("/api/boards", {"title": title})
        assert response.status_code == 201, response.text
        return response.json()

    def make_list(self, board_id: UUID | str, title: str = "List") -> dict[str, Any]:
        response = self.post(f"/api/boards/{board_id}/lists", {"title": title})
        assert response.status_code == 201, response.text
        return response.json()

    def make_card(self, list_id: UUID | str, title: str = "Card") -> dict[str, Any]:
        response = self.post(f"/api/lists/{list_id}/cards", {"title": title})
        assert response.status_code == 201, response.text
        return response.json()

    def make_cards(self, list_id: UUID | str, count: int) -> list[dict[str, Any]]:
        """Create `count` cards named c0..c{count-1}, in order."""
        return [self.make_card(list_id, f"c{index}") for index in range(count)]

    def board(self, board_id: UUID | str) -> dict[str, Any]:
        response = self.get(f"/api/boards/{board_id}")
        assert response.status_code == 200, response.text
        return response.json()

    # --- actions under test ----------------------------------------------

    def move_card(
        self, card_id: UUID | str, target_list_id: UUID | str, position: int
    ) -> httpx.Response:
        return self.post(
            f"/api/cards/{card_id}/move",
            {"target_list_id": str(target_list_id), "position": position},
        )

    def move_list(self, list_id: UUID | str, position: int) -> httpx.Response:
        return self.post(f"/api/lists/{list_id}/move", {"position": position})


def card_titles(board: dict[str, Any], list_index: int = 0) -> list[str]:
    """Titles of one list's cards, in stored position order."""
    return [card["title"] for card in board["lists"][list_index]["cards"]]


def positions(board: dict[str, Any], list_index: int = 0) -> list[int]:
    return [card["position"] for card in board["lists"][list_index]["cards"]]


def assert_contiguous(board: dict[str, Any]) -> None:
    """Assert spec invariants 1 and 2 over an entire board payload.

    Lists must occupy 0..n-1 and so must the cards within each list.
    """
    assert [lst["position"] for lst in board["lists"]] == list(range(len(board["lists"]))), (
        "list positions are not contiguous from zero"
    )
    for board_list in board["lists"]:
        actual = [card["position"] for card in board_list["cards"]]
        assert actual == list(range(len(board_list["cards"]))), (
            f"card positions in list {board_list['title']!r} are not contiguous: {actual}"
        )
