from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.models import (
    DishCategory,
    PlannedDish,
)
from app.domain.planner import (
    DishLimitExceededError,
    generate_period_plan,
    validate_meal_dish_limits,
)
from app.storage.repository import InMemoryRepository


def test_validate_meal_dish_limits_success():
    meal_id = uuid4()
    dishes = [
        PlannedDish(
            id=uuid4(),
            meal_plan_id=meal_id,
            recipe_id=uuid4(),
            recipe_name="Thịt kho",
            category=DishCategory.MAN,
        ),
        PlannedDish(
            id=uuid4(),
            meal_plan_id=meal_id,
            recipe_id=uuid4(),
            recipe_name="Gà kho",
            category=DishCategory.MAN,
        ),
        PlannedDish(
            id=uuid4(),
            meal_plan_id=meal_id,
            recipe_id=uuid4(),
            recipe_name="Rau muống",
            category=DishCategory.RAU,
        ),
        PlannedDish(
            id=uuid4(),
            meal_plan_id=meal_id,
            recipe_id=uuid4(),
            recipe_name="Canh chua",
            category=DishCategory.CANH,
        ),
    ]
    # 2 man, 1 rau, 1 canh -> OK
    validate_meal_dish_limits(dishes)


def test_validate_meal_dish_limits_exceeded():
    meal_id = uuid4()
    dishes = [
        PlannedDish(
            id=uuid4(),
            meal_plan_id=meal_id,
            recipe_id=uuid4(),
            recipe_name="Món 1",
            category=DishCategory.MAN,
        ),
        PlannedDish(
            id=uuid4(),
            meal_plan_id=meal_id,
            recipe_id=uuid4(),
            recipe_name="Món 2",
            category=DishCategory.MAN,
        ),
        PlannedDish(
            id=uuid4(),
            meal_plan_id=meal_id,
            recipe_id=uuid4(),
            recipe_name="Món 3",
            category=DishCategory.MAN,
        ),
    ]
    # 3 man -> Raises error
    with pytest.raises(DishLimitExceededError):
        validate_meal_dish_limits(dishes)


def test_no_repeat_dishes_in_period():
    """Verify that NO recipe is cooked freshly more than once within the planning period."""
    repo = InMemoryRepository()
    recipes = repo.get_recipes()
    user_id = uuid4()

    start = date(2026, 11, 1)
    end = date(2026, 11, 4)  # 4 days x 2 meals = 8 meals

    meal_plans, shopping_list = generate_period_plan(
        user_id=user_id,
        start_date=start,
        end_date=end,
        recipes=recipes,
        current_pantry_lots=[],
        allow_leftovers=True,
    )

    assert len(meal_plans) == 8

    # Collect all freshly cooked recipe IDs across the whole period
    fresh_recipe_ids: list = []
    for plan in meal_plans:
        for dish in plan.dishes:
            if not dish.is_leftover:
                fresh_recipe_ids.append(dish.recipe_id)

    # Every freshly cooked recipe ID must be unique (no duplicates in the period)
    assert len(fresh_recipe_ids) == len(set(fresh_recipe_ids)), (
        "Món ăn nấu mới không được lặp lại trong 1 đợt!"
    )


def test_leftovers_allowed_in_period():
    """Verify that leftover dishes can be reused in later meals."""
    repo = InMemoryRepository()
    recipes = repo.get_recipes()
    user_id = uuid4()

    start = date(2026, 11, 1)
    end = date(2026, 11, 7)  # 7 days

    meal_plans, _ = generate_period_plan(
        user_id=user_id,
        start_date=start,
        end_date=end,
        recipes=recipes,
        current_pantry_lots=[],
        allow_leftovers=True,
    )

    leftover_dishes = [dish for plan in meal_plans for dish in plan.dishes if dish.is_leftover]
    # In a 7-day period with recipes with servings >= 4, leftovers should be scheduled
    assert len(leftover_dishes) > 0


def test_shopping_list_generated_when_stock_deficit():
    """When pantry stock is empty or insufficient, shopping list is generated
    for the unique recipes."""
    repo = InMemoryRepository()
    recipes = repo.get_recipes()
    user_id = uuid4()

    start = date(2026, 11, 1)
    end = date(2026, 11, 2)  # 2 days

    meal_plans, shopping_list = generate_period_plan(
        user_id=user_id,
        start_date=start,
        end_date=end,
        recipes=recipes,
        current_pantry_lots=[],  # Empty pantry
        allow_leftovers=False,
    )

    assert len(shopping_list) > 0
    # Every shopping item has positive needed quantity
    for item in shopping_list:
        assert item.needed_quantity > Decimal("0")
        assert len(item.dish_names) > 0
