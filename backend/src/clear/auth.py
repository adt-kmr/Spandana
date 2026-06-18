"""Role-based access: separate operator and citizen scopes (constraint 15)."""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from .config import Settings, get_settings

def _resolve_scope(token: Optional[str], settings: Settings) -> Optional[str]:
    if not token:
        return None
    token = token.removeprefix("Bearer ").strip()
    if token == settings.operator_token:
        return "operator"
    if token == settings.citizen_token:
        return "citizen"
    return None

def require_scope(*allowed: str):
    """FastAPI dependency factory enforcing one of the allowed scopes."""

    def _dep(
        authorization: Optional[str] = Header(default=None),
        settings: Settings = Depends(get_settings),
    ) -> str:
        scope = _resolve_scope(authorization, settings)
        if scope is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="missing or invalid bearer token",
            )
        if scope not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"scope '{scope}' not permitted; requires one of {list(allowed)}",
            )
        return scope

    return _dep
