"""Test hồi quy cho các mục cứng hoá L1–L5 (vòng bảo mật 8)."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.storage.repository import _sanitize_postgrest_search

ROOT = Path(__file__).resolve().parents[1]


def _csp(res) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in res.headers["Content-Security-Policy"].split(";"):
        part = part.strip()
        if part:
            name, _, value = part.partition(" ")
            out[name] = value
    return out


def test_l1_csp_locks_base_form_object_and_connect(client: TestClient):
    csp = _csp(client.get("/"))
    assert csp.get("base-uri") == "'none'"
    assert csp.get("form-action") == "'self'"
    assert csp.get("object-src") == "'none'"
    # Trình duyệt không bao giờ gọi thẳng Supabase; chỉ backend gọi.
    assert csp.get("connect-src") == "'self'"
    assert "supabase" not in client.get("/").headers["Content-Security-Policy"]


def test_l2_hsts_only_over_https(client: TestClient):
    plain = client.get("/")
    assert "Strict-Transport-Security" not in plain.headers

    secure = TestClient(app, base_url="https://testserver").get("/")
    hsts = secure.headers.get("Strict-Transport-Security", "")
    assert "max-age=31536000" in hsts
    assert "includeSubDomains" in hsts

    forwarded = client.get("/", headers={"x-forwarded-proto": "https"})
    assert "max-age=31536000" in forwarded.headers.get("Strict-Transport-Security", "")


def test_l3_ingredient_search_length_limited(client: TestClient):
    assert client.get("/api/ingredients", params={"q": "a" * 100}).status_code == 200
    assert client.get("/api/ingredients", params={"q": "a" * 101}).status_code == 422


def test_l3_underscore_wildcard_stripped():
    assert "_" not in _sanitize_postgrest_search("th_t_b_")
    assert _sanitize_postgrest_search("thịt bò") == "thịt bò"


def test_l4_android_manifest_minimal_permissions():
    manifest = (ROOT / "mobile/android/app/src/main/AndroidManifest.xml").read_text(
        encoding="utf-8"
    )
    perms = set(re.findall(r'uses-permission android:name="([^"]+)"', manifest))
    assert "android.permission.INTERNET" not in perms
    # F2: chỉ thêm quyền thông báo cục bộ (xin khi người dùng bật nhắc việc).
    assert "android.permission.POST_NOTIFICATIONS" in perms
    assert perms == {"android.permission.VIBRATE", "android.permission.POST_NOTIFICATIONS"}
    # Receiver nhắc việc không được export cho ứng dụng khác.
    assert re.search(
        r'<receiver[^>]*android:name="\.data\.notifications\.ReminderReceiver"[^>]*android:exported="false"',
        manifest,
        re.S,
    )


def test_l5_service_worker_cache_scope_limited():
    sw = (ROOT / "app/static/sw.js").read_text(encoding="utf-8")
    assert 'CACHE_NAME = "easymeals-v4"' in sw
    # Chỉ lưu cache đường dẫn trong danh sách app shell hoặc /api/catalogue.
    assert "isCacheable" in sw
    assert '"/api/catalogue"' in sw
    assert re.search(r"if \(!isCacheable\(", sw) or "isCacheable(url" in sw
    # Không còn lưu cache vô điều kiện mọi phản hồi 200.
    assert "MAX_RUNTIME_ENTRIES" in sw
