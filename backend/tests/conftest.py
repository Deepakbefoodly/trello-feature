"""Test fixtures.

Tests run against a real PostgreSQL database, never SQLite: the ordering code
depends on SELECT ... FOR UPDATE and on DEFERRABLE unique constraints, neither
of which SQLite supports. Testing against a different engine than production
would mean testing a different algorithm.

The database is created and dropped per session, and every table is truncated
before each test, so no test can depend on another's rows.
"""

import os
from pathlib import Path

from sqlalchemy.engine import make_url

BACKEND_ROOT = Path(__file__).resolve().parent.parent
TEST_DB_NAME = "kanban_test"

_DEV_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://kanban:kanban@localhost:5433/kanban"
)
_BASE_URL = make_url(_DEV_URL)
TEST_URL = _BASE_URL.set(database=TEST_DB_NAME)
# "postgres" is the maintenance database; CREATE/DROP DATABASE cannot run while
# connected to the database being created or dropped.
ADMIN_URL = _BASE_URL.set(database="postgres")

# Set before importing anything under `app`: the settings object is cached and
# the engine is built at import time, so this must win before either happens.
os.environ["DATABASE_URL"] = TEST_URL.render_as_string(hide_password=False)

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from alembic import command  # noqa: E402
from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402
from tests.api import Api  # noqa: E402

_TABLES = "users, boards, lists, cards"


def _run(sql: str) -> None:
    admin = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(sql))
    admin.dispose()


@pytest.fixture(scope="session", autouse=True)
def _database() -> None:
    _run(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)')
    _run(f'CREATE DATABASE "{TEST_DB_NAME}"')

    # Build the schema with the real migrations rather than metadata.create_all,
    # so the migrations themselves are exercised on every test run and cannot
    # drift from the models.
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.upgrade(config, "head")

    yield

    engine.dispose()
    _run(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)')


@pytest.fixture(autouse=True)
def _clean_tables() -> None:
    """Truncate before each test, not after.

    A failing test leaves its rows in place for inspection, while the next test
    still starts from empty.
    """
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def api(client: TestClient) -> Api:
    """An authenticated API wrapper for the primary test user."""
    return Api.register(client, "owner@example.com")


@pytest.fixture
def other_api(client: TestClient) -> Api:
    """A second, unrelated user — used for every ownership test."""
    return Api.register(client, "intruder@example.com")
