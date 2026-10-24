"""Xác nhận mô hình miền (domain models) và hàm tính toán đã được xoá hoàn toàn user_id.

EasyMeals kiến trúc mới: dữ liệu cá nhân (tủ lạnh, thực đơn, biến động kho) nằm
hoàn toàn trong IndexedDB côté client; miền/backend không nhận và không lưu user_id.
"""

from dataclasses import fields
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from app.domain.inventory import deduct_recipe_stock_fifo
from app.domain.models import (
    DishCategory,
    MealPeriod,
    MealPlan,
    PantryLot,
    PlannedDish,
    QuantityUnit,
    Recipe,
    RecipeIngredient,
    StockMovement,
)
from app.domain.planner import generate_period_plan


def _make_ingredient_id():
    return uuid4()


def _make_recipe(ingredient_id):
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
                ingredient_id=ingredient_id,
                ingredient_name="Thịt ba chỉ",
                quantity=Decimal("500"),
                unit=QuantityUnit.GRAM,
            )
        ],
    )


def _make_lot(ingredient_id):
    return PantryLot(
        id=uuid4(),
        ingredient_id=ingredient_id,
        ingredient_name="Thịt ba chỉ",
        purchased_quantity=Decimal("1"),
        remaining_quantity=Decimal("1"),
        unit=QuantityUnit.KILOGRAM,
        purchased_at=datetime.now(),
    )


def test_domain_models_have_no_user_id_field():
    """PantryLot, MealPlan, StockMovement không được chứa trường user_id."""
    for model in (PantryLot, MealPlan, StockMovement):
        field_names = {f.name for f in fields(model)}
        msg = (
            f"{model.__name__} vẫn còn trường user_id "
            "(vi phạm kiến trúc không lưu dữ liệu cá nhân)."
        )
        assert "user_id" not in field_names, msg


def test_meal_plan_and_planned_dish_have_no_user_id_field():
    """MealPlan và PlannedDish (dùng trong kế hoạch) không chứa user_id."""
    for model in (MealPlan, PlannedDish):
        field_names = {f.name for f in fields(model)}
        assert "user_id" not in field_names, f"{model.__name__} vẫn còn trường user_id."


def test_generate_period_plan_without_user_id_runs():
    """generate_period_plan không nhận user_id và vẫn trả về kế hoạch đúng."""
    ingredient_id = _make_ingredient_id()
    recipe = _make_recipe(ingredient_id)

    meal_plans, shopping_list = generate_period_plan(
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 2),
        recipes=[recipe],
        current_pantry_lots=[],
        allow_leftovers=False,
    )

    assert len(meal_plans) == 4  # 2 ngày x 2 khung bữa (lunch, dinner)
    for plan in meal_plans:
        assert plan.planned_for in (date(2026, 11, 1), date(2026, 11, 2))
        assert plan.meal_period in (MealPeriod.LUNCH, MealPeriod.DINNER)
    assert len(shopping_list) > 0


def test_deduct_recipe_stock_fifo_without_user_id_runs():
    """deduct_recipe_stock_fifo không nhận user_id và vẫn trừ kho FIFO đúng."""
    ingredient_id = _make_ingredient_id()
    recipe = _make_recipe(ingredient_id)  # cần 500g
    lot = _make_lot(ingredient_id)  # có 1 kg
    meal_plan_id = uuid4()

    result = deduct_recipe_stock_fifo(
        pantry_lots=[lot],
        recipe=recipe,
        meal_plan_id=meal_plan_id,
        idempotency_key="key_no_user",
    )

    assert lot.remaining_quantity == Decimal("0.5")  # 1 kg - 500g = 500g = 0.5 kg
    assert len(result.movements) == 1
    assert result.movements[0].pantry_lot_id == lot.id
    assert result.movements[0].quantity_delta == Decimal("-0.5")  # 500g = 0.5 kg (đơn vị lot)
    assert result.movements[0].meal_plan_id == meal_plan_id
