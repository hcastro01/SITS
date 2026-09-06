from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Sistema Integral de Gestión de Trabajo Social"
    database_url: str = "sqlite:///./data/trabajo_social.db"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]

    # Pendientes de decisión (MIGRACION_FASE_1.md §10): quedan sin valor por defecto útil
    # hasta que se cierren identidad, alojamiento y almacenamiento de archivos.
    private_files_dir: str = "/data/files"
    google_client_id: str | None = None
    google_client_secret: str | None = None
    allowed_google_domain: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()

