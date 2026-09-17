"""Create a demo user with a populated board, for manual checking.

Re-running this deletes and recreates the demo user, so it is safe to run
repeatedly. It touches nothing else in the database.

    python seed.py
"""

from sqlalchemy import select

from app.db import SessionFactory
from app.models import Board, BoardList, Card, User
from app.security import hash_password

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo-password"

CONTENT: dict[str, list[tuple[str, str | None]]] = {
    "Backlog": [
        ("Research competitor pricing", None),
        ("Draft Q3 roadmap", "Needs input from design and support."),
        ("Upgrade CI runners", None),
    ],
    "In progress": [
        ("Rewrite the onboarding email", "Cut it to three paragraphs."),
        ("Fix flaky checkout test", None),
    ],
    "Done": [("Ship the settings page", None)],
}


def main() -> None:
    with SessionFactory() as session:
        existing = session.scalar(select(User).where(User.email == DEMO_EMAIL))
        if existing:
            # Boards, lists and cards go with the user via ON DELETE CASCADE.
            session.delete(existing)
            session.flush()

        # Each flush is what assigns the generated id, which the next level
        # needs as its foreign key.
        user = User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD))
        session.add(user)
        session.flush()

        board = Board(owner_id=user.id, title="Product")
        session.add(board)
        session.flush()

        # Positions are assigned by enumeration, which is what every creation
        # path produces: contiguous and 0-based.
        for list_position, (list_title, cards) in enumerate(CONTENT.items()):
            board_list = BoardList(board_id=board.id, title=list_title, position=list_position)
            session.add(board_list)
            session.flush()

            session.add_all(
                Card(
                    list_id=board_list.id,
                    title=title,
                    description=description,
                    position=card_position,
                )
                for card_position, (title, description) in enumerate(cards)
            )

        session.commit()

    print(f"Seeded {DEMO_EMAIL} / {DEMO_PASSWORD} with the 'Product' board.")


if __name__ == "__main__":
    main()
