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
    app_secret_key: str  # required — 32-byte hex for AES-256-GCM
    app_base_url: str = "http://localhost:8000"
    app_env: str = "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()  # type: ignore[call-arg]
