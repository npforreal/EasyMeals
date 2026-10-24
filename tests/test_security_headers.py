"""Tests for security response headers (S4)."""

from fastapi.testclient import TestClient


def test_security_headers_present_on_all_responses(client: TestClient):
    """Every HTTP response includes essential hardening security headers."""
    res = client.get("/")
    headers = res.headers

    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "camera=()" in headers.get("Permissions-Policy", "")

    csp = headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    # Script-src must NOT contain unsafe-inline
    assert "script-src 'self'" in csp
    assert "'unsafe-inline'" not in csp.split("script-src")[1].split(";")[0]


def test_cache_control_on_sensitive_pages(client: TestClient):
    """Dynamic and authenticated pages set no-store Cache-Control header."""
    res = client.get("/")
    assert "no-store" in res.headers.get("Cache-Control", "")
