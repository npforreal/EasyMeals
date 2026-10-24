"""Test phân trang SupabaseRepository (PostgREST cắt ở 1.000 dòng/truy vấn)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.storage import repository as repo_module
from app.storage.repository import SupabaseRepository


class _Resp:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _FakeQuery:
    """Mô phỏng PostgREST: mỗi truy vấn tối đa 1.000 dòng, hỗ trợ range/order."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.window = (0, 999)
        self.calls = 0

    def select(self, *_a: Any, **_k: Any) -> _FakeQuery:
        return self

    def order(self, *_a: Any, **_k: Any) -> _FakeQuery:
        return self

    def ilike(self, *_a: Any, **_k: Any) -> _FakeQuery:
        return self

    def eq(self, *_a: Any, **_k: Any) -> _FakeQuery:
        return self

    def range(self, start: int, end: int) -> _FakeQuery:
        self.window = (start, min(end, start + 999))
        return self

    def execute(self) -> _Resp:
        self.calls += 1
        start, end = self.window
        return _Resp(self.rows[start : end + 1])


class _FakeClient:
    def __init__(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        self.tables = tables
        self.queries: dict[str, _FakeQuery] = {}

    def table(self, name: str) -> _FakeQuery:
        q = _FakeQuery(self.tables[name])
        self.queries[name] = q
        return q


def _make_repo(tables: dict[str, list[dict[str, Any]]]) -> SupabaseRepository:
    repo = SupabaseRepository.__new__(SupabaseRepository)
    repo.client = _FakeClient(tables)  # type: ignore[assignment]
    return repo


def test_get_ingredients_reads_every_page():
    rows = [
        {
            "id": str(UUID(int=i + 1)),
            "name": f"Nguyên liệu {i}",
            "normalized_name": f"nguyen lieu {i}",
            "category": None,
            "ingredient_aliases": [],
        }
        for i in range(2500)
    ]
    repo = _make_repo({"ingredients": rows})
    result = repo.get_ingredients()
    assert len(result) == 2500
    assert repo.client.queries["ingredients"].calls == 3  # 1000 + 1000 + 500


def test_get_recipes_reads_every_page():
    rows = [
        {
            "id": str(UUID(int=i + 1)),
            "name": f"Món {i}",
            "category": "man",
            "servings": 4,
            "instructions": ["Nấu."],
            "recipe_ingredients": [],
        }
        for i in range(1000)  # đúng bằng một trang: phải hỏi thêm trang rỗng, không dừng sớm sai
    ]
    repo = _make_repo({"recipes": rows})
    assert len(repo.get_recipes()) == 1000
    assert repo.client.queries["recipes"].calls == 2


def test_page_size_matches_postgrest_default():
    assert repo_module.SUPABASE_PAGE_SIZE == 1000
