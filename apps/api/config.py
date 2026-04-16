from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Agent Platform"
    environment: str = "development"
    google_api_key: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()