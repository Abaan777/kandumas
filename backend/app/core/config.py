"""Application configuration loaded from environment variables / .env file."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> backend/app/core -> backend/app -> backend -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_RAW_DIR = REPO_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = REPO_ROOT / "data" / "processed"
ML_ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "ml" / "artifacts"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MySQL
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "kandumas"
    mysql_password: str = "change-me"
    mysql_database: str = "kandumas_db"
    database_url: str | None = None

    # Auth
    jwt_secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Used to build the password-reset link (see api/auth.py forgot_password). Update
    # this once the frontend is deployed (WBS Phase 6).
    frontend_base_url: str = "http://localhost:5173"

    # Password reset tokens
    password_reset_token_expire_minutes: int = 30

    # Demo accounts
    demo_admin_password: str = "Admin123!"
    demo_officer_password: str = "Officer123!"
    demo_fisherman_password: str = "Fisherman123!"

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
