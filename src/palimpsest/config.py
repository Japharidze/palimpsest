import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]  # src/palimpsest/config.py -> repo root
MIGRATIONS_DIR = ROOT / "migrations"
DATA_DIR = ROOT / "data"
EVAL_RESULTS = ROOT / "evals" / "results"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ROOT / ".env"),
        extra="ignore"
    )

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "localhost"
    postgres_port: int

    sec_user_agent: str

    summarizer_provider: str = "anthropic"
    summarizer_model: str = "claude-haiku-4-5-20251001"

    embedding_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"

    agent_provider: str = "anthropic"
    agent_model: str = "claude-haiku-4-5-20251001"

    anthropic_api_key: str | None = None  # only needed when one of providers is anthropic
    openai_api_key: str | None = None     # only needed when one of providers is openai

    @property
    def db_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()  # type: ignore[call-arg]
