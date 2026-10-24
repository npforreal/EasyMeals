"""Meal planning algorithm enforcing balance, category limits, and the no-repeat rule."""

from collections import defaultdict
from datetime import date, timedelta
from uuid import UUID, uuid4

from app.domain.inventory import check_recipe_stock
from app.domain.models import (
    DishCategory,
    MealPeriod,
    MealPlan,
    PantryLot,
    PlannedDish,
    Recipe,
    ShoppingItem,
)

MAX_DISHES_PER_CATEGORY = 2


class DishLimitExceededError(ValueError):
    """Raised when a meal contains more than 2 dishes in one category."""

    pass


class DishRepeatInPeriodError(ValueError):
    """Raised when a dish is scheduled to be cooked more than once in the same period."""

    pass


def validate_meal_dish_limits(dishes: list[PlannedDish]) -> None:
    """Ensure at most 2 dishes per category in a meal."""
    category_counts: dict[DishCategory, int] = defaultdict(int)
    for dish in dishes:
        category_counts[dish.category] += 1
        if category_counts[dish.category] > MAX_DISHES_PER_CATEGORY:
            raise DishLimitExceededError(
                f"Một bữa ăn chỉ được có tối đa {MAX_DISHES_PER_CATEGORY} "
                f"món thuộc nhóm '{dish.category.value}'"
            )


def generate_period_plan(
    start_date: date,
    end_date: date,
    recipes: list[Recipe],
    current_pantry_lots: list[PantryLot],
    user_id: UUID | None = None,
    periods: list[MealPeriod] | None = None,
    allow_leftovers: bool = True,
) -> tuple[list[MealPlan], list[ShoppingItem]]:
    """Generate meal plans for the specified period.

    Enforces:
      1. At most 2 dishes per category (man, rau, canh) per meal. Standard
      target: 1 man, 1 rau, 1 canh.
      2. NO REPEAT RULE: A recipe cannot be newly cooked (is_leftover=False)
      more than once in the period.
      3. LEFTOVER UTILIZATION: Leftovers from earlier meals in the period can
      be scheduled in later meals.
      4. SHOPPING LIST: If pantry stock runs out of non-repeating dishes,
      pick suitable unique recipes
         and aggregate missing ingredients into a shopping list.
    """
    if periods is None:
        periods = [MealPeriod.LUNCH, MealPeriod.DINNER]

    total_days = (end_date - start_date).days + 1
    if total_days <= 0:
        raise ValueError("Ngày kết thúc phải lớn hơn hoặc bằng ngày bắt đầu.")

    period_id = uuid4()
    recipes_by_cat: dict[DishCategory, list[Recipe]] = {
        DishCategory.MAN: [r for r in recipes if r.category == DishCategory.MAN],
        DishCategory.RAU: [r for r in recipes if r.category == DishCategory.RAU],
        DishCategory.CANH: [r for r in recipes if r.category == DishCategory.CANH],
    }

    # Track simulated pantry stock to evaluate availability as we plan
    simulated_lots: list[PantryLot] = [
        PantryLot(
            id=lot.id,
            user_id=lot.user_id,
            ingredient_id=lot.ingredient_id,
            ingredient_name=lot.ingredient_name,
            purchased_quantity=lot.purchased_quantity,
            remaining_quantity=lot.remaining_quantity,
            unit=lot.unit,
            purchased_at=lot.purchased_at,
            expires_at=lot.expires_at,
            created_at=lot.created_at,
        )
        for lot in current_pantry_lots
    ]

    cooked_recipe_ids_in_period: set[UUID] = set()
    available_leftovers: list[PlannedDish] = []
    meal_plans: list[MealPlan] = []
    shopping_items_map: dict[UUID, ShoppingItem] = {}

    current_d = start_date
    while current_d <= end_date:
        for period in periods:
            meal_plan = MealPlan(
                id=uuid4(),
                user_id=user_id,
                planned_for=current_d,
                meal_period=period,
                period_id=period_id,
            )

            # Target standard balanced menu: 1 món mặn, 1 món rau, 1 món canh
            for cat in [DishCategory.MAN, DishCategory.RAU, DishCategory.CANH]:
                dish_chosen: PlannedDish | None = None

                # 1. Try to use an available leftover dish from a previous meal
                if allow_leftovers and available_leftovers:
                    for idx, leftover in enumerate(available_leftovers):
                        if leftover.category == cat:
                            dish_chosen = PlannedDish(
                                id=uuid4(),
                                meal_plan_id=meal_plan.id,
                                recipe_id=leftover.recipe_id,
                                recipe_name=f"{leftover.recipe_name} (Ăn lại)",
                                category=cat,
                                is_leftover=True,
                                original_dish_id=leftover.id,
                            )
                            available_leftovers.pop(idx)
                            break

                # 2. If no leftover used, pick a fresh recipe respecting the NO-REPEAT rule
                if not dish_chosen:
                    candidate_recipes = [
                        r for r in recipes_by_cat[cat] if r.id not in cooked_recipe_ids_in_period
                    ]

                    # First priority: Recipes that can be cooked with current simulated stock
                    fully_stocked_recipe: Recipe | None = None
                    for r in candidate_recipes:
                        can_cook, _ = check_recipe_stock(r, simulated_lots)
                        if can_cook:
                            fully_stocked_recipe = r
                            break

                    chosen_recipe: Recipe | None = None
                    if fully_stocked_recipe:
                        chosen_recipe = fully_stocked_recipe
                        # Deduct from simulated stock
                        for req in chosen_recipe.ingredients:
                            needed = req.quantity
                            for lot in simulated_lots:
                                if (
                                    lot.ingredient_id == req.ingredient_id
                                    and lot.remaining_quantity > 0
                                ):
                                    # Deduct simplified for simulation
                                    take = min(lot.remaining_quantity, needed)
                                    lot.remaining_quantity -= take
                                    needed -= take
                                    if needed <= 0:
                                        break
                    elif candidate_recipes:
                        # Stock is insufficient for any remaining fresh recipe in this category.
                        # Pick the first non-repeating recipe and generate
                        # shopping items for deficits
                        chosen_recipe = candidate_recipes[0]
                        _, deficits = check_recipe_stock(chosen_recipe, simulated_lots)
                        for ing_id, (ing_name, missing_qty, unit) in deficits.items():
                            if ing_id not in shopping_items_map:
                                shopping_items_map[ing_id] = ShoppingItem(
                                    ingredient_id=ing_id,
                                    ingredient_name=ing_name,
                                    needed_quantity=missing_qty,
                                    unit=unit,
                                    dish_names=[chosen_recipe.name],
                                )
                            else:
                                shopping_items_map[ing_id].needed_quantity += missing_qty
                                if chosen_recipe.name not in shopping_items_map[ing_id].dish_names:
                                    shopping_items_map[ing_id].dish_names.append(chosen_recipe.name)

                    if chosen_recipe:
                        cooked_dish = PlannedDish(
                            id=uuid4(),
                            meal_plan_id=meal_plan.id,
                            recipe_id=chosen_recipe.id,
                            recipe_name=chosen_recipe.name,
                            category=cat,
                            is_leftover=False,
                        )
                        dish_chosen = cooked_dish
                        # Mark this recipe as cooked in this period -> DO NOT REPEAT!
                        cooked_recipe_ids_in_period.add(chosen_recipe.id)

                        # If servings >= 4 and for a smaller meal, we can
                        # potentially save 1 leftover portion
                        # Example: Thịt kho tàu or Canh chua can yield 1
                        # leftover for dinner/next day lunch
                        if allow_leftovers and chosen_recipe.servings >= 4:
                            available_leftovers.append(cooked_dish)

                if dish_chosen:
                    meal_plan.dishes.append(dish_chosen)

            validate_meal_dish_limits(meal_plan.dishes)
            meal_plans.append(meal_plan)

        current_d += timedelta(days=1)

    return meal_plans, list(shopping_items_map.values())
