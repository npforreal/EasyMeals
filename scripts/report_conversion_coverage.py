#!/usr/bin/env python3
"""scripts/report_conversion_coverage.py — Báo cáo độ phủ quy đổi nguyên liệu EasyMeals.

Phân tích danh mục:
1. Danh sách 148 nguyên liệu và tần suất sử dụng trong 133 công thức.
2. Các nguyên liệu thô (nguồn) và nguyên liệu chế biến (đích quy đổi).
3. Phát hiện các nguyên liệu dạng chế biến (cơm, xôi, chín...) xem đã có nguồn thô chưa.
4. Ghi nhận số lượng nguyên liệu mồ côi (cần chế biến nhưng chưa có quy đổi).
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE_PATH = ROOT / "data" / "catalogue.json"


def load_catalogue() -> dict:
    with open(CATALOGUE_PATH, encoding="utf-8") as f:
        return json.load(f)


def analyze_coverage() -> dict:
    cat = load_catalogue()
    ingredients = {ing["id"]: ing for ing in cat["ingredients"]}
    recipes = cat["recipes"]
    conversions = cat.get("conversions", [])

    # Thống kê tần suất dùng trong công thức
    usage_counts = defaultdict(int)
    for r in recipes:
        for item in r.get("ingredients", []):
            usage_counts[item["ingredient_id"]] += 1

    # Phân loại theo conversions
    source_ids = {c["from_ingredient_id"] for c in conversions}
    target_ids = {c["to_ingredient_id"] for c in conversions}

    # Tìm các nguyên liệu có tính chất chế biến (tên bắt đầu bằng Cơm, chứa cơm chín, xôi...)
    processed_candidates = []
    orphans = []

    for ing_id, ing in ingredients.items():
        name_lower = ing["name"].lower()
        is_processed = (
            name_lower.startswith("cơm")
            or "cơm chín" in name_lower
            or "xôi" in name_lower
            or "đã luộc" in name_lower
        )
        if is_processed:
            processed_candidates.append(ing)
            if ing_id not in target_ids:
                orphans.append(ing)

    return {
        "total_ingredients": len(ingredients),
        "total_recipes": len(recipes),
        "total_conversions": len(conversions),
        "source_ids": list(source_ids),
        "target_ids": list(target_ids),
        "processed_candidates": processed_candidates,
        "orphans": orphans,
        "usage_counts": usage_counts,
    }


def main() -> int:
    result = analyze_coverage()
    print("============================================================")
    print("EASYMEALS — BÁO CÁO ĐỘ PHỦ QUY ĐỔI NGUYÊN LIỆU (CONVERSIONS)")
    print("============================================================")
    print(f"Tổng số nguyên liệu: {result['total_ingredients']}")
    print(f"Tổng số món ăn: {result['total_recipes']}")
    print(f"Tổng số cặp quy đổi hiện có: {result['total_conversions']}")
    print(f"Số nguyên liệu đích chế biến có nguồn: {len(result['target_ids'])}")
    print(f"Số nguyên liệu dạng chế biến ('cơm', 'xôi'...): {len(result['processed_candidates'])}")
    for p in result["processed_candidates"]:
        status = "ĐÃ CÓ NGUỒN" if p["id"] in result["target_ids"] else "MỒ CÔI (THIẾU NGUỒN)"
        print(f"  - [{status}] {p['name']} ({p['id']})")

    print("------------------------------------------------------------")
    print(f"Số nguyên liệu chế biến mồ côi (chưa có quy đổi): {len(result['orphans'])}")
    if result["orphans"]:
        for o in result["orphans"]:
            print(f"  * CẢNH BÁO: {o['name']} ({o['id']}) chưa có quy đổi từ nguyên liệu thô!")
        return 1

    print("-> Tất cả các nguyên liệu chế biến ('cơm', 'xôi'...) đều đã có quy đổi hợp lệ.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
