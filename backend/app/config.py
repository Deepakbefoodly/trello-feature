"""Application settings, loaded once from the environment."""

import re
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    # 24 hours. There are no refresh tokens (out of scope), so this is the full
    # lifetime of a session.
    access_token_ttl_minutes: int = 60 * 24
    cors_origins: str = "http://localhost:5173"
    # PostgreSQL schema holding this application's tables. "public" locally; set
    # to a dedicated name when sharing an instance with another application, so
    # both can own a `users` table without colliding.
    db_schema: str = "public"

    @field_validator("db_schema")
    @classmethod
    def _reject_unsafe_schema_name(cls, value: str) -> str:
        """Constrain the name to a plain identifier.

        It is interpolated into DDL and into a libpq connection option, neither
        of which accepts bound parameters, so validating it here is what keeps
        it from being an injection point.
        """
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", value):
            raise ValueError(
                "db_schema must start with a lowercase letter or underscore and "
                "contain only lowercase letters, digits and underscores"
            )
        return value

    @field_validator("database_url")
    @classmethod
    def _force_psycopg_driver(cls, value: str) -> str:
        """Rewrite the scheme so a hosting platform's URL works untouched.

        Render and similar platforms supply `postgresql://...` or the legacy
        `postgres://...`. SQLAlchemy resolves the former to psycopg2, which this
        project does not install, and the latter is not a registered dialect at
        all — so both fail when the first connection is opened rather than at
        startup.

        Only the scheme is replaced, so a password containing '@' or '/' is left
        intact. Anything that is not a Postgres URL passes through unchanged.
        """
        for scheme in ("postgres://", "postgresql://"):
            if value.startswith(scheme):
                return "postgresql+psycopg://" + value[len(scheme) :]
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached so the environment is read once per process."""
    return Settings()  # type: ignore[call-arg]  # values come from env/.env
