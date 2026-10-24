"""Script xóa sạch dữ liệu danh mục cũ trên Supabase để nạp lại từ đầu.

Yêu cầu xác nhận tường minh (--confirm) trước khi xóa để ngăn ngừa mất dữ liệu ngoài ý muốn.
Yêu cầu SUPABASE_SERVICE_ROLE_KEY (chỉ chạy cục bộ).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")


def reset_database(confirm: bool = False) -> None:
    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    print("=" * 60)
    print("EasyMeals — Xoá Dữ Liệu Danh Mục Supabase (Reset Database)")
    print("=" * 60)

    if not supabase_url:
        print("Lỗi: SUPABASE_URL không được tìm thấy trong môi trường hoặc .env", file=sys.stderr)
        sys.exit(1)

    if not service_role_key:
        print("Lỗi: Cần SUPABASE_SERVICE_ROLE_KEY để thực hiện quyền xoá.", file=sys.stderr)
        sys.exit(1)

    if not confirm:
        print(
            "\n[CẢNH BÁO]: Thao tác này sẽ xoá TOÀN BỘ dữ liệu trong 4 bảng danh mục:\n"
            "  - recipe_ingredients\n"
            "  - ingredient_aliases\n"
            "  - recipes\n"
            "  - ingredients\n"
            "\nĐể xác nhận thực hiện, hãy thêm cờ --confirm:\n"
            "  python scripts/reset_supabase.py --confirm\n"
        )
        return

    from supabase import create_client

    client = create_client(supabase_url, service_role_key)

    print("\n--> Đang xoá dữ liệu bảng recipe_ingredients...")
    client.table("recipe_ingredients").delete().neq("quantity", -999999).execute()

    print("--> Đang xoá dữ liệu bảng ingredient_aliases...")
    client.table("ingredient_aliases").delete().neq("alias", "___NON_EXISTENT___").execute()

    print("--> Đang xoá dữ liệu bảng recipes...")
    client.table("recipes").delete().neq("name", "___NON_EXISTENT___").execute()

    print("--> Đang xoá dữ liệu bảng ingredients...")
    client.table("ingredients").delete().neq("name", "___NON_EXISTENT___").execute()

    print("\n--> Kiểm tra lại số lượng sau khi xoá:")
    for tbl in ("recipe_ingredients", "ingredient_aliases", "recipes", "ingredients"):
        col = "id" if tbl != "recipe_ingredients" else "recipe_id"
        res = client.table(tbl).select(col, count="exact").execute()
        count = res.count or len(res.data)
        print(f"  - Bảng {tbl}: {count} dòng")

    print("\n[HOÀN TẤT] Đã xoá sạch dữ liệu danh mục cũ trên Supabase.")
    print("Bây giờ bạn có thể nạp lại dữ liệu mới bằng lệnh:")
    print("  python scripts/seed_catalogue.py --apply --with-harvest")


def main() -> None:
    parser = argparse.ArgumentParser(description="Xoá sạch dữ liệu danh mục trên Supabase.")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Xác nhận chắc chắn muốn xoá sạch dữ liệu danh mục trên Supabase.",
    )
    args = parser.parse_args()
    reset_database(confirm=args.confirm)


if __name__ == "__main__":
    main()
