"""Unified LLM factory — selects provider based on LLM_PROVIDER env var.

Supported providers (set via LLM_PROVIDER):
  gemini   — Google Gemini via langchain-google-genai  (default)
  openai   — OpenAI GPT via langchain-openai
  ollama   — Local Ollama via langchain-community
  groq     — Groq via langchain-groq (if installed)

Required env vars per provider:
  gemini : GOOGLE_API_KEY, GEMINI_MODEL (default: gemini-2.5-flash)
  openai : OPENAI_API_KEY, OPENAI_MODEL (default: gpt-4o-mini)
  ollama : OLLAMA_BASE_URL (default: http://localhost:11434), OLLAMA_MODEL (default: llama3.2)
  groq   : GROQ_API_KEY, GROQ_MODEL (default: llama-3.1-8b-instant)
"""

from __future__ import annotations

import os


def get_llm(temperature: float = 0.0):  # noqa: ANN201
    """Return a configured LangChain chat model based on LLM_PROVIDER."""
    from apps.api.config import settings

    provider = settings.llm_provider.lower()

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        if settings.google_api_key:
            os.environ["GOOGLE_API_KEY"] = settings.google_api_key
        return ChatGoogleGenerativeAI(model=settings.gemini_model, temperature=temperature)

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        if settings.openai_api_key:
            os.environ["OPENAI_API_KEY"] = settings.openai_api_key
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
        if settings.groq_api_key:
            os.environ["GROQ_API_KEY"] = settings.groq_api_key
        return ChatGroq(model=settings.groq_model, temperature=temperature)

    raise ValueError(
        f"Unknown LLM_PROVIDER '{provider}'. Choose one of: gemini, openai, ollama, groq"
    )
