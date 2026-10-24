"""Pytest test suite validating Python domain engine against shared fixture."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from app.domain.inventory import (
    check_recipe_stock,
    deduct_recipe_stock_fifo,
    reverse_stock_movements,
)
from app.domain.models import (
    DishCategory,
    PantryLot,
    QuantityUnit,
    Recipe,
    RecipeIngredient,
    convert_quantity,
)
from app.domain.planner import generate_period_plan

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "engine_test_cases.json"


def norm_dec_str(val: Decimal | str) -> str:
    s = str(val)
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def test_python_engine_matches_shared_fixture():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        cases = json.load(f)

    # 1. Unit conversions
    for u in cases["unit_conversions"]:
        res = convert_quantity(Decimal(u["quantity"]), u["from_unit"], u["to_unit"])
        assert norm_dec_str(res) == u["expected"]

    # 2. FIFO Deduction
    fifo_data = cases["fifo_deduction"]
    recipe_dict = fifo_data["recipe"]
    recipe = Recipe(
        id=UUID(recipe_dict["id"]),
        name=recipe_dict["name"],
        category=DishCategory(recipe_dict["category"]),
        servings=recipe_dict["servings"],
        instructions=[],
        ingredients=[
            RecipeIngredient(
                recipe_id=UUID(recipe_dict["id"]),
                ingredient_id=UUID(ri["ingredient_id"]),
                ingredient_name=ri["ingredient_name"],
                quantity=Decimal(ri["quantity"]),
                unit=QuantityUnit(ri["unit"]),
            )
            for ri in recipe_dict["ingredients"]
        ],
    )
    pantry_lots = [
        PantryLot(
            id=UUID(pl["id"]),
            ingredient_id=UUID(pl["ingredient_id"]),
            ingredient_name=pl["ingredient_name"],
            purchased_quantity=Decimal(pl["purchased_quantity"]),
            remaining_quantity=Decimal(pl["remaining_quantity"]),
            unit=QuantityUnit(pl["unit"]),
            purchased_at=datetime.fromisoformat(pl["purchased_at"]),
            expires_at=date.fromisoformat(pl["expires_at"]) if pl["expires_at"] else None,
        )
        for pl in fifo_data["pantry"]
    ]

    can_cook, deficits = check_recipe_stock(recipe, pantry_lots)
    assert can_cook == fifo_data["check_stock_expected"]["can_cook"]
    assert len(deficits) == fifo_data["check_stock_expected"]["deficits_count"]

    res = deduct_recipe_stock_fifo(
        pantry_lots=pantry_lots,
        recipe=recipe,
        meal_plan_id=UUID("bbbbbbbb-0001-0000-0000-000000000001"),
        idempotency_key="fifo_test",
    )
    exp_lots = fifo_data["deduction_expected"]["updated_lots"]
    assert len(res.updated_lots) == len(exp_lots)
    for l_actual, l_exp in zip(res.updated_lots, exp_lots, strict=True):
        assert str(l_actual.id) == l_exp["id"]
        assert str(l_actual.remaining_quantity) == l_exp["remaining_quantity"]

    # 3. Undo consumption
    undo_data = cases["undo_consumption"]
    restored_lots, reversal_movements = reverse_stock_movements(
        pantry_lots=res.updated_lots,
        movements=res.movements,
        meal_plan_id=UUID("bbbbbbbb-0001-0000-0000-000000000001"),
    )
    assert len(restored_lots) == len(undo_data["restored_lots"])
    for l_actual, l_exp in zip(restored_lots, undo_data["restored_lots"], strict=True):
        assert str(l_actual.id) == l_exp["id"]
        assert str(l_actual.remaining_quantity) == l_exp["remaining_quantity"]

    # 4. Planner generation
    plan_data = cases["planner_generation"]
    recipes = [
        Recipe(
            id=UUID(rd["id"]),
            name=rd["name"],
            category=DishCategory(rd["category"]),
            servings=rd["servings"],
            instructions=[],
            ingredients=[
                RecipeIngredient(
                    recipe_id=UUID(rd["id"]),
                    ingredient_id=UUID(ri["ingredient_id"]),
                    ingredient_name=ri["ingredient_name"],
                    quantity=Decimal(ri["quantity"]),
                    unit=QuantityUnit(ri["unit"]),
                )
                for ri in rd["ingredients"]
            ],
        )
        for rd in plan_data["recipes"]
    ]
    plans, shopping_items = generate_period_plan(
        start_date=date.fromisoformat(plan_data["start_date"]),
        end_date=date.fromisoformat(plan_data["end_date"]),
        recipes=recipes,
        current_pantry_lots=pantry_lots,
        allow_leftovers=True,
    )
    assert len(plans) == plan_data["expected_meals_count"]
    for p_actual, exp_dishes in zip(plans, plan_data["expected_dishes_per_meal"], strict=True):
        assert len(p_actual.dishes) == len(exp_dishes)
        for d_act, d_exp in zip(p_actual.dishes, exp_dishes, strict=True):
            assert d_act.recipe_name == d_exp["recipe_name"]
            assert d_act.category.value == d_exp["category"]
            assert d_act.is_leftover == d_exp["is_leftover"]
