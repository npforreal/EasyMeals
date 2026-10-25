"""Meal planning algorithm enforcing balance, category limits, and the no-repeat rule."""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
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


class MealAlreadyEatenError(ValueError):
    """Raised when attempting to edit, remove, or regenerate a meal that has already been eaten."""

    pass


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


def merge_new_plans_into_existing(
    existing: list[MealPlan],
    new_plans: list[MealPlan],
    mode: str = "replace",
) -> list[MealPlan]:
    """Gộp đợt thực đơn mới vào thực đơn cũ an toàn (A2 - Vòng 13).

    Quy tắc theo quyết định chủ dự án §0:
      - mode "replace" (= "Thay các bữa chưa ăn trong khoảng ngày này"):
        bữa chưa ăn trong khoảng ngày của đợt mới bị thay; bữa đã ăn luôn
        được giữ; bữa chưa ăn ngoài khoảng ngày giữ nguyên.
      - mode "keep" (= "Giữ thực đơn cũ, chỉ thêm ngày chưa có"): giữ nguyên
        toàn bộ thực đơn cũ (kể cả bữa chưa ăn trong khoảng ngày), chỉ thêm
        các bữa của đợt mới ở ngày chưa từng có trong thực đơn cũ.
      - Bữa của đợt mới ở ngày đã có trong thực đơn cũ nhưng ở chế độ "keep"
        bị bỏ qua. Bản ghi trùng id bị khử (idempotency theo mã định danh bữa).
    """
    existing = list(existing or [])
    if not new_plans:
        return existing
    if mode not in ("replace", "keep"):
        raise ValueError(f"Chế độ gộp thực đơn không hợp lệ: {mode!r}")

    if mode == "replace":
        range_start = min(p.planned_for for p in new_plans)
        range_end = max(p.planned_for for p in new_plans)

    kept: list[MealPlan] = []
    seen_ids: set[UUID] = set()
    for plan in existing:
        if plan.id in seen_ids:
            continue
        seen_ids.add(plan.id)
        if mode == "replace" and not plan.eaten_at and range_start <= plan.planned_for <= range_end:
            # Thay bữa chưa ăn trong khoảng ngày này.
            continue
        kept.append(plan)
    if mode == "keep":
        covered_dates = {p.planned_for for p in existing}
        for plan in new_plans:
            if plan.id in seen_ids or plan.planned_for in covered_dates:
                continue
            seen_ids.add(plan.id)
            kept.append(plan)
    else:
        for plan in new_plans:
            if plan.id in seen_ids:
                continue
            seen_ids.add(plan.id)
            kept.append(plan)
    return kept


def regenerate_single_meal(
    target_meal_plan_id: UUID,
    all_meal_plans: list[MealPlan],
    recipes: list[Recipe],
    current_pantry_lots: list[PantryLot],
    allow_leftovers: bool = True,
    conversions: list[IngredientConversion] | None = None,
    raw_ingredient_names: dict[UUID, str] | None = None,
    leftover_days: int = LEFTOVER_DEFAULT_DAYS,
) -> MealPlan:
    """Sinh lại 1 bữa đơn lẻ mà không ảnh hưởng các bữa khác (B1 & B2).

    Quy tắc:
      - B2: Nếu bữa đã ăn (eaten_at is not None), quăng MealAlreadyEatenError.
      - B1: Thu thập danh sách recipe_id đã nấu trong các bữa khác của cùng đợt
        (để tuân thủ quy tắc không lặp món trong đợt - NO REPEAT RULE).
      - Lập lại các món (1 mặn, 1 rau, 1 canh) cho bữa này.
      - Giữ nguyên id, planned_for, meal_period, period_id của bữa cũ.
    """
    _validate_leftover_days(leftover_days)
    target_plan = next((p for p in all_meal_plans if p.id == target_meal_plan_id), None)
    if target_plan is None:
        raise ValueError(f"Không tìm thấy bữa ăn có ID {target_meal_plan_id}")

    if target_plan.eaten_at is not None:
        raise MealAlreadyEatenError(
            "Bữa ăn này đã được đánh dấu ăn và ghi nhận vào kho. "
            "Hãy hoàn tác bữa ăn trước nếu bạn muốn đổi món."
        )

    # Thu thập các món đã nấu trong các bữa KHÁC của cùng đợt (is_leftover = False)
    other_cooked_recipe_ids: set[UUID] = {
        dish.recipe_id
        for p in all_meal_plans
        if p.id != target_meal_plan_id
        for dish in p.dishes
        if not dish.is_leftover
    }

    recipes_by_cat: dict[DishCategory, list[Recipe]] = {
        DishCategory.MAN: [r for r in recipes if r.category == DishCategory.MAN],
        DishCategory.RAU: [r for r in recipes if r.category == DishCategory.RAU],
        DishCategory.CANH: [r for r in recipes if r.category == DishCategory.CANH],
    }

    usable_lots = [
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
        if lot.expires_at is None or lot.expires_at >= target_plan.planned_for
    ]

    new_dishes: list[PlannedDish] = []
    for cat in [DishCategory.MAN, DishCategory.RAU, DishCategory.CANH]:
        candidate_recipes = [r for r in recipes_by_cat[cat] if r.id not in other_cooked_recipe_ids]
        if not candidate_recipes:
            candidate_recipes = [
                r for r in recipes_by_cat[cat] if r.id not in {d.recipe_id for d in new_dishes}
            ]

        chosen_recipe: Recipe | None = None
        for r in candidate_recipes:
            can_cook, _ = check_recipe_stock(r, usable_lots, conversions=conversions)
            if can_cook:
                chosen_recipe = r
                break

        if not chosen_recipe and candidate_recipes:
            chosen_recipe = candidate_recipes[0]

        if chosen_recipe:
            for req in aggregate_requirements(chosen_recipe):
                consume_available(
                    usable_lots,
                    req.ingredient_id,
                    req.quantity,
                    req.unit,
                    conversions=conversions,
                )
            new_dishes.append(
                PlannedDish(
                    id=uuid4(),
                    meal_plan_id=target_plan.id,
                    recipe_id=chosen_recipe.id,
                    recipe_name=chosen_recipe.name,
                    category=cat,
                    is_leftover=False,
                    servings=chosen_recipe.servings,
                )
            )

    validate_meal_dish_limits(new_dishes)
    return MealPlan(
        id=target_plan.id,
        planned_for=target_plan.planned_for,
        meal_period=target_plan.meal_period,
        period_id=target_plan.period_id,
        eaten_at=None,
        notes=target_plan.notes,
        dishes=new_dishes,
        created_at=target_plan.created_at,
    )


def recompute_shopping_list(
    meal_plans: list[MealPlan],
    current_pantry_lots: list[PantryLot],
    recipes: list[Recipe],
    conversions: list[IngredientConversion] | None = None,
    raw_ingredient_names: dict[UUID, str] | None = None,
    ingredient_categories: dict[UUID, str] | None = None,
) -> list[ShoppingItem]:
    """Tính lại danh sách mua từ các bữa chưa ăn dựa trên tồn kho hiện tại (B1 & B3)."""
    recipes_map: dict[UUID, Recipe] = {r.id: r for r in recipes}
    target_conv_map = {c.to_ingredient_id: c for c in conversions} if conversions else {}

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

    shopping_items_map: dict[tuple[UUID, str], ShoppingItem] = {}

    uneaten_plans = sorted(
        [p for p in meal_plans if p.eaten_at is None],
        key=lambda p: (p.planned_for, p.meal_period),
    )

    for meal in uneaten_plans:
        usable_lots = [
            lot
            for lot in simulated_lots
            if lot.expires_at is None or lot.expires_at >= meal.planned_for
        ]

        for dish in meal.dishes:
            if dish.is_leftover:
                continue
            recipe = recipes_map.get(dish.recipe_id)
            if not recipe:
                continue

            _, deficits = check_recipe_stock(recipe, usable_lots, conversions=conversions)
            for req in aggregate_requirements(recipe):
                consume_available(
                    usable_lots,
                    req.ingredient_id,
                    req.quantity,
                    req.unit,
                    conversions=conversions,
                )

            for ing_id, (ing_name, missing_qty, unit) in deficits.items():
                if ing_id in target_conv_map:
                    conv = target_conv_map[ing_id]
                    missing_in_to = convert_quantity(missing_qty, unit, conv.to_unit)
                    raw_needed = missing_in_to / conv.ratio
                    actual_ing_id = conv.from_ingredient_id
                    actual_unit = conv.from_unit
                    actual_qty = raw_needed
                    raw_name = (
                        raw_ingredient_names.get(actual_ing_id) if raw_ingredient_names else None
                    ) or f"Nguyên liệu gốc cho {ing_name}"
                    actual_name = raw_name
                else:
                    actual_ing_id = ing_id
                    actual_unit = unit
                    actual_qty = missing_qty
                    actual_name = ing_name

                key = (actual_ing_id, UNIT_DIMENSIONS[actual_unit])
                item = shopping_items_map.get(key)
                cat = (
                    ingredient_categories.get(actual_ing_id, "khac")
                    if ingredient_categories
                    else "khac"
                )
                if item is None:
                    shopping_items_map[key] = ShoppingItem(
                        ingredient_id=actual_ing_id,
                        ingredient_name=actual_name,
                        needed_quantity=actual_qty,
                        unit=actual_unit,
                        dish_names=[recipe.name],
                        category=cat,
                        source="plan",
                    )
                else:
                    item.needed_quantity += convert_quantity(actual_qty, actual_unit, item.unit)
                    if recipe.name not in item.dish_names:
                        item.dish_names.append(recipe.name)

    return list(shopping_items_map.values())


def calculate_shopping_budget(items: list[ShoppingItem | dict]) -> dict:
    """B4: Tính toán ngân sách từ giá người dùng nhập.

    TUYỆT ĐỐI không bịa giá thị trường khi người dùng chưa nhập giá.
    """
    total_estimated = Decimal("0")
    total_spent = Decimal("0")
    items_with_price = 0
    total_items = len(items)

    for it in items:
        price = it.price if isinstance(it, ShoppingItem) else it.get("price")
        is_bought = (
            it.is_bought
            if isinstance(it, ShoppingItem)
            else (it.get("is_bought") or it.get("bought", False))
        )
        if price is not None:
            p = Decimal(str(price))
            if p > Decimal("0"):
                total_estimated += p
                items_with_price += 1
                if is_bought:
                    total_spent += p

    return {
        "total_estimated_budget": total_estimated,
        "total_spent": total_spent,
        "items_with_price_count": items_with_price,
        "total_items_count": total_items,
    }


STANDARD_SHOPPING_CATEGORIES = [
    "thit",
    "gia_cam",
    "hai_san",
    "trung_sua",
    "rau_cu",
    "cu_qua",
    "gao_bot_mi",
    "gia_vi",
    "nuoc_cham_dau",
    "khac",
]


def group_shopping_items_by_category(
    items: list[ShoppingItem | dict],
    categories_order: list[str] | None = None,
) -> dict[str, list]:
    """B3: Nhóm danh sách mua theo loại/quầy hàng."""
    order = categories_order or STANDARD_SHOPPING_CATEGORIES
    grouped: dict[str, list] = {c: [] for c in order}

    for it in items:
        cat = it.category if isinstance(it, ShoppingItem) else (it.get("category") or "khac")
        if not cat or cat not in grouped:
            cat = "khac"
        grouped[cat].append(it)

    return {cat: items_list for cat, items_list in grouped.items() if items_list}


def swap_dish_in_meal(
    meal_plan: MealPlan,
    old_dish_id: UUID,
    new_recipe: Recipe,
    all_plans_in_period: list[MealPlan] | None = None,
) -> MealPlan:
    """B1 & B2: Đổi 1 món cụ thể trong bữa sang món mới."""
    if meal_plan.eaten_at is not None:
        raise MealAlreadyEatenError(
            "Bữa ăn này đã được đánh dấu ăn và ghi nhận vào kho. "
            "Hãy hoàn tác bữa ăn trước nếu bạn muốn đổi món."
        )

    dish_idx = next((i for i, d in enumerate(meal_plan.dishes) if d.id == old_dish_id), None)
    if dish_idx is None:
        raise ValueError(f"Không tìm thấy món có ID {old_dish_id} trong bữa ăn.")

    if all_plans_in_period:
        other_recipe_ids = {
            d.recipe_id
            for p in all_plans_in_period
            for d in p.dishes
            if not d.is_leftover and (p.id != meal_plan.id or d.id != old_dish_id)
        }
        if new_recipe.id in other_recipe_ids:
            raise ValueError(f"Món '{new_recipe.name}' đã được lên lịch trong chu kỳ thực đơn này.")

    new_dish = PlannedDish(
        id=uuid4(),
        meal_plan_id=meal_plan.id,
        recipe_id=new_recipe.id,
        recipe_name=new_recipe.name,
        category=new_recipe.category,
        servings=new_recipe.servings,
        is_leftover=False,
    )
    meal_plan.dishes[dish_idx] = new_dish
    return meal_plan


def add_dish_to_meal(
    meal_plan: MealPlan,
    recipe: Recipe,
    servings: int | None = None,
) -> MealPlan:
    """B1 & B2: Thêm 1 món vào bữa ăn."""
    if meal_plan.eaten_at is not None:
        raise MealAlreadyEatenError(
            "Bữa ăn này đã được đánh dấu ăn và ghi nhận vào kho. "
            "Hãy hoàn tác bữa ăn trước nếu bạn muốn thêm món."
        )

    if any(d.recipe_id == recipe.id for d in meal_plan.dishes):
        raise ValueError(f"Món '{recipe.name}' đã có trong bữa ăn này.")

    cat_count = sum(1 for d in meal_plan.dishes if d.category == recipe.category)
    if cat_count >= MAX_DISHES_PER_CATEGORY:
        cat_val = recipe.category.value
        raise ValueError(
            f"Bữa ăn đã đạt giới hạn tối đa {MAX_DISHES_PER_CATEGORY} món cho nhóm {cat_val}."
        )

    new_dish = PlannedDish(
        id=uuid4(),
        meal_plan_id=meal_plan.id,
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        category=recipe.category,
        servings=servings or recipe.servings,
        is_leftover=False,
    )
    meal_plan.dishes.append(new_dish)
    return meal_plan


def remove_dish_from_meal(
    meal_plan: MealPlan,
    dish_id: UUID,
) -> MealPlan:
    """B1 & B2: Bỏ 1 món khỏi bữa ăn."""
    if meal_plan.eaten_at is not None:
        raise MealAlreadyEatenError(
            "Bữa ăn này đã được đánh dấu ăn và ghi nhận vào kho. "
            "Hãy hoàn tác bữa ăn trước nếu bạn muốn bỏ món."
        )

    dish_idx = next((i for i, d in enumerate(meal_plan.dishes) if d.id == dish_id), None)
    if dish_idx is None:
        raise ValueError(f"Không tìm thấy món có ID {dish_id} trong bữa ăn.")

    if len(meal_plan.dishes) <= 1:
        raise ValueError("Không thể bỏ món duy nhất còn lại trong bữa ăn.")

    meal_plan.dishes.pop(dish_idx)
    return meal_plan


def reschedule_meal(
    meal_plan: MealPlan,
    new_date: date,
    new_period: MealPeriod,
    all_meal_plans: list[MealPlan],
) -> MealPlan:
    """B1 & B2: Chuyển ngày/bữa của một bữa ăn."""
    if meal_plan.eaten_at is not None:
        raise MealAlreadyEatenError(
            "Bữa ăn này đã được đánh dấu ăn và ghi nhận vào kho. "
            "Hãy hoàn tác bữa ăn trước nếu bạn muốn chuyển ngày/bữa."
        )

    conflict = any(
        p.id != meal_plan.id and p.planned_for == new_date and p.meal_period == new_period
        for p in all_meal_plans
    )
    if conflict:
        period_vn = "trưa" if new_period == MealPeriod.LUNCH else "tối"
        raise ValueError(f"Đã có bữa ăn khác được lên lịch vào bữa {period_vn} ngày {new_date}.")

    meal_plan.planned_for = new_date
    meal_plan.meal_period = new_period
    return meal_plan


def merge_compatible_shopping_items(
    items: list[ShoppingItem],
) -> list[ShoppingItem]:
    """B3: Gộp các món đi chợ cùng nguyên liệu và cùng thứ nguyên."""
    merged_map: dict[tuple[UUID, str], ShoppingItem] = {}

    for it in items:
        dim = UNIT_DIMENSIONS.get(it.unit)
        key = (it.ingredient_id, str(dim) if dim else str(it.unit))

        existing = merged_map.get(key)
        if existing is None:
            merged_map[key] = ShoppingItem(
                id=it.id,
                ingredient_id=it.ingredient_id,
                ingredient_name=it.ingredient_name,
                needed_quantity=it.needed_quantity,
                unit=it.unit,
                is_bought=it.is_bought,
                dish_names=list(it.dish_names),
                category=it.category,
                price=it.price,
                bought_quantity=it.bought_quantity,
                source=it.source,
            )
        else:
            qty_converted = convert_quantity(it.needed_quantity, it.unit, existing.unit)
            existing.needed_quantity += qty_converted
            for dn in it.dish_names:
                if dn not in existing.dish_names:
                    existing.dish_names.append(dn)
            if it.price and not existing.price:
                existing.price = it.price
            elif it.price and existing.price:
                existing.price += it.price
            existing.is_bought = existing.is_bought and it.is_bought

    return list(merged_map.values())
