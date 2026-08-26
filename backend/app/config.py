from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://cbcr:cbcr_dev_only@db:5432/cbcr"
    cors_origins: str = "http://localhost:5173,http://localhost:4173"
    # Demo-level admin login (POST /auth/login). Not a security boundary — the
    # rest of the API still trusts the X-User-Role header for demo identity
    # switching. Override in .env for a real deployment.
    admin_username: str = "admin"
    admin_password: str = "admin123"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
