#!/usr/bin/env python3
"""scripts/generate_design_tokens.py

Sinh ra tokens CSS và mã nguồn cho Android (Kotlin) và iOS (Swift) từ:
  - design-tokens/tokens.json
  - design-tokens/labels.json

Hỗ trợ cờ --check để kiểm tra tính đồng bộ (dùng trong CI / scripts/check.sh).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKENS_FILE = ROOT / "design-tokens" / "tokens.json"
LABELS_FILE = ROOT / "design-tokens" / "labels.json"

TARGET_CSS = ROOT / "app" / "static" / "tokens.css"
TARGET_PYTHON = ROOT / "app" / "constants.py"
TARGET_JS = ROOT / "app" / "static" / "js" / "constants.js"
TARGET_KOTLIN = (
    ROOT
    / "mobile"
    / "android"
    / "app"
    / "src"
    / "main"
    / "java"
    / "com"
    / "easymeals"
    / "app"
    / "ui"
    / "theme"
    / "GeneratedTokens.kt"
)
TARGET_SWIFT = ROOT / "mobile" / "ios" / "EasyMeals" / "UI" / "Theme" / "GeneratedTokens.swift"
TARGET_SWIFT_LIMITS = (
    ROOT / "mobile" / "ios" / "EasyMeals" / "Domain" / "Common" / "PlanLimits.swift"
)


def load_inputs() -> tuple[dict, dict]:
    with open(TOKENS_FILE, encoding="utf-8") as f:
        tokens = json.load(f)
    with open(LABELS_FILE, encoding="utf-8") as f:
        labels = json.load(f)
    return tokens, labels


def generate_css(tokens: dict, labels: dict) -> str:
    lines = [
        "/* TỰ SINH — KHÔNG SỬA TAY (scripts/generate_design_tokens.py) */",
        "",
        ":root {",
        "  /* Radii */",
    ]
    for k, v in tokens["radius"].items():
        lines.append(f"  --radius-{k}: {v}px;")

    lines.append("")
    lines.append("  /* Spacing */")
    for k, v in tokens["spacing"].items():
        css_name = k.replace("_", "-")
        lines.append(f"  --{css_name}: {v / 16:.4g}rem;")

    lines.append("")
    lines.append("  /* Typography */")
    lines.append(f'  --font-display: "{tokens["typography"]["font_display"]}", Georgia, serif;')
    lines.append(f"  --font-body: {tokens['typography']['font_body']};")
    for k, v in tokens["typography"]["sizes"].items():
        lines.append(f"  --text-{k}: {v / 16:.4g}rem;")

    lines.append("")
    lines.append("  /* Light Neutrals (default) */")
    for k, v in tokens["neutrals"]["light"].items():
        lines.append(f"  --{k.replace('_', '-')}: {v};")

    if "plan_limits" in tokens:
        lines.append("")
        lines.append("  /* Plan Limits */")
        for k, v in tokens["plan_limits"].items():
            lines.append(f"  --plan-{k.replace('_', '-')}: {v};")

    # Default palette (green light)
    default_pal = tokens["palettes"]["green"]["light"]
    lines.append("")
    lines.append("  /* Default Palette (Green Light) */")
    for k, v in default_pal.items():
        lines.append(f"  --{k.replace('_', '-')}: {v};")
    lines.append("  color-scheme: light;")
    lines.append("}")
    lines.append("")

    # Dark mode neutrals
    lines.append("@media (prefers-color-scheme: dark) {")
    lines.append('  :root:not([data-theme="light"]) {')
    for k, v in tokens["neutrals"]["dark"].items():
        lines.append(f"    --{k.replace('_', '-')}: {v};")
    for k, v in tokens["palettes"]["green"]["dark"].items():
        lines.append(f"    --{k.replace('_', '-')}: {v};")
    lines.append("    color-scheme: dark;")
    lines.append("  }")
    lines.append("}")
    lines.append("")

    lines.append(':root[data-theme="dark"] {')
    for k, v in tokens["neutrals"]["dark"].items():
        lines.append(f"  --{k.replace('_', '-')}: {v};")
    for k, v in tokens["palettes"]["green"]["dark"].items():
        lines.append(f"  --{k.replace('_', '-')}: {v};")
    lines.append("  color-scheme: dark;")
    lines.append("}")
    lines.append("")

    # Palette overrides
    for pal_name, pal_data in tokens["palettes"].items():
        lines.append(f"/* Palette: {pal_name} ({pal_data.get('name_vi', pal_name)}) */")
        # Light
        lines.append(f':root[data-palette="{pal_name}"], [data-palette="{pal_name}"] {{')
        for k, v in pal_data["light"].items():
            lines.append(f"  --{k.replace('_', '-')}: {v};")
        lines.append("}")
        lines.append("")

        # Dark (prefers-color-scheme)
        lines.append("@media (prefers-color-scheme: dark) {")
        lines.append(f'  :root[data-palette="{pal_name}"]:not([data-theme="light"]) {{')
        for k, v in pal_data["dark"].items():
            lines.append(f"    --{k.replace('_', '-')}: {v};")
        lines.append("  }")
        lines.append("}")
        lines.append("")

        # Dark explicit
        selector_dark = (
            f':root[data-theme="dark"][data-palette="{pal_name}"], '
            f'[data-theme="dark"][data-palette="{pal_name}"] {{'
        )
        lines.append(selector_dark)
        for k, v in pal_data["dark"].items():
            lines.append(f"  --{k.replace('_', '-')}: {v};")
        lines.append("}")
        lines.append("")

    return "\n".join(lines)


def generate_python(tokens: dict, labels: dict) -> str:
    limits = tokens.get("plan_limits", {"min_days": 1, "max_days": 7, "default_days": 3})
    lines = [
        "# TỰ SINH — KHÔNG SỬA TAY (scripts/generate_design_tokens.py)",
        '"""Hằng số dùng chung toàn hệ thống sinh từ design-tokens/tokens.json."""',
        "",
        f"PLAN_MIN_DAYS = {limits['min_days']}",
        f"PLAN_MAX_DAYS = {limits['max_days']}",
        f"PLAN_DEFAULT_DAYS = {limits['default_days']}",
        f"LEFTOVER_MIN_DAYS = {limits.get('min_leftover_days', 1)}",
        f"LEFTOVER_MAX_DAYS = {limits.get('max_leftover_days', 3)}",
        f"LEFTOVER_DEFAULT_DAYS = {limits.get('default_leftover_days', 2)}",
        "",
    ]
    return "\n".join(lines)


def generate_js(tokens: dict, labels: dict) -> str:
    limits = tokens.get("plan_limits", {"min_days": 1, "max_days": 7, "default_days": 3})
    lines = [
        "// TỰ SINH — KHÔNG SỬA TAY (scripts/generate_design_tokens.py)",
        f"export const PLAN_MIN_DAYS = {limits['min_days']};",
        f"export const PLAN_MAX_DAYS = {limits['max_days']};",
        f"export const PLAN_DEFAULT_DAYS = {limits['default_days']};",
        f"export const LEFTOVER_MIN_DAYS = {limits.get('min_leftover_days', 1)};",
        f"export const LEFTOVER_MAX_DAYS = {limits.get('max_leftover_days', 3)};",
        f"export const LEFTOVER_DEFAULT_DAYS = {limits.get('default_leftover_days', 2)};",
        "",
    ]
    return "\n".join(lines)


def hex_to_kotlin_color(hex_str: str) -> str:
    clean = hex_str.lstrip("#").upper()
    return f"Color(0xFF{clean})"


def generate_kotlin(tokens: dict, labels: dict) -> str:
    lines = [
        "// TỰ SINH — KHÔNG SỬA TAY (scripts/generate_design_tokens.py)",
        "package com.easymeals.app.ui.theme",
        "",
        "import androidx.compose.ui.graphics.Color",
        "import androidx.compose.ui.unit.Dp",
        "import androidx.compose.ui.unit.TextUnit",
        "import androidx.compose.ui.unit.dp",
        "import androidx.compose.ui.unit.sp",
        "",
        "data class PaletteColors(",
        "    val primary: Color,",
        "    val primaryStrong: Color,",
        "    val onPrimary: Color,",
        "    val primarySoft: Color",
        ")",
        "",
        "data class NeutralColors(",
        "    val bg: Color,",
        "    val surface: Color,",
        "    val surfaceSunken: Color,",
        "    val ink: Color,",
        "    val inkMuted: Color,",
        "    val line: Color,",
        "    val accent: Color,",
        "    val accentSoft: Color,",
        "    val honey: Color,",
        "    val danger: Color,",
        "    val dangerSoft: Color,",
        "    val focus: Color",
        ")",
        "",
        "object GeneratedTokens {",
        "    object Radius {",
    ]
    for k, v in tokens["radius"].items():
        lines.append(f"        val {k}: Dp = {v}.dp")
    lines.append("    }")
    lines.append("")

    lines.append("    object Spacing {")
    for k, v in tokens["spacing"].items():
        lines.append(f"        val {k}: Dp = {v}.dp")
    lines.append("    }")
    lines.append("")

    lines.append("    object Typography {")
    for k, v in tokens["typography"]["sizes"].items():
        var_name = f"size{k.capitalize()}" if not k[0].isdigit() else f"size{k}"
        lines.append(f"        val {var_name}: TextUnit = {v}.sp")
    lines.append("    }")
    lines.append("")

    lines.append("    object Neutrals {")
    for mode in ["light", "dark"]:
        n = tokens["neutrals"][mode]
        lines.append(f"        val {mode} = NeutralColors(")
        fields = [
            f"bg = {hex_to_kotlin_color(n['bg'])}",
            f"surface = {hex_to_kotlin_color(n['surface'])}",
            f"surfaceSunken = {hex_to_kotlin_color(n['surface_sunken'])}",
            f"ink = {hex_to_kotlin_color(n['ink'])}",
            f"inkMuted = {hex_to_kotlin_color(n['ink_muted'])}",
            f"line = {hex_to_kotlin_color(n['line'])}",
            f"accent = {hex_to_kotlin_color(n['accent'])}",
            f"accentSoft = {hex_to_kotlin_color(n['accent_soft'])}",
            f"honey = {hex_to_kotlin_color(n['honey'])}",
            f"danger = {hex_to_kotlin_color(n['danger'])}",
            f"dangerSoft = {hex_to_kotlin_color(n['danger_soft'])}",
            f"focus = {hex_to_kotlin_color(n['focus'])}",
        ]
        for idx, f in enumerate(fields):
            sep = "," if idx < len(fields) - 1 else ""
            lines.append(f"            {f}{sep}")
        lines.append("        )")
    lines.append("    }")
    lines.append("")

    lines.append("    object Palettes {")
    for pal_name, pal_data in tokens["palettes"].items():
        lines.append(f"        object {pal_name.capitalize()} {{")
        lines.append(f'            const val NAME_VI = "{pal_data.get("name_vi", pal_name)}"')
        for mode in ["light", "dark"]:
            p = pal_data[mode]
            lines.append(f"            val {mode} = PaletteColors(")
            lines.append(f"                primary = {hex_to_kotlin_color(p['primary'])},")
            lines.append(
                f"                primaryStrong = {hex_to_kotlin_color(p['primary_strong'])},"
            )
            lines.append(f"                onPrimary = {hex_to_kotlin_color(p['on_primary'])},")
            lines.append(f"                primarySoft = {hex_to_kotlin_color(p['primary_soft'])}")
            lines.append("            )")
        lines.append("        }")
    lines.append("    }")
    lines.append("")

    lines.append("    object Labels {")
    for section_name, map_data in labels.items():
        lines.append(f"        val {section_name}: Map<String, String> = mapOf(")
        items = list(map_data.items())
        for idx, (k, v) in enumerate(items):
            sep = "," if idx < len(items) - 1 else ""
            lines.append(f'            "{k}" to "{v}"{sep}')
        lines.append("        )")
    lines.append("    }")
    lines.append("")

    limits = tokens.get("plan_limits", {"min_days": 1, "max_days": 7, "default_days": 3})
    lines.append("    object PlanLimits {")
    lines.append(f"        const val MIN_DAYS: Int = {limits['min_days']}")
    lines.append(f"        const val MAX_DAYS: Int = {limits['max_days']}")
    lines.append(f"        const val DEFAULT_DAYS: Int = {limits['default_days']}")
    lines.append(f"        const val LEFTOVER_MIN_DAYS: Int = {limits.get('min_leftover_days', 1)}")
    lines.append(f"        const val LEFTOVER_MAX_DAYS: Int = {limits.get('max_leftover_days', 3)}")
    lines.append(
        f"        const val LEFTOVER_DEFAULT_DAYS: Int = {limits.get('default_leftover_days', 2)}"
    )
    lines.append("    }")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def hex_to_swift_color(hex_str: str) -> str:
    clean = hex_str.lstrip("#").upper()
    r = int(clean[0:2], 16) / 255.0
    g = int(clean[2:4], 16) / 255.0
    b = int(clean[4:6], 16) / 255.0
    return f"Color(red: {r:.4f}, green: {g:.4f}, blue: {b:.4f})"


def generate_swift(tokens: dict, labels: dict) -> str:
    lines = [
        "// TỰ SINH — KHÔNG SỬA TAY (scripts/generate_design_tokens.py)",
        "import SwiftUI",
        "",
        "public struct PaletteColors {",
        "    public let primary: Color",
        "    public let primaryStrong: Color",
        "    public let onPrimary: Color",
        "    public let primarySoft: Color",
        "}",
        "",
        "public struct NeutralColors {",
        "    public let bg: Color",
        "    public let surface: Color",
        "    public let surfaceSunken: Color",
        "    public let ink: Color",
        "    public let inkMuted: Color",
        "    public let line: Color",
        "    public let accent: Color",
        "    public let accentSoft: Color",
        "    public let honey: Color",
        "    public let danger: Color",
        "    public let dangerSoft: Color",
        "    public let focus: Color",
        "}",
        "",
        "public enum GeneratedTokens {",
        "    public enum Radius {",
    ]
    for k, v in tokens["radius"].items():
        lines.append(f"        public static let {k}: CGFloat = {v}")
    lines.append("    }")
    lines.append("")

    lines.append("    public enum Spacing {")
    for k, v in tokens["spacing"].items():
        lines.append(f"        public static let {k}: CGFloat = {v}")
    lines.append("    }")
    lines.append("")

    lines.append("    public enum Typography {")
    for k, v in tokens["typography"]["sizes"].items():
        var_name = f"size{k.capitalize()}" if not k[0].isdigit() else f"size{k}"
        lines.append(f"        public static let {var_name}: CGFloat = {v}")
    lines.append("    }")
    lines.append("")

    lines.append("    public enum Neutrals {")
    for mode in ["light", "dark"]:
        n = tokens["neutrals"][mode]
        lines.append(f"        public static let {mode} = NeutralColors(")
        fields = [
            f"bg: {hex_to_swift_color(n['bg'])}",
            f"surface: {hex_to_swift_color(n['surface'])}",
            f"surfaceSunken: {hex_to_swift_color(n['surface_sunken'])}",
            f"ink: {hex_to_swift_color(n['ink'])}",
            f"inkMuted: {hex_to_swift_color(n['ink_muted'])}",
            f"line: {hex_to_swift_color(n['line'])}",
            f"accent: {hex_to_swift_color(n['accent'])}",
            f"accentSoft: {hex_to_swift_color(n['accent_soft'])}",
            f"honey: {hex_to_swift_color(n['honey'])}",
            f"danger: {hex_to_swift_color(n['danger'])}",
            f"dangerSoft: {hex_to_swift_color(n['danger_soft'])}",
            f"focus: {hex_to_swift_color(n['focus'])}",
        ]
        for idx, f in enumerate(fields):
            sep = "," if idx < len(fields) - 1 else ""
            lines.append(f"            {f}{sep}")
        lines.append("        )")
    lines.append("    }")
    lines.append("")

    lines.append("    public enum Palettes {")
    for pal_name, pal_data in tokens["palettes"].items():
        lines.append(f"        public enum {pal_name.capitalize()} {{")
        lines.append(
            f'            public static let nameVi = "{pal_data.get("name_vi", pal_name)}"'
        )
        for mode in ["light", "dark"]:
            p = pal_data[mode]
            lines.append(f"            public static let {mode} = PaletteColors(")
            lines.append(f"                primary: {hex_to_swift_color(p['primary'])},")
            lines.append(
                f"                primaryStrong: {hex_to_swift_color(p['primary_strong'])},"
            )
            lines.append(f"                onPrimary: {hex_to_swift_color(p['on_primary'])},")
            lines.append(f"                primarySoft: {hex_to_swift_color(p['primary_soft'])}")
            lines.append("            )")
        lines.append("        }")
    lines.append("    }")
    lines.append("")

    lines.append("    public enum Labels {")
    for section_name, map_data in labels.items():
        lines.append(f"        public static let {section_name}: [String: String] = [")
        items = list(map_data.items())
        for idx, (k, v) in enumerate(items):
            sep = "," if idx < len(items) - 1 else ""
            lines.append(f'            "{k}": "{v}"{sep}')
        lines.append("        ]")
    lines.append("    }")
    lines.append("")

    limits = tokens.get("plan_limits", {"min_days": 1, "max_days": 7, "default_days": 3})
    lines.append("    public enum PlanLimits {")
    lines.append(f"        public static let minDays: Int = {limits['min_days']}")
    lines.append(f"        public static let maxDays: Int = {limits['max_days']}")
    lines.append(f"        public static let defaultDays: Int = {limits['default_days']}")
    lines.append(
        f"        public static let leftoverMinDays: Int = {limits.get('min_leftover_days', 1)}"
    )
    lines.append(
        f"        public static let leftoverMaxDays: Int = {limits.get('max_leftover_days', 3)}"
    )
    default_leftover = limits.get("default_leftover_days", 2)
    lines.append(f"        public static let leftoverDefaultDays: Int = {default_leftover}")
    lines.append("    }")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def generate_swift_limits(tokens: dict) -> str:
    limits = tokens.get("plan_limits", {"min_days": 1, "max_days": 7, "default_days": 3})
    default_leftover = limits.get("default_leftover_days", 2)
    lines = [
        "// TỰ SINH — KHÔNG SỬA TAY (scripts/generate_design_tokens.py)",
        "import Foundation",
        "",
        "public enum PlanLimits {",
        f"    public static let minDays: Int = {limits['min_days']}",
        f"    public static let maxDays: Int = {limits['max_days']}",
        f"    public static let defaultDays: Int = {limits['default_days']}",
        f"    public static let leftoverMinDays: Int = {limits.get('min_leftover_days', 1)}",
        f"    public static let leftoverMaxDays: Int = {limits.get('max_leftover_days', 3)}",
        f"    public static let leftoverDefaultDays: Int = {default_leftover}",
        "}",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate design tokens across Web, Android, iOS.")
    parser.add_argument(
        "--check", action="store_true", help="Check that generated files are in sync."
    )
    args = parser.parse_args()

    tokens, labels = load_inputs()
    css_content = generate_css(tokens, labels)
    python_content = generate_python(tokens, labels)
    js_content = generate_js(tokens, labels)
    kotlin_content = generate_kotlin(tokens, labels)
    swift_content = generate_swift(tokens, labels)
    swift_limits_content = generate_swift_limits(tokens)

    pairs = [
        (TARGET_CSS, css_content),
        (TARGET_PYTHON, python_content),
        (TARGET_JS, js_content),
        (TARGET_KOTLIN, kotlin_content),
        (TARGET_SWIFT, swift_content),
        (TARGET_SWIFT_LIMITS, swift_limits_content),
    ]

    if args.check:
        mismatched = []
        for path, expected in pairs:
            if not path.exists():
                mismatched.append(f"{path} (missing)")
            else:
                current = path.read_text(encoding="utf-8")
                if current != expected:
                    mismatched.append(str(path))
        if mismatched:
            print(
                "Lỗi: Các tệp sau không khớp nguồn design-tokens:\n  " + "\n  ".join(mismatched),
                file=sys.stderr,
            )
            print("Chạy: python scripts/generate_design_tokens.py để đồng bộ.", file=sys.stderr)
            sys.exit(1)
        print("-> [OK] Toàn bộ file tokens đã đồng bộ với design-tokens/.")
        sys.exit(0)

    for path, content in pairs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"-> Đã sinh: {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
