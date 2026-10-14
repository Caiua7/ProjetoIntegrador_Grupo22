from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ARQUIVO_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    DATABASE_URL: str = ""

    CORS_ORIGINS: str = "http://localhost:5173"

    def get_cors_origins(self) -> list[str]:
        return [origem.strip() for origem in self.CORS_ORIGINS.split(",") if origem.strip()]

    model_config = SettingsConfigDict(env_file=ARQUIVO_ENV, env_file_encoding="utf-8", extra="ignore")


settings = Settings()
