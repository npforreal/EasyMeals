"""Chốt chặn kiểm thử: không còn TheMealDB và danh mục nhất quán 100%."""

from __future__ import annotations

import json
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE_PATH = ROOT / "data" / "catalogue.json"

ALLOWED_THEMEALDB_DOCS = {
    "docs/third_party_catalogue_removal.md",
    "tests/test_no_themealdb.py",
}

# Các nguyên liệu dạng lỏng được phép dùng ml/l
LIQUID_INGREDIENTS = {
    "dau an",
    "dau hao",
    "dau me",
    "dau oliu",
    "giam",
    "kem tuoi",
    "nuoc mam",
    "nuoc tuong",
    "sua tuoi",
}


def test_no_tracked_files_contain_themealdb():
    """Kiểm tra không file nào trong git chứa chuỗi themealdb, trừ tài liệu giải thích."""
    res = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    tracked_files = [line.strip() for line in res.stdout.splitlines() if line.strip()]

    offending: list[str] = []
    for rel_path in tracked_files:
        if rel_path in ALLOWED_THEMEALDB_DOCS:
            continue
        file_path = ROOT / rel_path
        if not file_path.exists() or file_path.is_dir():
            continue
        # Skip binary files
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        if "themealdb" in content.lower():
            offending.append(rel_path)

    assert not offending, (
        f"Phát hiện chuỗi 'themealdb' trong {len(offending)} file theo dõi: {offending}"
    )


def test_catalogue_ingredients_have_consistent_units_and_no_solid_ml():
    """Kiểm tra mỗi nguyên liệu dùng duy nhất 1 đơn vị và nguyên liệu rắn không dùng ml/l."""
    assert CATALOGUE_PATH.exists(), f"Không tìm thấy file {CATALOGUE_PATH}"
    with open(CATALOGUE_PATH, encoding="utf-8") as f:
        bundle = json.load(f)

    recipes = bundle.get("recipes", [])
    ingredients = {i["id"]: i for i in bundle.get("ingredients", [])}

    ing_units = defaultdict(set)
    solid_with_volume = []

    for r in recipes:
        for ring in r.get("ingredients", []):
            ing_id = ring["ingredient_id"]
            ing_name = ring.get("ingredient_name") or ingredients[ing_id]["name"]
            norm_name = ingredients[ing_id]["normalized_name"]
            unit = ring["unit"]

            ing_units[ing_name].add(unit)

            if unit in ("ml", "l") and norm_name not in LIQUID_INGREDIENTS:
                solid_with_volume.append((r["name"], ing_name, unit))

    # 1. Mỗi nguyên liệu chỉ dùng đúng 1 đơn vị
    multi_units = {name: units for name, units in ing_units.items() if len(units) > 1}
    assert not multi_units, f"Có nguyên liệu dùng nhiều đơn vị khác nhau: {multi_units}"

    # 2. Không nguyên liệu rắn nào dùng ml hoặc l
    assert not solid_with_volume, (
        f"Có nguyên liệu rắn bị ghi đơn vị thể tích (ml/l): {solid_with_volume}"
    )

    # 3. Đảm bảo toàn bộ 147 nguyên liệu
    assert len(bundle.get("ingredients", [])) == 147, (
        f"Kỳ vọng 147 nguyên liệu, thực tế {len(bundle.get('ingredients', []))}"
    )
    assert len(recipes) >= 130, f"Kỳ vọng >= 130 công thức, thực tế {len(recipes)}"
