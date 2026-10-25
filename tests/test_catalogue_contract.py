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
    required_top_keys = [
        "catalogue_version",
        "etag",
        "ingredients",
        "recipes",
        "categories",
        "conversions",
    ]
    for key in required_top_keys:
        assert key in data, f"Thiếu khoá bắt buộc cấp cao nhất '{key}' trong catalogue.json"
        assert data[key] is not None, f"Khoá '{key}' không được có giá trị null"

    assert isinstance(data["catalogue_version"], str) and data["catalogue_version"].strip()
    assert isinstance(data["etag"], str) and data["etag"].strip()
    assert isinstance(data["ingredients"], list)
    assert isinstance(data["recipes"], list)
    assert isinstance(data["categories"], list)
    assert isinstance(data["conversions"], list)

    ingredients = data["ingredients"]
    recipes = data["recipes"]
    categories = data["categories"]
    conversions = data["conversions"]

    assert len(ingredients) >= 148, (
        f"Số lượng nguyên liệu ({len(ingredients)}) ít hơn mong đợi (148)"
    )
    assert len(recipes) >= 133, f"Số lượng món ăn ({len(recipes)}) ít hơn mong đợi (133)"
    assert len(categories) == 10, f"Số danh mục ({len(categories)}) khác 10"
    assert len(conversions) >= 2, f"Số quy đổi ({len(conversions)}) ít hơn 2"

    # Kiểm tra danh mục
    cat_ids = set()
    for cat in categories:
        assert isinstance(cat, dict)
        cid = cat.get("id")
        assert cid and cid not in cat_ids
        cat_ids.add(cid)
        assert cat.get("name_vi") or cat.get("name")
        assert "display_order" in cat or "sort_order" in cat

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
        assert ing["category"] in cat_ids, f"Nguyên liệu {ing['id']} category lạ: {ing['category']}"
        assert ing.get("default_unit"), f"Nguyên liệu {ing['id']} thiếu default_unit"

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

    # 4. Hợp đồng quy đổi nguyên liệu (Conversions)
    from_ids = set()
    to_ids = set()
    for conv in conversions:
        assert isinstance(conv, dict)
        f_id = conv.get("from_ingredient_id")
        t_id = conv.get("to_ingredient_id")
        assert f_id in ing_ids, f"from_ingredient_id {f_id} không tồn tại!"
        assert t_id in ing_ids, f"to_ingredient_id {t_id} không tồn tại!"
        assert f_id != t_id, f"Quy đổi từ và đến cùng nguyên liệu: {f_id}"
        ratio = float(conv.get("ratio") or 0)
        assert ratio > 0, f"Ratio quy đổi <= 0: {conv}"
        from_ids.add(f_id)
        to_ids.add(t_id)

    assert not from_ids.intersection(to_ids), "Phát hiện chuỗi quy đổi đa bước hoặc vòng lặp!"
