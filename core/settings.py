"""One typed Settings object, loaded once, imported everywhere.

No os.environ[...] scattered across the codebase, no secrets in source, and a
hard fail at startup if a required var is missing. SecretStr keeps keys out of
logs and tracebacks (they render as '**********'); the Ellipsis (...) default
makes the two API keys required, surfacing config errors at boot.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",  # vars are named exactly as the aliases below
        extra="ignore",
    )

    # --- Anthropic / Claude (generation + routing) ---
    anthropic_api_key: SecretStr = Field(..., alias="ANTHROPIC_API_KEY")
    model_workhorse: str = Field("claude-sonnet-4-6", alias="MODEL_WORKHORSE")  # $3 / $15
    model_hard: str = Field("claude-opus-4-8", alias="MODEL_HARD")  # $5 / $25
    model_router: str = Field("claude-haiku-4-5", alias="MODEL_ROUTER")  # $1 / $5

    # --- Voyage (embeddings + reranking) ---
    voyage_api_key: SecretStr = Field(..., alias="VOYAGE_API_KEY")
    embed_model: str = Field("voyage-3.5", alias="EMBED_MODEL")  # general prose
    embed_model_code: str = Field("voyage-code-3", alias="EMBED_MODEL_CODE")
    rerank_model: str = Field("rerank-2.5", alias="RERANK_MODEL")
    embed_dim: int = Field(1024, alias="EMBED_DIM")  # MUST equal the vector(N) column width

    # --- Postgres / pgvector ---
    # SQLAlchemy/psycopg3 URL form (langchain + async engine).
    database_url: str = Field(
        "postgresql+psycopg://eih:eih@localhost:5432/eih",
        alias="DATABASE_URL",
    )
    # Plain psycopg DSN (no +driver suffix) for the raw full-text retriever.
    database_url_raw: str = Field(
        "postgresql://eih:eih@localhost:5432/eih",
        alias="DATABASE_URL_RAW",
    )

    # --- LangSmith (optional tracing) ---
    langsmith_tracing: bool = Field(False, alias="LANGSMITH_TRACING")
    langsmith_api_key: SecretStr | None = Field(None, alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field("eih-dev", alias="LANGSMITH_PROJECT")

    # --- Auth & abuse prevention ---
    # auth_enabled=False keeps the demo open (anonymous principal in group "all").
    # Turn it on in production and provide the IdP's RS256 public key.
    auth_enabled: bool = Field(False, alias="AUTH_ENABLED")
    jwt_public_key: SecretStr | None = Field(None, alias="JWT_PUBLIC_KEY")
    jwt_audience: str = Field("eih", alias="JWT_AUDIENCE")
    rate_limit_per_minute: int = Field(20, alias="RATE_LIMIT_PER_MINUTE")
    daily_spend_cap_usd: float = Field(5.0, alias="DAILY_SPEND_CAP_USD")


@lru_cache
def get_settings() -> Settings:
    """Cached singleton — import this everywhere, never construct Settings() directly."""
    return Settings()
