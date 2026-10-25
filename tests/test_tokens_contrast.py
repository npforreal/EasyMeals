"""Test kiểm tra độ tương phản màu (WCAG AA Contrast) của design tokens.

Yêu cầu WCAG AA:
- Chữ thường (normal text): contrast >= 4.5:1
- Chữ lớn / UI component (large text, icons, controls): contrast >= 3.0:1
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKENS_FILE = ROOT / "design-tokens" / "tokens.json"


def srgb_to_lin(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * srgb_to_lin(r) + 0.7152 * srgb_to_lin(g) + 0.0722 * srgb_to_lin(b)


def contrast_ratio(hex1: str, hex2: str) -> float:
    l1 = luminance(hex1)
    l2 = luminance(hex2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def test_palettes_wcag_aa_contrast():
    with open(TOKENS_FILE, encoding="utf-8") as f:
        tokens = json.load(f)

    palettes = tokens["palettes"]
    for pal_name, pal_data in palettes.items():
        for mode in ["light", "dark"]:
            colors = pal_data[mode]
            primary = colors["primary"]
            on_primary = colors["on_primary"]
            primary_strong = colors["primary_strong"]
            primary_soft = colors["primary_soft"]

            # Nút chính: on_primary trên primary phải đạt >= 4.5:1
            ratio_button = contrast_ratio(primary, on_primary)
            assert ratio_button >= 4.5, (
                f"Palette '{pal_name}' ({mode}): on_primary trên primary chỉ đạt "
                f"{ratio_button:.2f}:1 (< 4.5:1)"
            )

            # Tab chọn / badge: primary_strong trên primary_soft phải đạt >= 4.5:1
            ratio_nav = contrast_ratio(primary_strong, primary_soft)
            assert ratio_nav >= 4.5, (
                f"Palette '{pal_name}' ({mode}): primary_strong trên primary_soft chỉ đạt "
                f"{ratio_nav:.2f}:1 (< 4.5:1)"
            )


def test_neutrals_wcag_aa_contrast():
    with open(TOKENS_FILE, encoding="utf-8") as f:
        tokens = json.load(f)

    neutrals = tokens["neutrals"]
    for mode in ["light", "dark"]:
        n = neutrals[mode]
        bg = n["bg"]
        surface = n["surface"]
        ink = n["ink"]
        ink_muted = n["ink_muted"]
        danger = n["danger"]

        # Chữ chính trên nền và trên surface
        assert contrast_ratio(ink, bg) >= 4.5, f"Ink trên bg ({mode}) không đạt 4.5:1"
        assert contrast_ratio(ink, surface) >= 4.5, f"Ink trên surface ({mode}) không đạt 4.5:1"

        # Chữ phụ (muted) trên surface >= 4.5:1
        assert contrast_ratio(ink_muted, surface) >= 4.5, (
            f"Ink muted trên surface ({mode}) không đạt 4.5:1"
        )

        # Danger text trên surface >= 4.5:1
        assert contrast_ratio(danger, surface) >= 4.5, (
            f"Danger trên surface ({mode}) không đạt 4.5:1"
        )


def test_no_hardcoded_colors_in_mobile_code():
    import os
    import re

    patterns = [r"ForestGreen", r"Color\(0x", r"Color\(red:"]
    # Bỏ qua các file định nghĩa token hệ thống
    token_files = {"GeneratedTokens.kt", "GeneratedTokens.swift", "Color.kt", "Theme.swift"}

    violations = []
    mobile_dir = ROOT / "mobile"
    for root, _, files in os.walk(mobile_dir):
        for f in files:
            if f.endswith((".kt", ".swift")) and f not in token_files:
                path = Path(root) / f
                with open(path, encoding="utf-8") as fp:
                    for line_no, line in enumerate(fp, 1):
                        for p in patterns:
                            if re.search(p, line):
                                violations.append(
                                    f"{path.relative_to(ROOT)}:{line_no}: {line.strip()}"
                                )

    assert not violations, (
        "Phát hiện hardcode màu trong UI mobile (phải dùng design tokens):\n"
        + "\n".join(violations)
    )
