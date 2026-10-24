"""'Đã ăn' phải trừ kho khớp với lượng mà bước lập thực đơn đã tính (cả công thức)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient


def _full_pantry(recipe) -> list[dict]:
    return [
        {
            "id": str(uuid4()),
            "ingredient_id": str(ri.ingredient_id),
            "ingredient_name": ri.ingredient_name,
            "purchased_quantity": "100000",
            "remaining_quantity": "100000",
            "unit": ri.unit.value,
            "purchased_at": "2026-01-01T00:00:00",
        }
        for ri in recipe.ingredients
    ]


def test_planned_dishes_carry_full_recipe_servings(client: TestClient, repo):
    pantry = [p for r in repo.get_recipes()[:3] for p in _full_pantry(r)]
    res = client.post(
        "/api/planner/generate",
        json={"pantry": pantry, "start_date": date(2026, 1, 2).isoformat(), "days": 1},
    )
    assert res.status_code == 200
    by_id = {str(r.id): r for r in repo.get_recipes()}
    fresh = [d for m in res.json()["meals"] for d in m["dishes"] if not d["is_leftover"]]
    assert fresh
    for dish in fresh:
        assert dish["servings"] == by_id[dish["recipe_id"]].servings


def test_eat_without_servings_deducts_full_recipe(client: TestClient, repo):
    recipe = next(r for r in repo.get_recipes() if r.ingredients)
    pantry = _full_pantry(recipe)
    res = client.post(
        "/api/planner/eat",
        json={
            "pantry": pantry,
            "meal_plan_id": str(uuid4()),
            "idempotency_key": "k1",
            "dishes": [{"recipe_id": str(recipe.id)}],
        },
    )
    assert res.status_code == 200
    after = {p["ingredient_id"]: Decimal(p["remaining_quantity"]) for p in res.json()["pantry"]}
    for ri in recipe.ingredients:
        assert after[str(ri.ingredient_id)] == Decimal(100000) - ri.quantity


def test_eat_with_explicit_servings_scales(client: TestClient, repo):
    recipe = next(r for r in repo.get_recipes() if r.ingredients)
    res = client.post(
        "/api/planner/eat",
        json={
            "pantry": _full_pantry(recipe),
            "meal_plan_id": str(uuid4()),
            "idempotency_key": "k2",
            "dishes": [{"recipe_id": str(recipe.id), "servings": recipe.servings // 2}],
        },
    )
    assert res.status_code == 200
    first = recipe.ingredients[0]
    after = {p["ingredient_id"]: Decimal(p["remaining_quantity"]) for p in res.json()["pantry"]}
    expected = Decimal(100000) - first.quantity * Decimal(recipe.servings // 2) / Decimal(
        recipe.servings
    )
    assert after[str(first.ingredient_id)] == expected
