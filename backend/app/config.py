"""Application settings, loaded once from the environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    # 24 hours. There are no refresh tokens (out of scope), so this is the full
    # lifetime of a session.
    access_token_ttl_minutes: int = 60 * 24
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached so the environment is read once per process."""
    return Settings()  # type: ignore[call-arg]  # values come from env/.env
