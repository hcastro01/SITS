from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SQLiteJournalMode = Literal["wal", "delete"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Sistema Integral de Gestión de Trabajo Social"
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./data/trabajo_social.db"
    sqlite_journal_mode: SQLiteJournalMode = "wal"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]
    trusted_hosts: list[str] = ["localhost", "127.0.0.1", "testserver"]
    timezone: str = "America/Guayaquil"
    log_level: str = "INFO"

    # Pendientes de decisión (MIGRACION_FASE_1.md §10): quedan sin valor por defecto útil
    # hasta que se cierren identidad, alojamiento y almacenamiento de archivos.
    private_files_dir: str = "/data/files"
    google_client_id: str | None = None
    google_client_secret: str | None = None
    allowed_google_domain: str | None = None

    # Sesión (Fase 1 §3): cookie HttpOnly. `cookie_secure` debe ser True en cualquier
    # despliegue real por HTTPS; False aquí solo sirve para http://localhost en desarrollo.
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    session_ttl_hours: int = 12
    auth_mode: Literal["password", "development_email"] = "development_email"

    @model_validator(mode="after")
    def validate_production(self):
        if "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS no puede contener '*' cuando se usan credenciales.")
        if self.timezone != "America/Guayaquil":
            raise ValueError("TIMEZONE debe ser America/Guayaquil.")
        if self.environment == "production":
            if self.auth_mode != "password":
                raise ValueError("AUTH_MODE=password es obligatorio en producción.")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE=true es obligatorio en producción.")
            if self.cookie_samesite == "none" and not self.cookie_secure:
                raise ValueError("SameSite=None exige una cookie Secure.")
            if any("localhost" in origin or "127.0.0.1" in origin for origin in self.cors_origins):
                raise ValueError("CORS_ORIGINS de producción no puede contener localhost.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

