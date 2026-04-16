from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Agent Platform"
    environment: str = "development"

    # ── LLM provider ─────────────────────────────────────────────────────────
    # Options: gemini | openai | ollama | groq
    llm_provider: str = "gemini"

    # Gemini
    google_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"

    # OpenAI
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # Ollama (local)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # Groq
    groq_api_key: str | None = None
    groq_model: str = "llama-3.1-8b-instant"

    # ── Langfuse observability ────────────────────────────────────────────────
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "http://localhost:3000"

    # ── Redis (session memory persistence) ───────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Postgres (agent run history) ─────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://agent:agent@localhost:5432/agent"

    # ── Security ──────────────────────────────────────────────────────────────
    # Comma-separated list of valid API keys; empty = auth disabled
    api_keys: str = ""

    @property
    def api_key_set(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}

    # ── Rate limiting ─────────────────────────────────────────────────────────
    # Requests per minute per IP for /agent/run
    rate_limit: str = "30/minute"


settings = Settings()
