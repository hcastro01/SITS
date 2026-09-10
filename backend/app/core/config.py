from functools import lru_cache
from pathlib import Path, PureWindowsPath
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

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
    session_ttl_hours: int = Field(default=12, ge=1, le=168)
    auth_mode: Literal["password", "development_email"] = "development_email"
    login_max_attempts: int = Field(default=5, ge=3, le=100)
    login_window_seconds: int = Field(default=300, ge=60, le=3600)

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
            origins = [urlsplit(origin) for origin in self.cors_origins]
            if not origins or any(
                origin.scheme != "https"
                or not origin.netloc
                or origin.username is not None
                or origin.password is not None
                or origin.path not in {"", "/"}
                or origin.query
                or origin.fragment
                for origin in origins
            ):
                raise ValueError(
                    "CORS_ORIGINS de producción debe contener orígenes HTTPS exactos y sin rutas."
                )
            if not self.trusted_hosts or any(
                "*" in host
                or "://" in host
                or "/" in host
                or "localhost" in host
                or "127.0.0.1" in host
                for host in self.trusted_hosts
            ):
                raise ValueError(
                    "TRUSTED_HOSTS de producción debe contener únicamente hosts públicos exactos."
                )

            database = make_url(self.database_url)
            database_path = database.database
            is_absolute = bool(
                database_path
                and (
                    Path(database_path).is_absolute()
                    or PureWindowsPath(database_path).is_absolute()
                )
            )
            if database.get_backend_name() != "sqlite" or database_path == ":memory:" or not is_absolute:
                raise ValueError(
                    "DATABASE_URL de producción debe apuntar a un archivo SQLite absoluto y persistente."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

