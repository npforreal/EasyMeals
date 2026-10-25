"""Ca logic bổ sung dùng chung Python/JS (tests/fixtures/engine_logic_cases.json).

Các ca này khoá lại các lỗi logic tìm thấy ở vòng rà soát: đơn vị trộn lẫn, mô phỏng trừ kho
sai đơn vị, đếm trùng kho, gộp danh sách mua, lô hết hạn, hoàn tác lặp.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from app.constants import LEFTOVER_DEFAULT_DAYS
from app.domain.inventory import (
    check_recipe_stock,
    deduct_recipe_stock_available,
    deduct_recipe_stock_fifo,
    reverse_stock_movements,
)
from app.domain.models import (
    DishCategory,
    IngredientConversion,
    MealPeriod,
    MealPlan,
    PantryLot,
    QuantityUnit,
    Recipe,
    RecipeIngredient,
    StockMovement,
    StockMovementReason,
)
from app.domain.planner import (
    calculate_shopping_budget,
    generate_period_plan,
    merge_new_plans_into_existing,
)

CASES = json.loads(
    (Path(__file__).parent / "fixtures" / "engine_logic_cases.json").read_text(encoding="utf-8")
)["cases"]


def _recipe(d: dict) -> Recipe:
    rid = UUID(d["id"])
    return Recipe(
        id=rid,
        name=d["name"],
        category=DishCategory(d["category"]),
        servings=d["servings"],
        instructions=[],
        ingredients=[
            RecipeIngredient(
                recipe_id=rid,
                ingredient_id=UUID(i["ingredient_id"]),
                ingredient_name=i["name"],
                quantity=Decimal(i["quantity"]),
                unit=QuantityUnit(i["unit"]),
            )
            for i in d["ingredients"]
        ],
    )


def _lots(items: list[dict]) -> list[PantryLot]:
    return [
        PantryLot(
            id=UUID(x["id"]),
            ingredient_id=UUID(x["ingredient_id"]),
            ingredient_name=x["name"],
            purchased_quantity=Decimal(x["purchased"]),
            remaining_quantity=Decimal(x["remaining"]),
            unit=QuantityUnit(x["unit"]),
            purchased_at=datetime(2025, 12, 1),
            expires_at=date.fromisoformat(x["expires_at"]) if x.get("expires_at") else None,
        )
        for x in items
    ]


def _conversions(items: list[dict] | None) -> list[IngredientConversion] | None:
    if not items:
        return None
    return [
        IngredientConversion(
            from_ingredient_id=UUID(c["from_ingredient_id"]),
            to_ingredient_id=UUID(c["to_ingredient_id"]),
            ratio=Decimal(c["ratio"]),
            from_unit=QuantityUnit(c.get("from_unit", "g")),
            to_unit=QuantityUnit(c.get("to_unit", "g")),
            note=c.get("note"),
        )
        for c in items
    ]


def _norm(v: Decimal | str) -> str:
    s = format(Decimal(str(v)), "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_logic_case(case):
    op = case["op"]
    convs = _conversions(case.get("conversions"))
    if op == "check":
        ok, deficits = check_recipe_stock(
            _recipe(case["recipe"]),
            _lots(case["pantry"]),
            Decimal(case.get("multiplier", "1")),
            conversions=convs,
        )
        assert ok == case["expect"]["can_cook"]
        assert {str(k): _norm(v[1]) for k, v in deficits.items()} == case["expect"]["deficits"]
    elif op == "fifo":
        lots = _lots(case["pantry"])
        res = deduct_recipe_stock_fifo(
            lots,
            _recipe(case["recipe"]),
            UUID(int=1),
            "key",
            Decimal(case.get("multiplier", "1")),
            conversions=convs,
        )
        assert res.movements
        assert {str(lot.id): _norm(lot.remaining_quantity) for lot in lots} == case["expect"][
            "remaining"
        ]
    elif op == "deduct_available":
        lots = _lots(case["pantry"])
        res, deficits = deduct_recipe_stock_available(
            lots,
            _recipe(case["recipe"]),
            UUID(int=1),
            "key",
            Decimal(case.get("multiplier", "1")),
            conversions=convs,
        )
        assert {str(lot.id): _norm(lot.remaining_quantity) for lot in lots} == case["expect"][
            "remaining"
        ]
        assert {str(k): _norm(v[1]) for k, v in deficits.items()} == case["expect"]["deficits"]
        actual_movements = {str(m.pantry_lot_id): _norm(m.quantity_delta) for m in res.movements}
        assert actual_movements == case["expect"]["movements"]
    elif op == "undo":
        lots = _lots(case["pantry"])
        movements = [
            StockMovement(
                id=UUID(m["id"]),
                pantry_lot_id=UUID(m["pantry_lot_id"]),
                quantity_delta=Decimal(m["delta"]),
                reason=StockMovementReason(m["reason"]),
                meal_plan_id=UUID(m["meal_plan_id"]),
                idempotency_key=m["idempotency_key"],
            )
            for m in case["movements"]
        ]
        reverse_stock_movements(lots, movements, UUID(case["meal_plan_id"]))
        assert {str(lot.id): _norm(lot.remaining_quantity) for lot in lots} == case["expect"][
            "remaining"
        ]
    elif op == "plan":
        start = date.fromisoformat(case["start"])
        end_date = date.fromordinal(start.toordinal() + case["days"] - 1)
        leftover_days = case.get("leftover_days", LEFTOVER_DEFAULT_DAYS)
        if case["expect"].get("error"):
            with pytest.raises(ValueError):
                generate_period_plan(
                    start_date=start,
                    end_date=end_date,
                    recipes=[_recipe(r) for r in case["recipes"]],
                    current_pantry_lots=_lots(case["pantry"]),
                    allow_leftovers=case["allow_leftovers"],
                    leftover_days=leftover_days,
                    conversions=convs,
                )
            return

        plans, shopping = generate_period_plan(
            start_date=start,
            end_date=end_date,
            recipes=[_recipe(r) for r in case["recipes"]],
            current_pantry_lots=_lots(case["pantry"]),
            allow_leftovers=case["allow_leftovers"],
            leftover_days=leftover_days,
            conversions=convs,
        )
        dishes = [d for p in plans for d in p.dishes]
        assert [d.recipe_name for d in dishes] == case["expect"]["dishes"]
        assert [d.servings for d in dishes] == case["expect"]["servings"]
        got = {str(s.ingredient_id): [_norm(s.needed_quantity), s.unit.value] for s in shopping}
        assert got == case["expect"]["shopping"]
    elif op == "merge_plans":

        def _plan(d: dict) -> MealPlan:
            return MealPlan(
                id=UUID(d["id"]),
                planned_for=date.fromisoformat(d["planned_for"]),
                meal_period=MealPeriod(d["meal_period"]),
                eaten_at=(datetime.fromisoformat(d["eaten_at"]) if d.get("eaten_at") else None),
            )

        merged = merge_new_plans_into_existing(
            [_plan(p) for p in case["existing"]],
            [_plan(p) for p in case["new_plans"]],
            mode=case.get("mode", "replace"),
        )
        assert [str(p.id) for p in merged] == case["expect"]["kept_ids"]
    elif op == "shopping_budget":
        budget = calculate_shopping_budget(case["items"])
        assert _norm(budget["total_estimated_budget"]) == case["expect"]["total_estimated"]
        assert _norm(budget["total_spent"]) == case["expect"]["total_spent"]
        assert budget["items_with_price_count"] == case["expect"]["items_with_price_count"]
        assert budget["total_items_count"] == case["expect"]["total_items_count"]
    else:  # pragma: no cover
        raise AssertionError(op)
