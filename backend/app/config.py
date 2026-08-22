"""Central configuration loaded from environment / .env.

Everything tunable lives here so that no module reaches for os.environ
directly and tests can override settings deterministically.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "ParcelPilot AI Support Agent"
    environment: str = "development"

    # LLM
    llm_provider: str = "anthropic"  # 'anthropic' | 'gemini' | 'openrouter'
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemini-2.5-flash"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Auth - HMAC secret for signed login tokens (set a strong value in prod)
    auth_secret: str = "dev-only-change-me-parcelpilot"

    # Data locations
    data_pack_dir: str = "./data_pack"
    sqlite_db_path: str = "./data/parcelpilot.db"
    vector_store_dir: str = "./data/chroma"

    # Time reference: None => use snapshot time from workbook README sheet
    snapshot_time_override: str | None = None

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]

    @staticmethod
    def _resolve(path_value: str) -> str:
        from app.ingestion.run import resolve_path

        return str(resolve_path(path_value))

    @property
    def sqlite_db_path_resolved(self) -> str:
        return self._resolve(self.sqlite_db_path)

    @property
    def vector_store_dir_resolved(self) -> str:
        return self._resolve(self.vector_store_dir)

    @property
    def data_pack_dir_resolved(self) -> str:
        return self._resolve(self.data_pack_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()
