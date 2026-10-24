"""Tests for Swagger / OpenAPI docs disabled in production mode (S2) and hard security defaults."""

from __future__ import annotations

import importlib
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


def test_docs_disabled_in_production():
    with patch.dict(os.environ, {"APP_ENV": "production"}):
        import app.main

        importlib.reload(app.main)
        prod_client = TestClient(app.main.app)

        res_docs = prod_client.get("/docs")
        assert res_docs.status_code == 404

        res_redoc = prod_client.get("/redoc")
        assert res_redoc.status_code == 404

        res_openapi = prod_client.get("/openapi.json")
        assert res_openapi.status_code == 404

    # Reload back to normal test environment
    with patch.dict(os.environ, {"APP_ENV": "test"}):
        importlib.reload(app.main)


def test_service_role_key_rejected_at_runtime():
    """Server must refuse to run if SUPABASE_SERVICE_ROLE_KEY is present in runtime."""
    with patch.dict(os.environ, {"SUPABASE_SERVICE_ROLE_KEY": "secret_service_key_123"}):
        import app.main

        with pytest.raises(RuntimeError) as exc:
            importlib.reload(app.main)
        assert "bị cấm tuyệt đối" in str(exc.value)

    # Reload back
    with patch.dict(os.environ, {"APP_ENV": "test"}):
        importlib.reload(app.main)
