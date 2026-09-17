"""Initial schema: users, boards, lists, cards

Revision ID: 0001
Revises:
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "boards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_boards"),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name="fk_boards_owner_id", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_boards_owner_id", "boards", ["owner_id"])

    op.create_table(
        "lists",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("board_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_lists"),
        sa.ForeignKeyConstraint(
            ["board_id"], ["boards.id"], name="fk_lists_board_id", ondelete="CASCADE"
        ),
        sa.CheckConstraint("position >= 0", name="ck_lists_position_non_negative"),
        # Deferred so the reindex can shift a range of siblings in one UPDATE
        # while positions are transiently duplicated mid-transaction.
        sa.UniqueConstraint(
            "board_id",
            "position",
            name="uq_lists_board_position",
            deferrable=True,
            initially="DEFERRED",
        ),
    )
    op.create_index("ix_lists_board_id", "lists", ["board_id"])

    op.create_table(
        "cards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("list_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_cards"),
        sa.ForeignKeyConstraint(
            ["list_id"], ["lists.id"], name="fk_cards_list_id", ondelete="CASCADE"
        ),
        sa.CheckConstraint("position >= 0", name="ck_cards_position_non_negative"),
        sa.UniqueConstraint(
            "list_id",
            "position",
            name="uq_cards_list_position",
            deferrable=True,
            initially="DEFERRED",
        ),
    )
    op.create_index("ix_cards_list_id", "cards", ["list_id"])


def downgrade() -> None:
    op.drop_table("cards")
    op.drop_table("lists")
    op.drop_table("boards")
    op.drop_table("users")
