"""Database engine and session wiring."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


def search_path_options(schema: str) -> dict[str, str]:
    """Connection arguments pinning every session to one schema.

    Unqualified table names then resolve inside `schema` only, which is what
    lets this application share a PostgreSQL instance with an unrelated one —
    both can own a `users` table and neither sees the other's.

    The schema name is validated as a plain identifier in Settings, because it
    lands in a libpq option string that cannot take a bound parameter.
    """
    return {"options": f"-csearch_path={schema}"}


_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    pool_pre_ping=True,
    connect_args=search_path_options(_settings.db_schema),
)

SessionFactory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a session that is committed on success.

    One request is one transaction. Any exception escaping the route rolls the
    whole thing back, which is what makes invariant 7 hold: a rejected move
    leaves the database exactly as it was.
    """
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
