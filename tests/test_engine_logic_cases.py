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
    StockMovement,
    StockMovementReason,
)
from app.domain.planner import generate_period_plan

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


def _norm(v: Decimal | str) -> str:
    s = format(Decimal(str(v)), "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_logic_case(case):
    op = case["op"]
    if op == "check":
        ok, deficits = check_recipe_stock(
            _recipe(case["recipe"]), _lots(case["pantry"]), Decimal(case["multiplier"])
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
            Decimal(case["multiplier"]),
        )
        assert res.movements
        assert {str(lot.id): _norm(lot.remaining_quantity) for lot in lots} == case["expect"][
            "remaining"
        ]
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
        plans, shopping = generate_period_plan(
            start_date=start,
            end_date=date.fromordinal(start.toordinal() + case["days"] - 1),
            recipes=[_recipe(r) for r in case["recipes"]],
            current_pantry_lots=_lots(case["pantry"]),
            allow_leftovers=case["allow_leftovers"],
        )
        dishes = [d for p in plans for d in p.dishes]
        assert [d.recipe_name for d in dishes] == case["expect"]["dishes"]
        assert [d.servings for d in dishes] == case["expect"]["servings"]
        got = {str(s.ingredient_id): [_norm(s.needed_quantity), s.unit.value] for s in shopping}
        assert got == case["expect"]["shopping"]
    else:  # pragma: no cover
        raise AssertionError(op)
