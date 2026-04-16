"""Security: optional API key auth + per-IP rate limiting."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address

from apps.api.config import settings

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])

# ── API key auth (optional — disabled when api_keys is empty) ────────────────
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    request: Request,
    api_key: str | None = Security(_api_key_header),
) -> None:
    """Dependency: enforce API key check only when API_KEYS is configured."""
    key_set = settings.api_key_set
    if not key_set:
        return  # auth disabled — no keys configured
    if not api_key or api_key not in key_set:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )


# Convenience dependency alias
RequireApiKey = Depends(verify_api_key)
