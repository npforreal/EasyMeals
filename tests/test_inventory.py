from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.inventory import (
    check_recipe_stock,
    deduct_recipe_stock_fifo,
    get_total_ingredient_stock,
    reverse_stock_movements,
)
from app.domain.models import (
    DishCategory,
    PantryLot,
    QuantityUnit,
    Recipe,
    RecipeIngredient,
    StockMovementReason,
)


@pytest.fixture
def sample_ingredient_id():
    return uuid4()


@pytest.fixture
def sample_recipe(sample_ingredient_id):
    recipe_id = uuid4()
    return Recipe(
        id=recipe_id,
        name="Thịt ba chỉ luộc",
        category=DishCategory.MAN,
        instructions=["Luộc thịt trong 20 phút."],
        servings=4,
        ingredients=[
            RecipeIngredient(
                recipe_id=recipe_id,
                ingredient_id=sample_ingredient_id,
                ingredient_name="Thịt ba chỉ",
                quantity=Decimal("500"),
                unit=QuantityUnit.GRAM,
            )
        ],
    )


def test_total_ingredient_stock_with_unit_conversion(sample_ingredient_id):
    lots = [
        PantryLot(
            id=uuid4(),
            ingredient_id=sample_ingredient_id,
            ingredient_name="Thịt ba chỉ",
            purchased_quantity=Decimal("0.5"),
            remaining_quantity=Decimal("0.5"),
            unit=QuantityUnit.KILOGRAM,
            purchased_at=datetime.now(),
        ),
        PantryLot(
            id=uuid4(),
            ingredient_id=sample_ingredient_id,
            ingredient_name="Thịt ba chỉ",
            purchased_quantity=Decimal("300"),
            remaining_quantity=Decimal("300"),
            unit=QuantityUnit.GRAM,
            purchased_at=datetime.now(),
        ),
    ]

    total_grams = get_total_ingredient_stock(lots, sample_ingredient_id, QuantityUnit.GRAM)
    assert total_grams == Decimal("800")

    total_kg = get_total_ingredient_stock(lots, sample_ingredient_id, QuantityUnit.KILOGRAM)
    assert total_kg == Decimal("0.8")


def test_check_recipe_stock_sufficient_and_insufficient(sample_recipe, sample_ingredient_id):
    lots_insufficient = [
        PantryLot(
            id=uuid4(),
            ingredient_id=sample_ingredient_id,
            ingredient_name="Thịt ba chỉ",
            purchased_quantity=Decimal("200"),
            remaining_quantity=Decimal("200"),
            unit=QuantityUnit.GRAM,
            purchased_at=datetime.now(),
        )
    ]
    can_cook, deficits = check_recipe_stock(sample_recipe, lots_insufficient)
    assert not can_cook
    assert sample_ingredient_id in deficits
    assert deficits[sample_ingredient_id][1] == Decimal("300")  # Needs 500, has 200 -> missing 300

    lots_sufficient = [
        PantryLot(
            id=uuid4(),
            ingredient_id=sample_ingredient_id,
            ingredient_name="Thịt ba chỉ",
            purchased_quantity=Decimal("1"),
            remaining_quantity=Decimal("1"),
            unit=QuantityUnit.KILOGRAM,
            purchased_at=datetime.now(),
        )
    ]
    can_cook, deficits = check_recipe_stock(sample_recipe, lots_sufficient)
    assert can_cook
    assert len(deficits) == 0


def test_deduct_recipe_stock_fifo(sample_recipe, sample_ingredient_id):
    meal_id = uuid4()

    # Two lots: lot 1 expires earlier (2026-10-25), lot 2 expires later (2026-10-30)
    lot1 = PantryLot(
        id=uuid4(),
        ingredient_id=sample_ingredient_id,
        ingredient_name="Thịt ba chỉ",
        purchased_quantity=Decimal("300"),
        remaining_quantity=Decimal("300"),
        unit=QuantityUnit.GRAM,
        purchased_at=datetime.now(),
        expires_at=date(2026, 10, 25),
    )
    lot2 = PantryLot(
        id=uuid4(),
        ingredient_id=sample_ingredient_id,
        ingredient_name="Thịt ba chỉ",
        purchased_quantity=Decimal("500"),
        remaining_quantity=Decimal("500"),
        unit=QuantityUnit.GRAM,
        purchased_at=datetime.now(),
        expires_at=date(2026, 10, 30),
    )

    all_lots = [lot2, lot1]  # pass in reverse order to ensure FIFO sorting by expiration
    result = deduct_recipe_stock_fifo(
        pantry_lots=all_lots,
        recipe=sample_recipe,
        meal_plan_id=meal_id,
        idempotency_key="key1",
    )

    # Required 500g: lot1 has 300g -> lot1 remaining 0g; lot2 has 500g -> lot2 remaining 300g
    assert lot1.remaining_quantity == Decimal("0")
    assert lot2.remaining_quantity == Decimal("300")
    assert len(result.movements) == 2
    assert result.movements[0].pantry_lot_id == lot1.id
    assert result.movements[0].quantity_delta == Decimal("-300")
    assert result.movements[1].pantry_lot_id == lot2.id
    assert result.movements[1].quantity_delta == Decimal("-200")


def test_reverse_stock_movements_undo(sample_recipe, sample_ingredient_id):
    meal_id = uuid4()

    lot = PantryLot(
        id=uuid4(),
        ingredient_id=sample_ingredient_id,
        ingredient_name="Thịt ba chỉ",
        purchased_quantity=Decimal("500"),
        remaining_quantity=Decimal("500"),
        unit=QuantityUnit.GRAM,
        purchased_at=datetime.now(),
    )

    result = deduct_recipe_stock_fifo(
        pantry_lots=[lot],
        recipe=sample_recipe,
        meal_plan_id=meal_id,
        idempotency_key="key_undo",
    )
    assert lot.remaining_quantity == Decimal("0")

    restored_lots, rev_movements = reverse_stock_movements(
        pantry_lots=[lot],
        movements=result.movements,
        meal_plan_id=meal_id,
    )

    # Restored back to 500g
    assert lot.remaining_quantity == Decimal("500")
    assert len(rev_movements) == 1
    assert rev_movements[0].reason == StockMovementReason.CORRECTION
    assert rev_movements[0].quantity_delta == Decimal("500")
