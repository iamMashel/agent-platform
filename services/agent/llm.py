"""Unified LLM factory — selects provider via LLM_PROVIDER env var.

Providers: gemini (default), openai, ollama, groq, litellm
LiteLLM gives access to 100+ models via a single LITELLM_MODEL env var.
"""

from __future__ import annotations

import os
from functools import lru_cache


def _setenv(key: str, value: str | None) -> None:
    if value and key not in os.environ:
        os.environ[key] = value


def _with_retry(llm):  # noqa: ANN001, ANN201
    """Wrap a LangChain chat model with 3-attempt exponential-backoff retry.

    Handles transient provider errors (5xx, network timeouts, brief rate limits)
    without surfacing them to the user. If all 3 attempts fail, the exception
    propagates normally.
    """
    return llm.with_retry(
        retry_if_exception_type=(Exception,),
        wait_exponential_jitter=True,
        stop_after_attempt=3,
    )


@lru_cache(maxsize=8)
def get_llm(temperature: float = 0.0, task: str = "default"):  # noqa: ANN201
    """Return a configured LangChain chat model based on LLM_PROVIDER.

    Args:
        temperature: Sampling temperature. 0 = deterministic (used by planner).
        task: "planner" uses a cheap fast model; "default" uses the main model.
              Cached per (temperature, task) pair.
    """
    from apps.api.config import settings

    provider = settings.llm_provider.lower()

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        _setenv("GOOGLE_API_KEY", settings.google_api_key)
        model = settings.gemini_model
        return _with_retry(ChatGoogleGenerativeAI(model=model, temperature=temperature))

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        _setenv("OPENAI_API_KEY", settings.openai_api_key)
        return _with_retry(ChatOpenAI(model=settings.openai_model, temperature=temperature))

    if provider == "ollama":
        from langchain_community.chat_models import ChatOllama  # type: ignore[import-untyped]

        return _with_retry(
            ChatOllama(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
                temperature=temperature,
            )
        )

    if provider == "groq":
        try:
            from langchain_groq import ChatGroq  # type: ignore[import-untyped]
        except ImportError as err:
            raise ImportError(
                "langchain-groq is not installed. Run: uv add langchain-groq"
            ) from err
        _setenv("GROQ_API_KEY", settings.groq_api_key)
        return _with_retry(ChatGroq(model=settings.groq_model, temperature=temperature))

    if provider == "litellm":
        from langchain_community.chat_models import ChatLiteLLM  # type: ignore[import-untyped]

        model = settings.resolved_planner_model if task == "planner" else settings.litellm_model
        return _with_retry(ChatLiteLLM(model=model, temperature=temperature))

    raise ValueError(
        f"Unknown LLM_PROVIDER '{provider}'. Choose one of: gemini, openai, ollama, groq, litellm"
    )
