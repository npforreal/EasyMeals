"""Shared planner ranking fixture checks used alongside the native/JS engines."""

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from app.domain.models import (
    DishCategory,
    HouseholdSettings,
    PantryLot,
    QuantityUnit,
    Recipe,
    RecipeIngredient,
)
from app.domain.planner import generate_period_plan

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "planner_preferences.json").read_text(encoding="utf-8")
)


def test_shared_preference_case_prioritizes_soon_expiring_stock():
    recipes = []
    for raw in FIXTURE["recipes"]:
        rid = UUID(raw["id"])
        recipes.append(
            Recipe(
                id=rid,
                name=raw["name"],
                category=DishCategory(raw["category"]),
                instructions=[],
                servings=raw["servings"],
                ingredients=[
                    RecipeIngredient(
                        recipe_id=rid,
                        ingredient_id=UUID(item["ingredient_id"]),
                        ingredient_name=item["ingredient_name"],
                        quantity=Decimal(item["quantity"]),
                        unit=QuantityUnit(item["unit"]),
                    )
                    for item in raw["ingredients"]
                ],
            )
        )
    pantry = [
        PantryLot(
            id=UUID(raw["id"]),
            ingredient_id=UUID(raw["ingredient_id"]),
            ingredient_name=raw["ingredient_name"],
            purchased_quantity=Decimal(raw["purchased_quantity"]),
            remaining_quantity=Decimal(raw["remaining_quantity"]),
            unit=QuantityUnit(raw["unit"]),
            purchased_at=datetime.fromisoformat(raw["purchased_at"]),
            expires_at=date.fromisoformat(raw["expires_at"]),
        )
        for raw in FIXTURE["pantry"]
    ]

    meals, _ = generate_period_plan(
        start_date=date.fromisoformat(FIXTURE["reference_date"]),
        end_date=date.fromisoformat(FIXTURE["reference_date"]),
        recipes=recipes,
        current_pantry_lots=pantry,
        allow_leftovers=False,
        household_settings=HouseholdSettings(meal_periods=FIXTURE["meal_periods"]),
        recently_cooked_recipe_ids={UUID(value) for value in FIXTURE["recently_cooked_recipe_ids"]},
        reference_date=date.fromisoformat(FIXTURE["reference_date"]),
    )
    selected = next(d for d in meals[0].dishes if d.category == DishCategory.MAN)
    assert str(selected.recipe_id) == FIXTURE["expected_recipe_id"]
    assert selected.selection_reason == FIXTURE["expected_reason"]

    recency = FIXTURE["recency_case"]
    recency_meals, _ = generate_period_plan(
        start_date=date.fromisoformat(FIXTURE["reference_date"]),
        end_date=date.fromisoformat(FIXTURE["reference_date"]),
        recipes=recipes,
        current_pantry_lots=pantry,
        allow_leftovers=False,
        household_settings=HouseholdSettings(meal_periods=FIXTURE["meal_periods"]),
        recently_cooked_recipe_ids={UUID(value) for value in recency["recently_cooked_recipe_ids"]},
    )
    recency_dish = next(d for d in recency_meals[0].dishes if d.category == DishCategory.MAN)
    assert str(recency_dish.recipe_id) == recency["expected_recipe_id"]
    assert recency_dish.selection_reason == recency["expected_reason"]
