"""Alembic environment.

Online mode only. Offline (--sql) migration generation is not used by this
project, so it is not implemented rather than left as dead boilerplate.
"""

from sqlalchemy import create_engine, text

from alembic import context
from app.config import get_settings
from app.db import search_path_options
from app.models import Base

target_metadata = Base.metadata


def run_migrations() -> None:
    settings = get_settings()

    engine = create_engine(
        settings.database_url,
        connect_args=search_path_options(settings.db_schema),
    )

    with engine.connect() as connection:
        # PostgreSQL happily accepts a search_path naming a schema that does not
        # exist — it simply resolves to nothing — so the schema is created here
        # rather than being assumed. Idempotent, and it means a fresh deployment
        # needs no manual setup step.
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{settings.db_schema}"'))
        connection.commit()

        # alembic_version is created unqualified, so search_path puts it in the
        # same schema as the tables it tracks. Two applications sharing an
        # instance therefore keep entirely separate migration histories.
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

    engine.dispose()


run_migrations()
