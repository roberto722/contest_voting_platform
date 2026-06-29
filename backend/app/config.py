from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Contest Voting Platform"
    database_url: str = Field(
        default="postgresql+psycopg://contest:contest@localhost:5432/contest_voting?connect_timeout=3",
        validation_alias="DATABASE_URL",
    )
    backend_cors_origins: str = Field(
        default="http://localhost:5173",
        validation_alias="BACKEND_CORS_ORIGINS",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
