"""Supabase configuration detection (offline: the database is faked)."""

from __future__ import annotations

import base64
import json

import pytest

from app.supabase_config import check_supabase, key_role, resolve_env

URL = "https://abcdefgh.supabase.co"


def _jwt(role: str) -> str:
    def part(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    return f"{part({'alg': 'HS256'})}.{part({'role': role})}.signature"


ANON, SERVICE = _jwt("anon"), _jwt("service_role")


class FakeResult:
    def __init__(self, count):
        self.count = count


class FakeClient:
    """Minimal stand-in for the supabase client: table(...).select(...).limit(...).execute()."""

    def __init__(self, counts, error=None):
        self.counts, self.error, self._table = counts, error, None

    def table(self, name):
        self._table = name
        return self

    def select(self, *args, **kwargs):
        return self

    def limit(self, n):
        return self

    def execute(self):
        if self.error:
            raise self.error
        return FakeResult(self.counts[self._table])


def factory(counts, error=None):
    return lambda url, key: FakeClient(counts, error)


def test_key_role_from_jwt_and_new_style_keys():
    assert key_role(ANON) == "anon"
    assert key_role(SERVICE) == "service_role"
    assert key_role("sb_publishable_abc") == "anon"
    assert key_role("sb_secret_abc") == "service_role"
    assert key_role("not-a-key") == "unknown"
    assert key_role(_jwt("authenticated")) == "unknown"


def test_resolve_env_prefers_service_role_and_ignores_placeholders():
    env = {"SUPABASE_URL": URL, "SUPABASE_ANON_KEY": ANON, "SUPABASE_SERVICE_ROLE_KEY": SERVICE}
    assert resolve_env(env).key_var == "SUPABASE_SERVICE_ROLE_KEY"
    pub_env = {"SUPABASE_URL": URL, "SUPABASE_PUBLISHABLE_KEY": ANON}
    assert resolve_env(pub_env).key_var == "SUPABASE_PUBLISHABLE_KEY"
    assert resolve_env({"SUPABASE_URL": URL, "SUPABASE_KEY": ANON}).key_var == "SUPABASE_KEY"
    assert resolve_env({"SUPABASE_URL": URL, "SUPABASE_ANON_KEY": "your-anon-key-here"}) is None
    assert (
        resolve_env({"SUPABASE_URL": "https://your-project-id.supabase.co", "SUPABASE_KEY": ANON})
        is None
    )
    assert resolve_env({}) is None


def test_check_reports_missing_config():
    result = check_supabase({})
    assert result["configured"] is False and result["ok"] is False


def test_check_ok_when_catalogue_readable():
    env = {"SUPABASE_URL": URL, "SUPABASE_ANON_KEY": ANON}
    result = check_supabase(env, factory({"ingredients": 10, "recipes": 3}))
    assert result["ok"] is True
    assert result["catalogue_rows"] == {"ingredients": 10, "recipes": 3}


def test_check_output_never_contains_secrets():
    env = {"SUPABASE_URL": URL, "SUPABASE_SERVICE_ROLE_KEY": SERVICE, "SUPABASE_ANON_KEY": ANON}
    dumped = json.dumps(check_supabase(env, factory({"ingredients": 1, "recipes": 1})))
    for secret in (URL, SERVICE, ANON, "abcdefgh"):
        assert secret not in dumped


def test_get_repository_raises_in_production_when_unconfigured(monkeypatch):
    from app.storage import repository

    monkeypatch.setattr(repository, "_default_repository", None)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "")

    with pytest.raises(RuntimeError) as exc:
        repository.get_repository()
    assert "chưa được cấu hình" in str(exc.value)

    monkeypatch.setattr(repository, "_default_repository", None)
