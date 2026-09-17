"""Database URL normalisation.

Hosting platforms hand out `postgresql://…` or `postgres://…`. SQLAlchemy maps
the first to psycopg2 — which this project does not install — and the second is
not a registered dialect at all, so both fail at connection time rather than at
startup. Settings rewrites the scheme so the platform's URL works untouched.
"""

import pytest
from sqlalchemy import create_engine

from app.config import Settings

EXPECTED = "postgresql+psycopg://user:secret@db.internal:5432/kanban"


def make_settings(database_url: str) -> Settings:
    return Settings(database_url=database_url, jwt_secret="test-secret")


@pytest.mark.parametrize(
    "given",
    [
        "postgres://user:secret@db.internal:5432/kanban",
        "postgresql://user:secret@db.internal:5432/kanban",
        "postgresql+psycopg://user:secret@db.internal:5432/kanban",
    ],
    ids=["render legacy scheme", "render standard scheme", "already explicit"],
)
def test_every_scheme_normalises_to_psycopg(given: str) -> None:
    assert make_settings(given).database_url == EXPECTED


def test_normalised_url_actually_builds_an_engine() -> None:
    """The point of the rewrite: create_engine raised on both raw forms."""
    engine = create_engine(make_settings("postgresql://u:p@host/db").database_url)

    assert engine.dialect.driver == "psycopg"


def test_credentials_containing_separators_survive() -> None:
    """A generated password can contain '@' or '/'; only the scheme is replaced."""
    given = "postgres://user:p@ss/word@db.internal:5432/kanban"

    assert make_settings(given).database_url == (
        "postgresql+psycopg://user:p@ss/word@db.internal:5432/kanban"
    )


def test_a_non_postgres_url_is_left_alone() -> None:
    assert make_settings("sqlite:///local.db").database_url == "sqlite:///local.db"
