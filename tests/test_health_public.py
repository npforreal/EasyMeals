"""Tests for public health endpoint security (S3)."""

from __future__ import annotations

import os
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_health_public_minimal_in_production():
    """Unauthenticated /health only returns minimal status.

    Never leaks internals, database details, or env var names.
    """
    with patch.dict(os.environ, {"APP_ENV": "production"}):
        import importlib

        import app.main

        importlib.reload(app.main)
        prod_client = TestClient(app.main.app)

        res = prod_client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["service"] == "easymeals"
        # Must NOT expose supabase object or credentials
        assert "supabase" not in data
        assert "key_var" not in data

    # Reload back
    with patch.dict(os.environ, {"APP_ENV": "test"}):
        importlib.reload(app.main)
