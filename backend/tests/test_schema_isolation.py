"""Sharing one PostgreSQL instance with an unrelated application.

Free hosting tiers typically allow a single database instance, so this app may
have to live alongside something else. Putting its tables in a dedicated schema
is what makes that safe: both applications can own a `users` table, and neither
can see the other's.

These tests cover the mechanism (a per-connection search_path) rather than any
particular deployment.
"""

import pytest
from sqlalchemy import create_engine, text

from app.config import Settings
from app.db import search_path_options

VALID_NAMES = ["kanban", "kanban_app", "app2", "_private"]
INVALID_NAMES = [
    "public; DROP TABLE users",
    "has space",
    "Kanban",
    "9leading_digit",
    "",
    "quote'd",
]


def make_settings(**overrides: str) -> Settings:
    return Settings(
        database_url="postgresql+psycopg://u:p@host/db",
        jwt_secret="test-secret",
        **overrides,
    )


# --- the schema name is interpolated, so it must be constrained -------------


@pytest.mark.parametrize("name", VALID_NAMES)
def test_plain_identifiers_are_accepted(name: str) -> None:
    assert make_settings(db_schema=name).db_schema == name


@pytest.mark.parametrize("name", INVALID_NAMES)
def test_anything_that_is_not_an_identifier_is_rejected(name: str) -> None:
    """The name reaches DDL and a libpq connection option, neither of which can
    be parameterised, so it is validated at the boundary instead."""
    with pytest.raises(ValueError):
        make_settings(db_schema=name)


def test_default_is_the_public_schema() -> None:
    """Local development and the test suite are unaffected by this feature."""
    assert make_settings().db_schema == "public"


# --- the mechanism actually isolates ---------------------------------------


@pytest.fixture
def isolated_engine(request: pytest.FixtureRequest):
    """An engine whose connections resolve to a throwaway schema."""
    from tests.conftest import TEST_URL

    schema = "isolation_check"
    admin = create_engine(TEST_URL)
    with admin.begin() as connection:
        connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    engine = create_engine(TEST_URL, connect_args=search_path_options(schema))
    yield engine, schema, admin

    engine.dispose()
    with admin.begin() as connection:
        connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
    admin.dispose()


def test_tables_are_created_in_the_configured_schema(isolated_engine) -> None:
    engine, schema, admin = isolated_engine

    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id integer primary key)"))

    with admin.connect() as connection:
        landed_in = (
            connection.execute(
                text(
                    "SELECT table_schema FROM information_schema.tables WHERE table_name = 'users'"
                )
            )
            .scalars()
            .all()
        )

    # Two independent `users` tables now coexist: the application's own in
    # public, created by the migrations, and this one. That is precisely the
    # collision that would be fatal without schema isolation.
    assert schema in landed_in
    assert "public" in landed_in


def test_an_unqualified_query_cannot_see_the_other_schema(isolated_engine) -> None:
    """The point of the whole exercise: two apps, one instance, no overlap."""
    engine, schema, admin = isolated_engine

    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id integer primary key)"))
        connection.execute(text("INSERT INTO users (id) VALUES (1)"))

    # public.users is the application's real table, created by the migrations
    # and emptied before each test. It must still be empty.
    with admin.connect() as connection:
        public_rows = connection.execute(text("SELECT count(*) FROM public.users")).scalar()

    assert public_rows == 0
