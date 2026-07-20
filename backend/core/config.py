"""Application configuration — loads from .env file."""
import os
import sys
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_clone_path() -> str:
    """Return a sensible clone path for the current OS."""
    if sys.platform == "win32":
        return "C:/tmp/cue_repos"
    return "/tmp/cue_repos"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "Codebase Understanding Engine"
    environment: str = "development"
    debug: bool = True

    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 1440
    algorithm: str = "HS256"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/codebase_engine"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/codebase_engine"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LLM
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    local_llm_model_path: Optional[str] = None

    # Embeddings
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # Ingestion — Windows-safe default
    clone_base_path: str = Field(default_factory=_default_clone_path)
    max_repo_size_mb: int = 500

    # Rate limiting
    rate_limit_per_minute: int = 60

    # CORS
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:5174"]
    )

    @field_validator("clone_base_path", mode="before")
    @classmethod
    def normalise_clone_path(cls, v: str) -> str:
        """Convert backslashes to forward slashes so pathlib works on Windows."""
        return str(v).replace("\\", "/")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
