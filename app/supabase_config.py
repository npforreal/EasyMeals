"""Supabase configuration: resolve env vars, tell which key role is in use, probe the catalogue.

Nothing here returns or logs a key or the project URL; only the name of the variable that was
picked, the role the key grants, and row counts.
"""

import base64
import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass

# Order matters: the privileged key wins when both are set (see get_repository).
KEY_VARS = (
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_ANON_KEY",
    "SUPABASE_PUBLISHABLE_KEY",
    "SUPABASE_KEY",
)
CATALOGUE_TABLES = ("ingredients", "recipes")


@dataclass(frozen=True)
class SupabaseEnv:
    url: str
    key: str
    key_var: str


def load_env() -> dict[str, str]:
    """Process environment on top of a local .env file (the file is absent on Vercel)."""
    try:
        from dotenv import dotenv_values

        file_values = {k: v for k, v in dotenv_values(".env").items() if v is not None}
    except ImportError:
        file_values = {}
    return {**file_values, **os.environ}


def _is_placeholder(value: str) -> bool:
    return value.startswith(("https://your-project", "your-"))


def resolve_env(env: Mapping[str, str]) -> SupabaseEnv | None:
    """The URL and key to use, or None when missing or still a placeholder."""
    url = (env.get("SUPABASE_URL") or "").strip()
    if not url or _is_placeholder(url):
        return None
    for var in KEY_VARS:
        key = (env.get(var) or "").strip()
        if key and not _is_placeholder(key):
            return SupabaseEnv(url=url, key=key, key_var=var)
    return None


def key_role(key: str) -> str:
    """'service_role', 'anon' or 'unknown', read from the key itself (no network, no secrets)."""
    if key.startswith("sb_secret_"):
        return "service_role"
    if key.startswith("sb_publishable_"):
        return "anon"
    try:
        payload = key.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        role = json.loads(base64.urlsafe_b64decode(payload)).get("role")
    except (IndexError, ValueError, TypeError):
        return "unknown"
    return role if role in ("service_role", "anon") else "unknown"


ANON_WARNING = (
    "Đang dùng khoá anon: chỉ đọc được các bảng danh mục (ingredients, recipes) nếu đã chạy "
    "migration 202610230001; dữ liệu cá nhân (tủ, thực đơn) sẽ bị RLS chặn cho đến khi có "
    "đăng nhập Supabase Auth. Không dùng khoá service_role để 'cho chạy' trên server công khai."
)


def check_supabase(
    env: Mapping[str, str],
    client_factory: Callable[[str, str], object] | None = None,
) -> dict:
    """Describe the configuration and try reading the catalogue. Safe to expose: no secrets."""
    resolved = resolve_env(env)
    if resolved is None:
        return {
            "configured": False,
            "ok": False,
            "problem": "SUPABASE_URL hoặc khoá (SUPABASE_ANON_KEY / SUPABASE_SERVICE_ROLE_KEY) "
            "thiếu hoặc còn là placeholder. Kiểm tra biến môi trường của môi trường đang deploy "
            "và redeploy sau khi sửa.",
        }

    role = key_role(resolved.key)
    result: dict = {
        "configured": True,
        "key_var": resolved.key_var,
        "key_role": role,
        "warnings": [ANON_WARNING] if role == "anon" else [],
    }

    if client_factory is None:
        from supabase import create_client as client_factory  # type: ignore[assignment]

    counts: dict[str, int] = {}
    try:
        client = client_factory(resolved.url, resolved.key)
        for table in CATALOGUE_TABLES:
            res = client.table(table).select("id", count="exact").limit(1).execute()  # type: ignore[attr-defined]
            counts[table] = res.count or 0
    except Exception as exc:  # report, never raise: health must stay answerable
        result.update(ok=False, problem=f"Không đọc được Supabase ({type(exc).__name__}).")
        return result

    result["catalogue_rows"] = counts
    empty = [t for t, n in counts.items() if n == 0]
    if empty:
        hint = (
            "khoá anon bị RLS chặn: chạy migration 202610230001_anon_read_catalogue.sql"
            if role == "anon"
            else "chưa có dữ liệu seed"
        )
        result.update(ok=False, problem=f"Đọc được 0 dòng ở: {', '.join(empty)} ({hint}).")
    else:
        result["ok"] = True
    return result


_cache: tuple[float, dict] | None = None


def cached_check(ttl: float = 30.0) -> dict:
    """check_supabase(load_env()) reused for `ttl` seconds so /health cannot hammer the database."""
    import time

    global _cache
    now = time.monotonic()
    if _cache is None or now - _cache[0] > ttl:
        _cache = (now, check_supabase(load_env()))
    return _cache[1]
