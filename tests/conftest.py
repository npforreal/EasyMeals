"""Cấu hình chung cho pytest (EasyMeals).

Tất cả test API dùng FixtureCatalogueRepository (qua dependency override)
để không cần kết nối Supabase thực, đảm bảo scripts/check.sh chạy xanh trên
máy sạch.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_repo
from app.main import app
from app.storage.repository import FixtureCatalogueRepository


@pytest.fixture(autouse=True)
def set_test_env(monkeypatch):
    """Ensure tests run in test environment."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)


@pytest.fixture()
def repo():
    """Repository catalogue fixture trong bộ nhớ cho từng test."""
    repository = FixtureCatalogueRepository()
    app.dependency_overrides[get_repo] = lambda: repository
    try:
        yield repository
    finally:
        app.dependency_overrides.pop(get_repo, None)


@pytest.fixture()
def client(repo):
    """TestClient có dependency get_repo đã được override bởi FixtureCatalogueRepository."""
    return TestClient(app)
