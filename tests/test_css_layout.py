"""Test hồi quy bố cục: quy tắc desktop không được rò ra ngoài @media (min-width: 720px)."""

from __future__ import annotations

import re
from pathlib import Path

CSS = (Path(__file__).resolve().parents[1] / "app/static/styles.css").read_text(encoding="utf-8")


def _strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _top_level_rules(css: str) -> dict[str, str]:
    """Gom thân quy tắc ở độ sâu 0 (ngoài mọi @media), theo bộ chọn."""
    css = _strip_comments(css)
    rules: dict[str, str] = {}
    depth = 0
    buf = ""
    start = 0
    for i, ch in enumerate(css):
        if ch == "{":
            if depth == 0:
                buf = css[start:i].strip()
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and not buf.startswith("@"):
                body = css[css.rfind("{", 0, i) + 1 : i]
                rules[buf] = rules.get(buf, "") + body
            if depth == 0:
                start = i + 1
    return rules


def test_css_braces_balanced():
    css = _strip_comments(CSS)
    assert css.count("{") == css.count("}")


def test_mobile_default_hides_sidebar_and_shows_tabbar():
    rules = _top_level_rules(CSS)
    assert re.search(r"display:\s*none", rules[".sidebar"])
    # Mặc định (di động) tabbar không bị ẩn ở ngoài media query.
    assert "display: none" not in rules.get(".tabbar", "")
    assert ".app-shell" in rules
    assert "grid-template-columns" not in rules[".app-shell"]


def test_desktop_shell_rules_live_inside_min_width_media():
    css = _strip_comments(CSS)
    m = re.search(r"@media \(min-width: 720px\)\s*\{", css)
    assert m
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(css[i], 0)
        i += 1
    block = css[m.end() : i - 1]
    assert "grid-template-columns: var(--sidebar-w)" in block
    assert ".tabbar { display: none; }" in block
