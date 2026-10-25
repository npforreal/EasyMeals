"""Meal planning algorithm enforcing balance, category limits, and the no-repeat rule."""

from collections import defaultdict
from datetime import date, timedelta
from uuid import UUID, uuid4

from app.constants import (
    LEFTOVER_DEFAULT_DAYS,
    LEFTOVER_MAX_DAYS,
    LEFTOVER_MIN_DAYS,
    PLAN_MAX_DAYS,
    PLAN_MIN_DAYS,
)
from app.domain.inventory import (
    aggregate_requirements,
    check_recipe_stock,
    consume_available,
)
from app.domain.models import (
    UNIT_DIMENSIONS,
    DishCategory,
    IngredientConversion,
    MealPeriod,
    MealPlan,
    PantryLot,
    PlannedDish,
    Recipe,
    ShoppingItem,
    convert_quantity,
)

MAX_DISHES_PER_CATEGORY = 2


class LeftoverDaysOutOfRangeError(ValueError):
    """Raised when the leftover reuse window is outside the allowed 1-3 days."""

    pass


def _validate_leftover_days(leftover_days: int) -> int:
    """Đồ dư dùng lại trong tối đa 2 ngày (mặc định), cấu hình được trong 1-3 ngày."""
    if not LEFTOVER_MIN_DAYS <= leftover_days <= LEFTOVER_MAX_DAYS:
        raise LeftoverDaysOutOfRangeError(
            f"Số ngày dùng lại đồ dư phải từ {LEFTOVER_MIN_DAYS} đến {LEFTOVER_MAX_DAYS} ngày."
        )
    return leftover_days


class AvailableLeftover:
    """Sổ cái phần dư của một mẻ nấu.

    Mô hình hoá nhất quán:
      - số khẩu phần nấu: ``leftover``(PlannedDish).servings
      - đã dùng: ``portions_remaining`` giảm 1 sau mỗi lần phần dư được lên lịch
      - còn lại: ``portions_remaining`` (không bao giờ > số phần dư ban đầu,
        nên một mẻ không được dùng vô hạn lần)
      - ngày có thể dùng: từ ngày nấu tới ``deadline`` = ngày nấu + số ngày cấu hình
        (mặc định 2, cấu hình 1-3) - hết hạn định nghĩa theo ngày, tiện so sánh múi giờ.
    """

    __slots__ = ("leftover", "portions_remaining", "deadline")

    def __init__(self, leftover: PlannedDish, cook_date: date, leftover_days: int) -> None:
        self.leftover = leftover
        # Mỗi mẻ nấu (≥ 4 khẩu phần) chỉ dư đúng một phần ăn dùng lại một lần.
        # (Khẩu phần thực tế theo hộ gia đình sẽ hoàn thiện ở Giai đoạn C1.)
        self.portions_remaining = 1
        self.deadline = cook_date + timedelta(days=leftover_days)


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
    periods: list[MealPeriod] | None = None,
    allow_leftovers: bool = True,
    conversions: list[IngredientConversion] | None = None,
    raw_ingredient_names: dict[UUID, str] | None = None,
    leftover_days: int = LEFTOVER_DEFAULT_DAYS,
) -> tuple[list[MealPlan], list[ShoppingItem]]:
    """Generate meal plans for the specified period.

    Enforces:
      1. At most 2 dishes per category (man, rau, canh) per meal. Standard
      target: 1 man, 1 rau, 1 canh.
      2. NO REPEAT RULE: A recipe cannot be newly cooked (is_leftover=False)
      more than once in the period.
      3. LEFTOVER UTILIZATION: Leftovers from earlier meals in the period can
      be scheduled in later meals. Mỗi phần dư dùng lại đúng một lần và chỉ
      trong `leftover_days` ngày kể từ ngày nấu (mặc định 2, cấu hình 1-3).
      4. SHOPPING LIST: If pantry stock runs out of non-repeating dishes,
      pick suitable unique recipes
         and aggregate missing ingredients into a shopping list.
    """
    _validate_leftover_days(leftover_days)
    if periods is None:
        periods = [MealPeriod.LUNCH, MealPeriod.DINNER]

    total_days = (end_date - start_date).days + 1
    if total_days < PLAN_MIN_DAYS or total_days > PLAN_MAX_DAYS:
        raise ValueError(f"Số ngày lập thực đơn phải từ {PLAN_MIN_DAYS} đến {PLAN_MAX_DAYS} ngày.")

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
    shopping_items_map: dict[tuple[UUID, str], ShoppingItem] = {}

    current_d = start_date
    while current_d <= end_date:
        # Lô đã quá hạn tại ngày đang lập kế hoạch không được tính là có hàng.
        # (cùng đối tượng với simulated_lots nên việc trừ kho mô phỏng vẫn có tác dụng)
        usable_lots = [
            lot for lot in simulated_lots if lot.expires_at is None or lot.expires_at >= current_d
        ]
        for period in periods:
            meal_plan = MealPlan(
                id=uuid4(),
                planned_for=current_d,
                meal_period=period,
                period_id=period_id,
            )

            # Target standard balanced menu: 1 món mặn, 1 món rau, 1 món canh
            for cat in [DishCategory.MAN, DishCategory.RAU, DishCategory.CANH]:
                dish_chosen: PlannedDish | None = None

                # 1. Try to use an available leftover dish from a previous meal
                if allow_leftovers and available_leftovers:
                    for idx, entry in enumerate(available_leftovers):
                        leftover = entry.leftover
                        # Hạn an toàn: phần dư chỉ dùng được tới deadline của mẻ nấu.
                        if entry.portions_remaining <= 0 or current_d > entry.deadline:
                            continue
                        if leftover.category == cat:
                            dish_chosen = PlannedDish(
                                id=uuid4(),
                                meal_plan_id=meal_plan.id,
                                recipe_id=leftover.recipe_id,
                                recipe_name=leftover.recipe_name,
                                category=cat,
                                is_leftover=True,
                                original_dish_id=leftover.id,
                                servings=leftover.servings,
                            )
                            # Trừ lượng đã dùng trong sổ cái: mỗi phần dư dùng lại một lần.
                            entry.portions_remaining -= 1
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
                        can_cook, _ = check_recipe_stock(r, usable_lots, conversions=conversions)
                        if can_cook:
                            fully_stocked_recipe = r
                            break

                    chosen_recipe: Recipe | None = None
                    if fully_stocked_recipe:
                        chosen_recipe = fully_stocked_recipe
                        # Trừ kho mô phỏng (có quy đổi đơn vị và nguyên liệu, theo FIFO)
                        for req in aggregate_requirements(chosen_recipe):
                            consume_available(
                                usable_lots,
                                req.ingredient_id,
                                req.quantity,
                                req.unit,
                                conversions=conversions,
                            )
                    elif candidate_recipes:
                        # Stock is insufficient for any remaining fresh recipe in this category.
                        # Pick the first non-repeating recipe and generate
                        # shopping items for deficits
                        chosen_recipe = candidate_recipes[0]
                        _, deficits = check_recipe_stock(
                            chosen_recipe, usable_lots, conversions=conversions
                        )
                        # Phần đã có trong kho được dùng cho món này, để món sau không đếm lại.
                        for req in aggregate_requirements(chosen_recipe):
                            consume_available(
                                usable_lots,
                                req.ingredient_id,
                                req.quantity,
                                req.unit,
                                conversions=conversions,
                            )

                        target_conv_map = (
                            {c.to_ingredient_id: c for c in conversions} if conversions else {}
                        )

                        for ing_id, (ing_name, missing_qty, unit) in deficits.items():
                            # Nếu nguyên liệu thiếu có quy đổi từ nguyên liệu gốc (ví dụ Cơm -> Gạo)
                            if ing_id in target_conv_map:
                                conv = target_conv_map[ing_id]
                                missing_in_to = convert_quantity(missing_qty, unit, conv.to_unit)
                                raw_needed = missing_in_to / conv.ratio
                                actual_ing_id = conv.from_ingredient_id
                                actual_unit = conv.from_unit
                                actual_qty = raw_needed
                                raw_name = (
                                    raw_ingredient_names.get(actual_ing_id)
                                    if raw_ingredient_names
                                    else None
                                ) or f"Nguyên liệu gốc cho {ing_name}"
                                actual_name = raw_name
                            else:
                                actual_ing_id = ing_id
                                actual_unit = unit
                                actual_qty = missing_qty
                                actual_name = ing_name

                            key = (actual_ing_id, UNIT_DIMENSIONS[actual_unit])
                            item = shopping_items_map.get(key)
                            if item is None:
                                shopping_items_map[key] = ShoppingItem(
                                    ingredient_id=actual_ing_id,
                                    ingredient_name=actual_name,
                                    needed_quantity=actual_qty,
                                    unit=actual_unit,
                                    dish_names=[chosen_recipe.name],
                                )
                            else:
                                item.needed_quantity += convert_quantity(
                                    actual_qty, actual_unit, item.unit
                                )
                                if chosen_recipe.name not in item.dish_names:
                                    item.dish_names.append(chosen_recipe.name)

                    if chosen_recipe:
                        cooked_dish = PlannedDish(
                            id=uuid4(),
                            meal_plan_id=meal_plan.id,
                            recipe_id=chosen_recipe.id,
                            recipe_name=chosen_recipe.name,
                            category=cat,
                            is_leftover=False,
                            servings=chosen_recipe.servings,
                        )
                        dish_chosen = cooked_dish
                        # Mark this recipe as cooked in this period -> DO NOT REPEAT!
                        cooked_recipe_ids_in_period.add(chosen_recipe.id)

                        # If servings >= 4 and for a smaller meal, we can
                        # potentially save 1 leftover portion
                        # Example: Thịt kho tàu or Canh chua can yield 1
                        # leftover for dinner/next day lunch
                        if allow_leftovers and chosen_recipe.servings >= 4:
                            available_leftovers.append(
                                AvailableLeftover(cooked_dish, current_d, leftover_days)
                            )

                if dish_chosen:
                    meal_plan.dishes.append(dish_chosen)

            validate_meal_dish_limits(meal_plan.dishes)
            meal_plans.append(meal_plan)

        current_d += timedelta(days=1)

    return meal_plans, list(shopping_items_map.values())
