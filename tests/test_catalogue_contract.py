"""Kiểm tra hợp đồng dữ liệu catalogue.json.

Đảm bảo tính tương thích với cả ba client: Web, Android, iOS.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE_PATH = ROOT / "data" / "catalogue.json"


def test_catalogue_json_structure() -> None:
    assert CATALOGUE_PATH.exists(), f"File {CATALOGUE_PATH} không tồn tại!"

    with open(CATALOGUE_PATH, encoding="utf-8") as f:
        data = json.load(f)

    # 1. Các khoá bắt buộc ở cấp cao nhất
    required_top_keys = ["catalogue_version", "etag", "ingredients", "recipes"]
    for key in required_top_keys:
        assert key in data, f"Thiếu khoá bắt buộc cấp cao nhất '{key}' trong catalogue.json"
        assert data[key] is not None, f"Khoá '{key}' không được có giá trị null"

    assert isinstance(data["catalogue_version"], str) and data["catalogue_version"].strip()
    assert isinstance(data["etag"], str) and data["etag"].strip()
    assert isinstance(data["ingredients"], list)
    assert isinstance(data["recipes"], list)

    ingredients = data["ingredients"]
    recipes = data["recipes"]

    assert len(ingredients) >= 147, (
        f"Số lượng nguyên liệu ({len(ingredients)}) ít hơn mong đợi (147)"
    )
    assert len(recipes) >= 133, f"Số lượng món ăn ({len(recipes)}) ít hơn mong đợi (133)"

    # 2. Hợp đồng nguyên liệu (Ingredients)
    ing_ids = set()
    for ing in ingredients:
        assert isinstance(ing, dict)
        assert "id" in ing and ing["id"], f"Nguyên liệu thiếu id: {ing}"
        assert ing["id"] not in ing_ids, f"Trùng lặp id nguyên liệu: {ing['id']}"
        ing_ids.add(ing["id"])

        assert "name" in ing and ing["name"], f"Nguyên liệu {ing['id']} thiếu name"
        assert "normalized_name" in ing and ing["normalized_name"], (
            f"Nguyên liệu {ing['id']} thiếu normalized_name"
        )
        assert "category" in ing, f"Nguyên liệu {ing['id']} thiếu category"

    # 3. Hợp đồng món ăn (Recipes)
    rec_ids = set()
    for rec in recipes:
        assert isinstance(rec, dict)
        assert "id" in rec and rec["id"], f"Món ăn thiếu id: {rec}"
        assert rec["id"] not in rec_ids, f"Trùng lặp id món ăn: {rec['id']}"
        rec_ids.add(rec["id"])

        assert "name" in rec and rec["name"], f"Món ăn {rec['id']} thiếu name"
        assert "category" in rec and rec["category"], f"Món ăn {rec['id']} thiếu category"
        assert "servings" in rec and rec["servings"] > 0, (
            f"Món ăn {rec['id']} thiếu servings hoặc servings <= 0"
        )
        assert "ingredients" in rec and isinstance(rec["ingredients"], list), (
            f"Món ăn {rec['id']} thiếu ingredients"
        )
        assert len(rec["ingredients"]) > 0, f"Món ăn {rec['id']} không có nguyên liệu nào"

        for ring in rec["ingredients"]:
            ing_fk = ring.get("ingredient_id")
            assert "ingredient_id" in ring and ing_fk in ing_ids, (
                f"Khoá ngoại ingredient_id {ing_fk} trong món {rec['id']} không tồn tại!"
            )
            assert "quantity" in ring and ring["quantity"], f"Thiếu quantity trong món {rec['id']}"
            assert "unit" in ring and ring["unit"], f"Thiếu unit trong món {rec['id']}"
