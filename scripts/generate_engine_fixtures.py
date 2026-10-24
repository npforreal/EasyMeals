"""Sinh bộ test fixture JSON dùng chung giữa Python pytest và Node.js test runner.

Đảm bảo hai engine (Python backend và JS client) đồng nhất 100% về mặt số học Decimal,
quy tắc trừ kho FIFO, hoàn tác, và thuật toán lập thực đơn.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from app.domain.inventory import (
    InsufficientStockError,
    check_recipe_stock,
    deduct_recipe_stock_fifo,
    reverse_stock_movements,
)
from app.domain.models import (
    DishCategory,
    IncompatibleUnitError,
    PantryLot,
    QuantityUnit,
    Recipe,
    RecipeIngredient,
    StockMovementReason,
    convert_quantity,
)
from app.domain.planner import generate_period_plan

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "engine_test_cases.json"


def serialize_val(obj):
    if isinstance(obj, (Decimal, UUID, date, datetime)):
        return str(obj)
    if isinstance(obj, QuantityUnit):
        return obj.value
    if isinstance(obj, DishCategory):
        return obj.value
    if isinstance(obj, StockMovementReason):
        return obj.value
    raise TypeError(f"Cannot serialize {type(obj)}")


def norm_dec_str(val: Decimal) -> str:
    s = str(val)
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def generate_fixtures() -> dict:
    cases = {}

    # Case 1: Unit Conversions
    unit_cases = [
        {
            "quantity": "500",
            "from_unit": "g",
            "to_unit": "kg",
            "expected": norm_dec_str(convert_quantity(Decimal("500"), "g", "kg")),
        },
        {
            "quantity": "1.25",
            "from_unit": "kg",
            "to_unit": "g",
            "expected": norm_dec_str(convert_quantity(Decimal("1.25"), "kg", "g")),
        },
        {
            "quantity": "250",
            "from_unit": "ml",
            "to_unit": "l",
            "expected": norm_dec_str(convert_quantity(Decimal("250"), "ml", "l")),
        },
        {
            "quantity": "3.5",
            "from_unit": "l",
            "to_unit": "ml",
            "expected": norm_dec_str(convert_quantity(Decimal("3.5"), "l", "ml")),
        },
        {"quantity": "4", "from_unit": "piece", "to_unit": "piece", "expected": "4"},
    ]
    cases["unit_conversions"] = unit_cases

    # Case 2: Stock Check & FIFO Deduction
    rec_id = UUID("22222222-0001-0000-0000-000000000001")
    ing_pork = UUID("11111111-0001-0000-0000-000000000001")
    ing_egg = UUID("11111111-0001-0000-0000-000000000009")

    recipe = Recipe(
        id=rec_id,
        name="Thịt kho tàu",
        category=DishCategory.MAN,
        servings=4,
        instructions=["Nấu thịt kho"],
        ingredients=[
            RecipeIngredient(
                recipe_id=rec_id,
                ingredient_id=ing_pork,
                ingredient_name="Thịt ba chỉ",
                quantity=Decimal("500"),
                unit=QuantityUnit.GRAM,
            ),
            RecipeIngredient(
                recipe_id=rec_id,
                ingredient_id=ing_egg,
                ingredient_name="Trứng vịt",
                quantity=Decimal("4"),
                unit=QuantityUnit.PIECE,
            ),
        ],
    )

    initial_pantry_lots = [
        # Lot 1: Expiring soonest, 300g pork
        PantryLot(
            id=UUID("aaaaaaaa-0001-0000-0000-000000000001"),
            ingredient_id=ing_pork,
            ingredient_name="Thịt ba chỉ",
            purchased_quantity=Decimal("500"),
            remaining_quantity=Decimal("300"),
            unit=QuantityUnit.GRAM,
            purchased_at=datetime(2026, 10, 20, 10, 0, 0),
            expires_at=date(2026, 10, 25),
        ),
        # Lot 2: Expiring later, 400g pork
        PantryLot(
            id=UUID("aaaaaaaa-0001-0000-0000-000000000002"),
            ingredient_id=ing_pork,
            ingredient_name="Thịt ba chỉ",
            purchased_quantity=Decimal("500"),
            remaining_quantity=Decimal("400"),
            unit=QuantityUnit.GRAM,
            purchased_at=datetime(2026, 10, 22, 10, 0, 0),
            expires_at=date(2026, 10, 28),
        ),
        # Lot 3: Eggs, 10 pieces
        PantryLot(
            id=UUID("aaaaaaaa-0001-0000-0000-000000000003"),
            ingredient_id=ing_egg,
            ingredient_name="Trứng vịt",
            purchased_quantity=Decimal("10"),
            remaining_quantity=Decimal("10"),
            unit=QuantityUnit.PIECE,
            purchased_at=datetime(2026, 10, 21, 10, 0, 0),
            expires_at=date(2026, 10, 30),
        ),
    ]

    pantry_for_deduction = [
        PantryLot(
            id=lot.id,
            ingredient_id=lot.ingredient_id,
            ingredient_name=lot.ingredient_name,
            purchased_quantity=lot.purchased_quantity,
            remaining_quantity=lot.remaining_quantity,
            unit=lot.unit,
            purchased_at=lot.purchased_at,
            expires_at=lot.expires_at,
        )
        for lot in initial_pantry_lots
    ]

    can_cook, deficits = check_recipe_stock(recipe, initial_pantry_lots)

    meal_plan_id = UUID("bbbbbbbb-0001-0000-0000-000000000001")
    deduction_result = deduct_recipe_stock_fifo(
        pantry_lots=pantry_for_deduction,
        recipe=recipe,
        meal_plan_id=meal_plan_id,
        idempotency_key="fifo_test_key",
    )

    fifo_case = {
        "recipe": {
            "id": str(recipe.id),
            "name": recipe.name,
            "category": recipe.category.value,
            "servings": recipe.servings,
            "ingredients": [
                {
                    "ingredient_id": str(i.ingredient_id),
                    "ingredient_name": i.ingredient_name,
                    "quantity": norm_dec_str(i.quantity),
                    "unit": i.unit.value,
                }
                for i in recipe.ingredients
            ],
        },
        "pantry": [
            {
                "id": str(lot.id),
                "ingredient_id": str(lot.ingredient_id),
                "ingredient_name": lot.ingredient_name,
                "purchased_quantity": norm_dec_str(lot.purchased_quantity),
                "remaining_quantity": norm_dec_str(lot.remaining_quantity),
                "unit": lot.unit.value,
                "purchased_at": lot.purchased_at.isoformat(),
                "expires_at": lot.expires_at.isoformat() if lot.expires_at else None,
            }
            for lot in initial_pantry_lots
        ],
        "check_stock_expected": {
            "can_cook": can_cook,
            "deficits_count": len(deficits),
        },
        "deduction_expected": {
            "updated_lots": [
                {
                    "id": str(lot.id),
                    "remaining_quantity": norm_dec_str(lot.remaining_quantity),
                }
                for lot in deduction_result.updated_lots
            ],
            "movements": [
                {
                    "pantry_lot_id": str(m.pantry_lot_id),
                    "quantity_delta": norm_dec_str(m.quantity_delta),
                    "reason": m.reason.value,
                }
                for m in deduction_result.movements
            ],
        },
    }
    cases["fifo_deduction"] = fifo_case

    # Case 3: Undo Consumption
    # Reversing the movements from Case 2
    restored_lots, reversal_movements = reverse_stock_movements(
        pantry_lots=deduction_result.updated_lots,
        movements=deduction_result.movements,
        meal_plan_id=meal_plan_id,
    )
    undo_case = {
        "restored_lots": [
            {
                "id": str(lot.id),
                "remaining_quantity": norm_dec_str(lot.remaining_quantity),
            }
            for lot in restored_lots
        ],
        "reversal_movements": [
            {
                "pantry_lot_id": str(m.pantry_lot_id),
                "quantity_delta": norm_dec_str(m.quantity_delta),
                "reason": m.reason.value,
            }
            for m in reversal_movements
        ],
    }
    cases["undo_consumption"] = undo_case

    # Case 4: Planner Generation with Leftovers and Shopping list
    # Use 3 classic recipes for man, rau, canh
    rec_rau = Recipe(
        id=UUID("22222222-0002-0000-0000-000000000001"),
        name="Rau muống xào tỏi",
        category=DishCategory.RAU,
        servings=4,
        instructions=["Xào rau"],
        ingredients=[
            RecipeIngredient(
                recipe_id=UUID("22222222-0002-0000-0000-000000000001"),
                ingredient_id=UUID("11111111-0001-0000-0000-000000000011"),
                ingredient_name="Rau muống",
                quantity=Decimal("400"),
                unit=QuantityUnit.GRAM,
            )
        ],
    )
    rec_canh = Recipe(
        id=UUID("22222222-0003-0000-0000-000000000001"),
        name="Canh chua cá lóc",
        category=DishCategory.CANH,
        servings=4,
        instructions=["Nấu canh chua"],
        ingredients=[
            RecipeIngredient(
                recipe_id=UUID("22222222-0003-0000-0000-000000000001"),
                ingredient_id=UUID("11111111-0001-0000-0000-000000000006"),
                ingredient_name="Cá lóc",
                quantity=Decimal("400"),
                unit=QuantityUnit.GRAM,
            )
        ],
    )
    all_recipes = [recipe, rec_rau, rec_canh]
    # Pantry only has pork and eggs (enough for Thịt kho tàu), missing rau and canh
    plans, shopping_items = generate_period_plan(
        start_date=date(2026, 10, 25),
        end_date=date(2026, 10, 25),  # 1 day = 2 meals (lunch & dinner)
        recipes=all_recipes,
        current_pantry_lots=initial_pantry_lots,
        allow_leftovers=True,
    )

    planner_case = {
        "start_date": "2026-10-25",
        "end_date": "2026-10-25",
        "recipes": [
            {
                "id": str(r.id),
                "name": r.name,
                "category": r.category.value,
                "servings": r.servings,
                "ingredients": [
                    {
                        "ingredient_id": str(i.ingredient_id),
                        "ingredient_name": i.ingredient_name,
                        "quantity": norm_dec_str(i.quantity),
                        "unit": i.unit.value,
                    }
                    for i in r.ingredients
                ],
            }
            for r in all_recipes
        ],
        "pantry": [
            {
                "id": str(lot.id),
                "ingredient_id": str(lot.ingredient_id),
                "ingredient_name": lot.ingredient_name,
                "purchased_quantity": norm_dec_str(lot.purchased_quantity),
                "remaining_quantity": norm_dec_str(lot.remaining_quantity),
                "unit": lot.unit.value,
                "purchased_at": lot.purchased_at.isoformat(),
                "expires_at": lot.expires_at.isoformat() if lot.expires_at else None,
            }
            for lot in initial_pantry_lots
        ],
        "expected_meals_count": len(plans),
        "expected_dishes_per_meal": [
            [
                {
                    "recipe_name": d.recipe_name,
                    "category": d.category.value,
                    "is_leftover": d.is_leftover,
                }
                for d in p.dishes
            ]
            for p in plans
        ],
        "expected_shopping_items": [
            {
                "ingredient_id": str(s.ingredient_id),
                "ingredient_name": s.ingredient_name,
                "needed_quantity": norm_dec_str(s.needed_quantity),
                "unit": s.unit.value,
            }
            for s in sorted(shopping_items, key=lambda x: str(x.ingredient_id))
        ],
    }
    cases["planner_generation"] = planner_case

    # -------------------------------------------------------------------------
    # Case 5: FIFO chute chuẩn khi hai lot có cùng hạn sử dụng
    # (tie-break theo ngày mua: lot sớm mua hơn được trừ trước)
    # -------------------------------------------------------------------------
    recipe_tie = Recipe(
        id=UUID("22222222-0001-0000-0000-000000000001"),
        name="Thịt kho tàu",
        category=DishCategory.MAN,
        servings=4,
        instructions=["Nấu thịt kho"],
        ingredients=[
            RecipeIngredient(
                recipe_id=UUID("22222222-0001-0000-0000-000000000001"),
                ingredient_id=ing_pork,
                ingredient_name="Thịt ba chỉ",
                quantity=Decimal("500"),
                unit=QuantityUnit.GRAM,
            ),
            RecipeIngredient(
                recipe_id=UUID("22222222-0001-0000-0000-000000000001"),
                ingredient_id=ing_egg,
                ingredient_name="Trứng vịt",
                quantity=Decimal("4"),
                unit=QuantityUnit.PIECE,
            ),
        ],
    )

    pantry_tie = [
        PantryLot(
            id=UUID("aaaaaaaa-0001-0000-0000-000000000010"),
            ingredient_id=ing_pork,
            ingredient_name="Thịt ba chỉ",
            purchased_quantity=Decimal("500"),
            remaining_quantity=Decimal("400"),
            unit=QuantityUnit.GRAM,
            purchased_at=datetime(2026, 10, 22, 10, 0, 0),
            expires_at=date(2026, 10, 28),
        ),
        PantryLot(
            id=UUID("aaaaaaaa-0001-0000-0000-000000000011"),
            ingredient_id=ing_pork,
            ingredient_name="Thịt ba chỉ",
            purchased_quantity=Decimal("500"),
            remaining_quantity=Decimal("300"),
            unit=QuantityUnit.GRAM,
            purchased_at=datetime(2026, 10, 20, 10, 0, 0),
            expires_at=date(2026, 10, 28),
        ),
        PantryLot(
            id=UUID("aaaaaaaa-0001-0000-0000-000000000012"),
            ingredient_id=ing_egg,
            ingredient_name="Trứng vịt",
            purchased_quantity=Decimal("10"),
            remaining_quantity=Decimal("10"),
            unit=QuantityUnit.PIECE,
            purchased_at=datetime(2026, 10, 21, 10, 0, 0),
            expires_at=date(2026, 10, 30),
        ),
    ]
    # Cả hai lot thịt hết hạn 2026-10-28 → chute chuẩn theo ngày mua:
    # lot ...0011 (mua 10-20) được trừ trước, rồi mới đến lot ...0010 (mua 10-22).

    pantry_tie_for_deduct = [
        PantryLot(
            id=lot.id,
            ingredient_id=lot.ingredient_id,
            ingredient_name=lot.ingredient_name,
            purchased_quantity=lot.purchased_quantity,
            remaining_quantity=lot.remaining_quantity,
            unit=lot.unit,
            purchased_at=lot.purchased_at,
            expires_at=lot.expires_at,
        )
        for lot in pantry_tie
    ]

    can_cook_tie, deficits_tie = check_recipe_stock(recipe_tie, pantry_tie)
    deduction_tie = deduct_recipe_stock_fifo(
        pantry_lots=pantry_tie_for_deduct,
        recipe=recipe_tie,
        meal_plan_id=UUID("bbbbbbbb-0001-0000-0000-000000000010"),
        idempotency_key="tiebreak_test_key",
    )

    def _serialize_recipe(r: Recipe) -> dict:
        return {
            "id": str(r.id),
            "name": r.name,
            "category": r.category.value,
            "servings": r.servings,
            "ingredients": [
                {
                    "ingredient_id": str(i.ingredient_id),
                    "ingredient_name": i.ingredient_name,
                    "quantity": norm_dec_str(i.quantity),
                    "unit": i.unit.value,
                }
                for i in r.ingredients
            ],
        }

    def _serialize_pantry(lots: list[PantryLot]) -> list[dict]:
        return [
            {
                "id": str(lot.id),
                "ingredient_id": str(lot.ingredient_id),
                "ingredient_name": lot.ingredient_name,
                "purchased_quantity": norm_dec_str(lot.purchased_quantity),
                "remaining_quantity": norm_dec_str(lot.remaining_quantity),
                "unit": lot.unit.value,
                "purchased_at": lot.purchased_at.isoformat(),
                "expires_at": lot.expires_at.isoformat() if lot.expires_at else None,
            }
            for lot in lots
        ]

    def _serialize_lots(result_lots: list[PantryLot]) -> list[dict]:
        return [
            {
                "id": str(lot.id),
                "remaining_quantity": norm_dec_str(lot.remaining_quantity),
            }
            for lot in result_lots
        ]

    def _serialize_movements(movements: list) -> list[dict]:
        return [
            {
                "pantry_lot_id": str(m.pantry_lot_id),
                "quantity_delta": norm_dec_str(m.quantity_delta),
                "reason": m.reason.value,
            }
            for m in movements
        ]

    tie_case = {
        "recipe": _serialize_recipe(recipe_tie),
        "pantry": _serialize_pantry(pantry_tie),
        "check_stock_expected": {
            "can_cook": can_cook_tie,
            "deficits_count": len(deficits_tie),
        },
        "deduction_expected": {
            "updated_lots": _serialize_lots(deduction_tie.updated_lots),
            "movements": _serialize_movements(deduction_tie.movements),
        },
    }
    cases["fifo_deduction_same_expiry_tiebreak"] = tie_case

    # -------------------------------------------------------------------------
    # Case 6: Hết hàng / không đủ hàng (InsufficientStockError)
    # -------------------------------------------------------------------------
    pantry_insuff = [
        PantryLot(
            id=UUID("aaaaaaaa-0001-0000-0000-000000000013"),
            ingredient_id=ing_pork,
            ingredient_name="Thịt ba chỉ",
            purchased_quantity=Decimal("500"),
            remaining_quantity=Decimal("300"),
            unit=QuantityUnit.GRAM,
            purchased_at=datetime(2026, 10, 20, 10, 0, 0),
            expires_at=date(2026, 10, 25),
        ),
        PantryLot(
            id=UUID("aaaaaaaa-0001-0000-0000-000000000014"),
            ingredient_id=ing_egg,
            ingredient_name="Trứng vịt",
            purchased_quantity=Decimal("10"),
            remaining_quantity=Decimal("10"),
            unit=QuantityUnit.PIECE,
            purchased_at=datetime(2026, 10, 21, 10, 0, 0),
            expires_at=date(2026, 10, 30),
        ),
    ]

    can_cook_insuff, deficits_insuff = check_recipe_stock(recipe_tie, pantry_insuff)

    insuff_deducted = False
    try:
        deduct_recipe_stock_fifo(
            pantry_lots=[
                PantryLot(
                    id=lot.id,
                    ingredient_id=lot.ingredient_id,
                    ingredient_name=lot.ingredient_name,
                    purchased_quantity=lot.purchased_quantity,
                    remaining_quantity=lot.remaining_quantity,
                    unit=lot.unit,
                    purchased_at=lot.purchased_at,
                    expires_at=lot.expires_at,
                )
                for lot in pantry_insuff
            ],
            recipe=recipe_tie,
            meal_plan_id=UUID("bbbbbbbb-0001-0000-0000-000000000011"),
            idempotency_key="insuff_test_key",
        )
    except InsufficientStockError:
        insuff_deducted = True

    insuff_case = {
        "recipe": _serialize_recipe(recipe_tie),
        "pantry": _serialize_pantry(pantry_insuff),
        "check_stock_expected": {
            "can_cook": can_cook_insuff,
            "deficits_count": len(deficits_insuff),
        },
        "deduction_expected": {
            "error": "InsufficientStockError",
            "raised": insuff_deducted,
            "deficits_count": len(deficits_insuff),
        },
    }
    cases["stock_insufficient"] = insuff_case

    # -------------------------------------------------------------------------
    # Case 7: Chuyển đổi không tương thích giữa khối lượng (g/kg)
    # và thể tích (ml/l) -> IncompatibleUnitError
    # -------------------------------------------------------------------------
    ing_oil = UUID("11111111-0001-0000-0000-000000000050")
    recipe_incompat = Recipe(
        id=UUID("22222222-0001-0000-0000-000000000010"),
        name="Cá kho dầu",
        category=DishCategory.MAN,
        servings=4,
        instructions=["N cá kho dầu ăn"],
        ingredients=[
            RecipeIngredient(
                recipe_id=UUID("22222222-0001-0000-0000-000000000010"),
                ingredient_id=ing_oil,
                ingredient_name="Dầu ăn",
                quantity=Decimal("250"),
                unit=QuantityUnit.GRAM,
            )
        ],
    )

    pantry_incompat = [
        PantryLot(
            id=UUID("aaaaaaaa-0001-0000-0000-000000000015"),
            ingredient_id=ing_oil,
            ingredient_name="Dầu ăn",
            purchased_quantity=Decimal("1000"),
            remaining_quantity=Decimal("1000"),
            unit=QuantityUnit.MILLILITER,
            purchased_at=datetime(2026, 10, 20, 10, 0, 0),
            expires_at=date(2026, 10, 28),
        ),
    ]

    can_cook_incompat, deficits_incompat = check_recipe_stock(recipe_incompat, pantry_incompat)

    conversion_error_name = None
    try:
        convert_quantity(Decimal("250"), QuantityUnit.GRAM, QuantityUnit.MILLILITER)
    except IncompatibleUnitError as exc:
        conversion_error_name = exc.__class__.__name__

    incompat_case = {
        "recipe": _serialize_recipe(recipe_incompat),
        "pantry": _serialize_pantry(pantry_incompat),
        "check_stock_expected": {
            "can_cook": can_cook_incompat,
            "deficits_count": len(deficits_incompat),
        },
        "conversion_expected": {
            "quantity": "250",
            "from_unit": "g",
            "to_unit": "ml",
            "error": conversion_error_name,
        },
    }
    cases["unit_conversion_incompatible_mass_volume"] = incompat_case

    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(FIXTURE_PATH, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"-> Đã sinh thành công fixture JSON: {FIXTURE_PATH}")
    return cases


if __name__ == "__main__":
    generate_fixtures()
