from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Basira LMS API"
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/basiralms"
    SUPABASE_URL: str = "https://placeholder.supabase.co"
    SUPABASE_JWT_SECRET: str = "placeholder-jwt-secret"
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_ANON_KEY: str = ""
    COHERE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ADMIN_EMAIL: str = ""
    ADMIN_INITIAL_PASSWORD: str = ""
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    FRONTEND_URL: str = "http://localhost:3000"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "Basira LMS"
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = ""
    FRONTEND_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"],
        min_length=1,
    )
    BOOTSTRAP_ADMIN_ID: str = ""
    BOOTSTRAP_ADMIN_EMAIL: str = ""
    BOOTSTRAP_ADMIN_PASSWORD: str = ""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        extra="ignore",
    )

settings = Settings()
