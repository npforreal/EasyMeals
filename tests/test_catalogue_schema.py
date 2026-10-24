"""Kiểm thử tính đúng đắn của Baseline Schema danh mục và quyền RLS.

- Test tĩnh (Static tests): Luôn chạy, kiểm tra file SQL không có bảng cá nhân,
  không có user_id, chỉ có 4 bảng danh mục và RLS chỉ cho phép SELECT.
- Test tích hợp (Integration tests): Chỉ chạy khi EASYMEALS_INTEGRATION=1.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_FILE = ROOT / "supabase" / "migrations" / "202610240001_catalogue_baseline.sql"
FULL_SCHEMA_FILE = ROOT / "supabase" / "full_schema.sql"


def test_catalogue_migration_files_exist():
    assert MIGRATION_FILE.exists(), "File migration baseline không tồn tại"
    assert FULL_SCHEMA_FILE.exists(), "File full_schema.sql không tồn tại"


def test_schema_contains_only_shared_catalogue():
    content = MIGRATION_FILE.read_text(encoding="utf-8").lower()

    # Phải có 4 bảng danh mục dùng chung
    expected_tables = [
        "create table public.ingredients",
        "create table public.ingredient_aliases",
        "create table public.recipes",
        "create table public.recipe_ingredients",
    ]
    for table_stmt in expected_tables:
        assert table_stmt in content, f"Thiếu định nghĩa bảng: {table_stmt}"

    # Tuyệt đối không có bảng dữ liệu cá nhân
    forbidden_tables = [
        "pantry_lots",
        "meal_plans",
        "planned_dishes",
        "stock_movements",
    ]
    for table in forbidden_tables:
        assert table not in content, (
            f"Phát hiện bảng dữ liệu người dùng bị cấm trong schema: {table}"
        )

    # Tuyệt đối không có cột user_id hay liên kết auth.users
    assert "user_id" not in content, "Phát hiện user_id trong baseline schema"
    assert "auth.users" not in content, "Phát hiện liên kết auth.users trong baseline schema"


def test_schema_enforces_strict_rls_and_read_only():
    content = MIGRATION_FILE.read_text(encoding="utf-8").lower()

    # RLS phải được bật cho toàn bộ 4 bảng
    assert "alter table public.ingredients enable row level security" in content
    assert "alter table public.ingredient_aliases enable row level security" in content
    assert "alter table public.recipes enable row level security" in content
    assert "alter table public.recipe_ingredients enable row level security" in content

    # Chỉ có policy SELECT cho anon/authenticated
    assert "for select to anon, authenticated" in content

    # Thu hồi toàn bộ quyền ghi từ internet
    assert "revoke insert, update, delete on public.ingredients from anon" in content
    assert "revoke insert, update, delete on public.recipes from anon" in content


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("EASYMEALS_INTEGRATION") != "1",
    reason="Chỉ chạy khi EASYMEALS_INTEGRATION=1 với Supabase project thật",
)
def test_supabase_remote_rls_read_only():
    from postgrest.exceptions import APIError

    from supabase import create_client

    supabase_url = os.environ.get("SUPABASE_URL")
    anon_key = os.environ.get("SUPABASE_ANON_KEY")
    assert supabase_url and anon_key, "Thiếu SUPABASE_URL hoặc SUPABASE_ANON_KEY"

    client = create_client(supabase_url, anon_key)

    # 1. Anon đọc được ingredients
    res = client.table("ingredients").select("id, name").limit(5).execute()
    assert res.data is not None

    # 2. Anon KHÔNG thể insert vào ingredients (phải ném APIError do RLS/permission)
    with pytest.raises(APIError):
        client.table("ingredients").insert(
            {"name": "Test Hacking", "normalized_name": "test hacking"}
        ).execute()

    # 3. Không có bảng pantry_lots hay meal_plans
    with pytest.raises(APIError):
        client.table("pantry_lots").select("id").execute()
