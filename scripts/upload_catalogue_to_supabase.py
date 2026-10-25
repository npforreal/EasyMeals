"""Upload toàn bộ danh mục hoàn chỉnh (data/catalogue.json) lên Supabase.

Mặc định chạy ở chế độ DRY-RUN (chỉ thống kê, không ghi DB).
Chỉ thực hiện ghi khi có cờ --apply.
Tuỳ chọn --clean để xoá sạch dữ liệu cũ trước khi nạp mới.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

CATALOGUE_FILE = ROOT / "data" / "catalogue.json"
BATCH_SIZE = 50


def build_client(apply: bool) -> Any:
    if not apply:
        return None
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key or url.startswith("https://your-project"):
        print(
            "Lỗi: Cần SUPABASE_URL và SUPABASE_SERVICE_ROLE_KEY để thực hiện --apply.",
            file=sys.stderr,
        )
        sys.exit(2)
    from supabase import create_client

    return create_client(url, key)


def chunked(items: list[Any], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def upload_catalogue(apply: bool = False, clean: bool = False) -> dict[str, Any]:
    if not CATALOGUE_FILE.exists():
        print(f"Lỗi: Không tìm thấy tệp {CATALOGUE_FILE}", file=sys.stderr)
        sys.exit(1)

    with CATALOGUE_FILE.open(encoding="utf-8") as f:
        bundle = json.load(f)

    ingredients = bundle.get("ingredients", [])
    recipes = bundle.get("recipes", [])
    categories = bundle.get("categories", [])
    conversions = bundle.get("conversions", [])

    print("=" * 60)
    print("EasyMeals — Upload Danh Mục Hoàn Chỉnh Lên Supabase")
    print("=" * 60)
    print(f"Chế độ: {'APPLY (ghi DB)' if apply else 'DRY-RUN (chỉ báo cáo)'}")
    print(f"Phiên bản: {bundle.get('catalogue_version')} | ETag: {bundle.get('etag')}")
    print(f"Tổng nhóm nguyên liệu: {len(categories)}")
    print(f"Tổng quy đổi: {len(conversions)}")
    print(f"Tổng nguyên liệu: {len(ingredients)}")
    print(f"Tổng công thức: {len(recipes)}")

    client = build_client(apply)

    if clean and apply:
        print("\n--> [LÀM SẠCH]: Đang xoá dữ liệu cũ theo ràng buộc khoá ngoại...")
        client.table("ingredient_conversions").delete().neq("ratio", -999999).execute()
        client.table("recipe_ingredients").delete().neq("quantity", -999999).execute()
        client.table("ingredient_aliases").delete().neq("alias", "___NON_EXISTENT___").execute()
        client.table("recipes").delete().neq("name", "___NON_EXISTENT___").execute()
        client.table("ingredients").delete().neq("name", "___NON_EXISTENT___").execute()
        client.table("ingredient_categories").delete().neq("id", "___NON_EXISTENT___").execute()
        print("    Đã xoá sạch các bảng danh mục.")

    # 1. Nạp ingredient_categories
    cat_rows = []
    for cat in categories:
        cat_rows.append(
            {
                "id": cat["id"],
                "name": cat["name"],
                "name_vi": cat.get("name_vi", cat["name"]),
                "display_order": int(cat.get("display_order", 0)),
            }
        )

    if apply and cat_rows:
        print(f"\n--> Đang upload {len(cat_rows)} nhóm nguyên liệu...")
        for batch in chunked(cat_rows, BATCH_SIZE):
            client.table("ingredient_categories").upsert(batch, on_conflict="id").execute()

    # 2. Nạp ingredients và aliases
    ing_rows = []
    alias_rows = []
    for ing in ingredients:
        ing_rows.append(
            {
                "id": ing["id"],
                "name": ing["name"],
                "normalized_name": ing["normalized_name"],
                "category": ing.get("category", "khac"),
                "default_unit": ing.get("default_unit", "g"),
            }
        )
        for alias in ing.get("aliases", []):
            alias_rows.append(
                {
                    "ingredient_id": ing["id"],
                    "alias": alias,
                    "normalized_alias": alias.strip().lower(),
                }
            )

    if apply:
        print(f"\n--> Đang upload {len(ing_rows)} nguyên liệu...")
        for batch in chunked(ing_rows, BATCH_SIZE):
            client.table("ingredients").upsert(batch, on_conflict="id").execute()

        if alias_rows:
            print(f"--> Đang upload {len(alias_rows)} tên gọi khác (aliases)...")
            for batch in chunked(alias_rows, BATCH_SIZE):
                client.table("ingredient_aliases").upsert(
                    batch, on_conflict="normalized_alias"
                ).execute()

    # 3. Nạp recipes và recipe_ingredients
    rec_rows = []
    ri_rows = []
    seen_ri: set[tuple[str, str]] = set()
    for rec in recipes:
        rec_rows.append(
            {
                "id": rec["id"],
                "name": rec["name"],
                "category": rec["category"],
                "instructions": rec.get("instructions", []),
                "servings": int(rec.get("servings", 4)),
            }
        )
        for ring in rec.get("ingredients", []):
            try:
                qty = float(ring["quantity"])
            except (ValueError, TypeError):
                qty = 0
            if qty <= 0:
                continue
            ri_key = (rec["id"], ring["ingredient_id"])
            if ri_key in seen_ri:
                continue
            seen_ri.add(ri_key)
            ri_rows.append(
                {
                    "recipe_id": rec["id"],
                    "ingredient_id": ring["ingredient_id"],
                    "quantity": float(ring["quantity"]),
                    "unit": ring["unit"],
                }
            )

    if apply:
        print(f"--> Đang upload {len(rec_rows)} công thức...")
        for batch in chunked(rec_rows, BATCH_SIZE):
            client.table("recipes").upsert(batch, on_conflict="id").execute()

        print(f"--> Đang upload {len(ri_rows)} liên kết nguyên liệu...")
        for batch in chunked(ri_rows, BATCH_SIZE):
            client.table("recipe_ingredients").upsert(
                batch, on_conflict="recipe_id,ingredient_id"
            ).execute()

        # 4. Nạp ingredient_conversions
        conv_rows = []
        for conv in conversions:
            conv_rows.append(
                {
                    "from_ingredient_id": conv["from_ingredient_id"],
                    "to_ingredient_id": conv["to_ingredient_id"],
                    "ratio": float(conv["ratio"]),
                    "from_unit": conv["from_unit"],
                    "to_unit": conv["to_unit"],
                    "note": conv.get("note", ""),
                }
            )
        if conv_rows:
            print(f"--> Đang upload {len(conv_rows)} quy đổi nguyên liệu...")
            for batch in chunked(conv_rows, BATCH_SIZE):
                client.table("ingredient_conversions").upsert(
                    batch, on_conflict="from_ingredient_id,to_ingredient_id"
                ).execute()

        # Kiểm tra đếm
        res_cat = client.table("ingredient_categories").select("id", count="exact").execute()
        res_ing = client.table("ingredients").select("id", count="exact").execute()
        res_rec = client.table("recipes").select("id", count="exact").execute()
        res_ri = client.table("recipe_ingredients").select("recipe_id", count="exact").execute()
        res_conv = client.table("ingredient_conversions").select("id", count="exact").execute()

        print("\n== KẾT QUẢ SUPABASE ==")
        print(f"  - Nhóm nguyên liệu: {res_cat.count or len(res_cat.data)}")
        print(f"  - Nguyên liệu: {res_ing.count or len(res_ing.data)}")
        print(f"  - Công thức: {res_rec.count or len(res_rec.data)}")
        print(f"  - Liên kết nguyên liệu: {res_ri.count or len(res_ri.data)}")
        print(f"  - Quy đổi: {res_conv.count or len(res_conv.data)}")
        print("\n[THÀNH CÔNG] Toàn bộ dữ liệu mới đã được cập nhật lên Supabase.")
    else:
        print("\n== BÁO CÁO DỰ KIẾN ==")
        print(f"  - Nhóm nguyên liệu: {len(cat_rows)}")
        print(f"  - Nguyên liệu: {len(ing_rows)}")
        print(f"  - Aliases: {len(alias_rows)}")
        print(f"  - Công thức: {len(rec_rows)}")
        print(f"  - Liên kết nguyên liệu: {len(ri_rows)}")
        print(f"  - Quy đổi: {len(conversions)}")
        print("\n--> Để ghi thật vào Supabase, hãy chạy:")
        print("    python scripts/upload_catalogue_to_supabase.py --apply")
        print("--> Hoặc xoá sạch trước rồi nạp mới:")
        print("    python scripts/upload_catalogue_to_supabase.py --apply --clean")

    return {
        "categories": len(cat_rows),
        "ingredients": len(ing_rows),
        "aliases": len(alias_rows),
        "recipes": len(rec_rows),
        "recipe_ingredients": len(ri_rows),
        "conversions": len(conversions),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload catalogue.json to Supabase.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Thực hiện ghi vào Supabase (mặc định dry-run).",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Xoá sạch dữ liệu danh mục cũ trên Supabase trước khi nạp mới.",
    )
    args = parser.parse_args()
    upload_catalogue(apply=args.apply, clean=args.clean)


if __name__ == "__main__":
    main()
