"""Dependencies for EasyMeals API."""

from __future__ import annotations

from typing import Any

from app.storage.repository import Repository, get_repository


def get_repo() -> Repository:
    """Dependency provider returning singleton catalogue repository."""
    return get_repository()


def get_supabase_probe() -> Any:
    """Minimal Supabase health check probe."""
    from app.supabase_config import cached_check

    return cached_check
