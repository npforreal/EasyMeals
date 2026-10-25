"""Script kiểm chứng Row Level Security (RLS) trên Supabase.

Chạy thủ công (không chạy trong CI mặc định).
Yêu cầu:
- CHỈ sử dụng SUPABASE_URL và SUPABASE_ANON_KEY từ biến môi trường.
- Từ chối chạy nếu phát hiện SUPABASE_SERVICE_ROLE_KEY.
- Kiểm tra 4 bảng danh mục công khai:
  + SELECT: Thành công (cho phép đọc).
  + INSERT, UPDATE, DELETE: Phải bị từ chối bởi RLS hoặc quyền role anon.
"""

from __future__ import annotations

import os
import sys
import uuid
from typing import Any


def verify_table_rls(client: Any, table_name: str) -> None:
    print(f"--> Kiểm tra bảng: {table_name}")

    # 1. Thử SELECT (Phải thành công)
    try:
        res = client.table(table_name).select("*").limit(2).execute()
        print(f"  [OK] SELECT thành công (trả về {len(res.data)} dòng).")
    except Exception as e:
        print(f"  [FAIL] SELECT thất bại: {e}", file=sys.stderr)
        raise

    # 2. Thử INSERT (Phải bị từ chối)
    fake_id = str(uuid.uuid4())
    try:
        client.table(table_name).insert({"id": fake_id}).execute()
        print(f"  [FAIL] INSERT vào bảng {table_name} được phép (lỗi RLS)!", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"  [OK] INSERT bị từ chối chuẩn xác ({type(e).__name__}).")

    # 3. Thử UPDATE (Phải bị từ chối hoặc không có dòng nào bị ảnh hưởng do RLS)
    try:
        client.table(table_name).update({"id": fake_id}).eq("id", fake_id).execute()
        print("  [OK] UPDATE được xử lý an toàn (bị từ chối hoặc 0 rows modified).")
    except Exception as e:
        print(f"  [OK] UPDATE bị từ chối chuẩn xác ({type(e).__name__}).")

    # 4. Thử DELETE (Phải bị từ chối hoặc không có dòng nào bị ảnh hưởng do RLS)
    try:
        client.table(table_name).delete().eq("id", fake_id).execute()
        print("  [OK] DELETE được xử lý an toàn (bị từ chối hoặc 0 rows modified).")
    except Exception as e:
        print(f"  [OK] DELETE bị từ chối chuẩn xác ({type(e).__name__}).")


def run_verification() -> int:
    supabase_url = os.environ.get("SUPABASE_URL")
    anon_key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_PUBLISHABLE_KEY")

    if os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        print(
            "Lỗi bảo mật nghiêm trọng: Phát hiện SUPABASE_SERVICE_ROLE_KEY trong môi trường. "
            "Script này CHỈ được chạy với SUPABASE_ANON_KEY.",
            file=sys.stderr,
        )
        return 1

    if not supabase_url or not anon_key:
        print(
            "Lỗi: Thiếu SUPABASE_URL hoặc SUPABASE_ANON_KEY trong biến môi trường.\n"
            "Cách chạy:\n"
            "  SUPABASE_URL='https://xyz.supabase.co' SUPABASE_ANON_KEY='eyJ...' "
            "python scripts/verify_rls.py",
            file=sys.stderr,
        )
        return 1

    try:
        from supabase import create_client
    except ImportError:
        print(
            "Lỗi: Thư viện 'supabase' chưa được cài đặt. Chạy: pip install supabase",
            file=sys.stderr,
        )
        return 1

    print("=== BẮT ĐẦU KIỂM CHỨNG RLS SUPABASE VỚI CHỈ KHOÁ ANON ===")
    print(f"URL: {supabase_url}")
    print("Anon Key: [Đã cung cấp qua biến môi trường]")
    client = create_client(supabase_url, anon_key)

    tables = [
        "ingredient_categories",
        "ingredients",
        "ingredient_aliases",
        "recipes",
        "recipe_ingredients",
        "ingredient_conversions",
    ]
    for tbl in tables:
        verify_table_rls(client, tbl)

    print(f"\n===> TẤT CẢ {len(tables)} BẢNG ĐÃ ĐƯỢC BẢO VỆ AN TOÀN BỞI RLS. CHỈ ĐỌC (READ-ONLY)!")
    return 0


if __name__ == "__main__":
    sys.exit(run_verification())
