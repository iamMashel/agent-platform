from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Agent Platform"
    environment: str = "development"

    # LLM
    google_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"

    # Langfuse observability
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "http://localhost:3000"


settings = Settings()
