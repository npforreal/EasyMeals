"""Màu theme phải có giá trị thật ở cả web lẫn bản đóng gói tĩnh (không để content rỗng)."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.theme import BACKGROUND_COLOR, THEME_COLOR

ROOT = Path(__file__).resolve().parents[1]
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def test_theme_constants_are_hex():
    assert HEX.match(THEME_COLOR)
    assert HEX.match(BACKGROUND_COLOR)


def test_web_pages_and_manifest_use_theme_color(client: TestClient):
    html = client.get("/").text
    assert f'<meta name="theme-color" content="{THEME_COLOR}">' in html
    manifest = client.get("/manifest.json").json()
    assert manifest["theme_color"] == THEME_COLOR
    assert manifest["background_color"] == BACKGROUND_COLOR


def test_static_mobile_build_has_theme_color(tmp_path, monkeypatch):
    from scripts import build_mobile_web

    monkeypatch.setattr(build_mobile_web, "WWW_DIR", tmp_path / "www")
    build_mobile_web.build_mobile_web()
    index = (tmp_path / "www" / "index.html").read_text(encoding="utf-8")
    assert f'<meta name="theme-color" content="{THEME_COLOR}">' in index
    assert 'content=""' not in index
