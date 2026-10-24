"""Script xuất gói danh mục chuẩn (catalogue.json) cho Mobile App chạy offline.

Gói xuất ra có cùng cấu trúc với phản hồi /api/catalogue:
- ingredients (id, name, normalized_name, category, aliases)
- recipes (id, name, category, servings, instructions, ingredients)
- catalogue_version
- etag (băm SHA-256 từ dữ liệu đã chuẩn hoá và sắp xếp ổn định)

Đảm bảo tính toàn vẹn:
- Không trùng id nguyên liệu hoặc món ăn.
- Mọi recipe_ingredients trỏ tới nguyên liệu hợp lệ.
- Đơn vị và category hợp lệ.
- Xuất ổn định: cùng input -> cùng byte (sắp xếp key và mảng).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "catalogue.json"

VALID_UNITS = {"g", "kg", "ml", "l", "piece"}
VALID_CATEGORIES = {"man", "rau", "canh"}


def validate_catalogue_integrity(bundle: dict[str, Any]) -> None:
    ingredients = bundle.get("ingredients", [])
    recipes = bundle.get("recipes", [])

    ing_ids: set[str] = set()
    ing_norms: set[str] = set()
    for ing in ingredients:
        iid = ing["id"]
        if iid in ing_ids:
            raise ValueError(f"Trùng lặp ID nguyên liệu: {iid}")
        ing_ids.add(iid)

        norm = ing.get("normalized_name")
        if norm in ing_norms:
            raise ValueError(f"Trùng lặp normalized_name nguyên liệu: {norm}")
        ing_norms.add(norm)

    rec_ids: set[str] = set()
    for rec in recipes:
        rid = rec["id"]
        if rid in rec_ids:
            raise ValueError(f"Trùng lặp ID công thức: {rid}")
        rec_ids.add(rid)

        cat = rec.get("category")
        if cat not in VALID_CATEGORIES:
            raise ValueError(f"Category công thức '{rec.get('name')}' không hợp lệ: {cat}")

        rec_ing_ids: set[str] = set()
        for ring in rec.get("ingredients", []):
            ref_id = ring.get("ingredient_id")
            if ref_id not in ing_ids:
                raise ValueError(
                    f"Công thức '{rec['name']}' tham chiếu nguyên liệu không tồn tại: {ref_id}"
                )
            if ref_id in rec_ing_ids:
                raise ValueError(f"Công thức '{rec['name']}' chứa nguyên liệu bị lặp: {ref_id}")
            rec_ing_ids.add(ref_id)
            u = ring.get("unit")
            if u not in VALID_UNITS:
                raise ValueError(f"Công thức '{rec['name']}' dùng đơn vị không được hỗ trợ: {u}")

            try:
                qty = float(ring.get("quantity") or 0)
            except (ValueError, TypeError):
                qty = 0
            if qty <= 0:
                ing_name = ring.get("ingredient_name")
                msg = f"Công thức '{rec['name']}' có nguyên liệu '{ing_name}' <= 0"
                raise ValueError(msg)


def export_catalogue(output_path: Path) -> dict[str, Any]:
    from app.storage.repository import (
        CATALOGUE_VERSION,
        FixtureCatalogueRepository,
        SupabaseRepository,
    )

    # Ưu tiên lấy từ Supabase nếu có biến môi trường anon/publishable key,
    # ngược lại dùng Fixture chuẩn nội bộ
    supabase_url = os.environ.get("SUPABASE_URL")
    anon_key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_PUBLISHABLE_KEY")

    if supabase_url and anon_key and not os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        print(f"-> Xuất danh mục từ Supabase ({supabase_url}) bằng anon key...")
        repo = SupabaseRepository(supabase_url, anon_key)
    else:
        print("-> Xuất danh mục từ Fixture chuẩn nội bộ...")
        repo = FixtureCatalogueRepository()

    bundle = repo.get_catalogue_bundle()

    # Chuẩn hoá và sắp xếp ổn định (deterministic sorting)
    sorted_ingredients = sorted(bundle["ingredients"], key=lambda x: x["id"])
    for ing in sorted_ingredients:
        ing["aliases"] = sorted(ing.get("aliases", []))

    sorted_recipes = sorted(bundle["recipes"], key=lambda x: x["id"])
    for rec in sorted_recipes:
        rec["ingredients"] = sorted(rec.get("ingredients", []), key=lambda x: x["ingredient_id"])

    clean_bundle = {
        "catalogue_version": CATALOGUE_VERSION,
        "ingredients": sorted_ingredients,
        "recipes": sorted_recipes,
    }

    # Kiểm tra toàn vẹn dữ liệu
    validate_catalogue_integrity(clean_bundle)

    # Tính toán ETag ổn định
    canonical_json_bytes = json.dumps(clean_bundle, sort_keys=True).encode("utf-8")
    content_hash = hashlib.sha256(canonical_json_bytes).hexdigest()[:16]
    etag = f'"{CATALOGUE_VERSION}-{content_hash}"'
    clean_bundle["etag"] = etag

    # Ghi file với định dạng JSON đẹp và utf-8
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(clean_bundle, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    print(
        f"-> Đã xuất thành công gói danh mục ({len(sorted_ingredients)} nguyên liệu, "
        f"{len(sorted_recipes)} món ăn) vào: {output_path}"
    )
    print(f"-> ETag: {etag}")
    return clean_bundle


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Xuất gói danh mục catalogue.json cho Mobile.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Đường dẫn file đích (mặc định: data/catalogue.json)",
    )
    args = parser.parse_args()
    try:
        export_catalogue(args.output)
    except Exception as e:
        print(f"Lỗi xuất danh mục: {e}", file=sys.stderr)
        sys.exit(1)
