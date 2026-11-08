from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ARQUIVO_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    DATABASE_URL: str = ""

    CORS_ORIGINS: str = "http://localhost:5173"

    # observabilidade (issue #65); vazios em local e nos testes
    AMBIENTE: str = "local"
    SENTRY_DSN: str = ""
    LOG_LEVEL: str = "INFO"
    # Modo explícito de demonstração. Desligado por padrão; não salva cenários.
    DEMO_CALCULATION_ENABLED: bool = False
    DEMO_CALCULATION_DEFAULTS_JSON: str = ""
    # o Render preenche RENDER_GIT_COMMIT; vira a "release" no Sentry
    VERSAO: str = Field(default="", validation_alias=AliasChoices("VERSAO", "RENDER_GIT_COMMIT"))

    def get_cors_origins(self) -> list[str]:
        return [origem.strip() for origem in self.CORS_ORIGINS.split(",") if origem.strip()]

    model_config = SettingsConfigDict(env_file=ARQUIVO_ENV, env_file_encoding="utf-8", extra="ignore")


settings = Settings()
