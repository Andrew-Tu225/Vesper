from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str

    # Redis
    redis_url: str

    # Slack
    slack_client_id: str = ""
    slack_client_secret: str = ""
    slack_signing_secret: str = ""

    # Google / Gmail
    google_client_id: str = ""
    google_client_secret: str = ""

    # LinkedIn
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""

    # OpenAI
    openai_api_key: str = ""

    # App
    app_secret_key: str  # required — 64-char hex string (32 random bytes); generate: openssl rand -hex 32
    app_base_url: str = "http://localhost:8000"
    app_frontend_url: str = "http://localhost:5173"
    app_env: str = "development"

    @field_validator("app_secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        try:
            key_bytes = bytes.fromhex(v)
        except ValueError as exc:
            raise ValueError("APP_SECRET_KEY must be a valid hex string") from exc
        if len(key_bytes) != 32:
            raise ValueError(
                f"APP_SECRET_KEY must be exactly 64 hex characters (32 bytes); got {len(v)} chars"
            )
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()  # type: ignore[call-arg]
