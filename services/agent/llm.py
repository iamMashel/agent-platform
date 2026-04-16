"""Unified LLM factory — selects provider via LLM_PROVIDER env var.

Providers: gemini (default), openai, ollama, groq
"""

from __future__ import annotations

import os
from functools import lru_cache


def _setenv(key: str, value: str | None) -> None:
    if value and key not in os.environ:
        os.environ[key] = value


@lru_cache(maxsize=4)
def get_llm(temperature: float = 0.0):  # noqa: ANN201
    """Return a configured LangChain chat model based on LLM_PROVIDER. Cached per temperature."""
    from apps.api.config import settings

    provider = settings.llm_provider.lower()

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        _setenv("GOOGLE_API_KEY", settings.google_api_key)
        return ChatGoogleGenerativeAI(model=settings.gemini_model, temperature=temperature)

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        _setenv("OPENAI_API_KEY", settings.openai_api_key)
        return ChatOpenAI(model=settings.openai_model, temperature=temperature)

    if provider == "ollama":
        from langchain_community.chat_models import ChatOllama  # type: ignore[import-untyped]

        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=temperature,
        )

    if provider == "groq":
        try:
            from langchain_groq import ChatGroq  # type: ignore[import-untyped]
        except ImportError as err:
            raise ImportError(
                "langchain-groq is not installed. Run: uv add langchain-groq"
            ) from err
        _setenv("GROQ_API_KEY", settings.groq_api_key)
        return ChatGroq(model=settings.groq_model, temperature=temperature)

    raise ValueError(
        f"Unknown LLM_PROVIDER '{provider}'. Choose one of: gemini, openai, ollama, groq"
    )
