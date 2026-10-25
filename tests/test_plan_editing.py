"""Tests for Plan Editing, History Protection, and Shopping Budget (Round 13 Phase B)."""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.models import (
    DishCategory,
    MealPeriod,
    MealPlan,
    PantryLot,
    PlannedDish,
    QuantityUnit,
    ShoppingItem,
)
from app.domain.planner import (
    MealAlreadyEatenError,
    add_dish_to_meal,
    calculate_shopping_budget,
    generate_period_plan,
    group_shopping_items_by_category,
    merge_compatible_shopping_items,
    recompute_shopping_list,
    regenerate_single_meal,
    remove_dish_from_meal,
    reschedule_meal,
    swap_dish_in_meal,
)
from app.storage.repository import InMemoryRepository


def test_regenerate_eaten_meal_raises_error():
    """B2 - Bảo vệ lịch sử: Không cho phép sinh lại bữa đã đánh dấu ăn."""
    meal = MealPlan(
        id=uuid4(),
        planned_for=date(2026, 10, 26),
        meal_period=MealPeriod.LUNCH,
        eaten_at=datetime(2026, 10, 26, 12, 0),
    )
    with pytest.raises(MealAlreadyEatenError):
        regenerate_single_meal(
            target_meal_plan_id=meal.id,
            all_meal_plans=[meal],
            recipes=[],
            current_pantry_lots=[],
        )


def test_regenerate_single_meal_respects_no_repeat():
    """B1 - Sinh lại 1 bữa không ảnh hưởng các bữa khác và không lặp món."""
    repo = InMemoryRepository()
    recipes = repo.get_recipes()
    pantry_lots: list[PantryLot] = []

    # Tạo kế hoạch 2 ngày (4 bữa: lunch/dinner day 1, lunch/dinner day 2)
    plans, _ = generate_period_plan(
        start_date=date(2026, 10, 26),
        end_date=date(2026, 10, 27),
        recipes=recipes,
        current_pantry_lots=pantry_lots,
        allow_leftovers=False,
    )
    assert len(plans) == 4

    target_meal = plans[2]  # Lunch day 2

    updated_meal = regenerate_single_meal(
        target_meal_plan_id=target_meal.id,
        all_meal_plans=plans,
        recipes=recipes,
        current_pantry_lots=pantry_lots,
        allow_leftovers=False,
    )

    assert updated_meal.id == target_meal.id
    assert updated_meal.planned_for == target_meal.planned_for
    assert updated_meal.meal_period == target_meal.meal_period
    assert len(updated_meal.dishes) > 0

    # Kiểm tra các món mới không trùng với các bữa còn lại
    other_recipe_ids = {
        d.recipe_id for p in plans if p.id != target_meal.id for d in p.dishes if not d.is_leftover
    }
    for d in updated_meal.dishes:
        if not d.is_leftover:
            assert d.recipe_id not in other_recipe_ids


def test_recompute_shopping_list_reflects_updated_plan():
    """B1 & B3 - Tính lại danh sách mua khi kế hoạch thay đổi."""
    repo = InMemoryRepository()
    recipes = repo.get_recipes()

    # Tạo kế hoạch 1 ngày 1 bữa
    plans, initial_shopping = generate_period_plan(
        start_date=date(2026, 10, 26),
        end_date=date(2026, 10, 26),
        recipes=recipes,
        current_pantry_lots=[],
        periods=[MealPeriod.LUNCH],
        allow_leftovers=False,
    )
    assert len(plans) == 1
    assert len(initial_shopping) > 0

    # Đổi 1 món trong bữa sang một công thức khác
    used_ids = {d.recipe_id for d in plans[0].dishes}
    candidates = [r for r in recipes if r.id not in used_ids and r.category == DishCategory.MAN]
    new_recipe = candidates[0]
    # Thay món mặn cũ bằng new_recipe
    man_dish_idx = next(i for i, d in enumerate(plans[0].dishes) if d.category == DishCategory.MAN)
    plans[0].dishes[man_dish_idx] = PlannedDish(
        id=uuid4(),
        meal_plan_id=plans[0].id,
        recipe_id=new_recipe.id,
        recipe_name=new_recipe.name,
        category=DishCategory.MAN,
        servings=new_recipe.servings,
    )

    recomputed = recompute_shopping_list(
        meal_plans=plans,
        current_pantry_lots=[],
        recipes=recipes,
    )

    # Tên món mới phải xuất hiện trong dish_names của các món cần mua
    dish_names_in_shopping = {name for item in recomputed for name in item.dish_names}
    assert new_recipe.name in dish_names_in_shopping


def test_shopping_budget_calculation():
    """B4 - Quản lý ngân sách: Chỉ tính từ giá người dùng nhập."""
    items = [
        ShoppingItem(
            ingredient_id=uuid4(),
            ingredient_name="Thịt ba chỉ",
            needed_quantity=Decimal("500"),
            unit=QuantityUnit.GRAM,
            dish_names=["Thịt kho"],
            price=Decimal("75000"),
            is_bought=True,
        ),
        ShoppingItem(
            ingredient_id=uuid4(),
            ingredient_name="Rau muống",
            needed_quantity=Decimal("300"),
            unit=QuantityUnit.GRAM,
            dish_names=["Rau xào"],
            price=Decimal("15000"),
            is_bought=False,
        ),
        ShoppingItem(
            ingredient_id=uuid4(),
            ingredient_name="Hành lá",
            needed_quantity=Decimal("50"),
            unit=QuantityUnit.GRAM,
            dish_names=["Canh"],
            price=None,  # Người dùng chưa nhập giá
            is_bought=False,
        ),
    ]

    budget = calculate_shopping_budget(items)
    # Tổng ngân sách dự kiến: 75,000 + 15,000 = 90,000
    assert budget["total_estimated_budget"] == Decimal("90000")
    # Đã mua: 75,000
    assert budget["total_spent"] == Decimal("75000")
    assert budget["items_with_price_count"] == 2
    assert budget["total_items_count"] == 3


def test_group_shopping_items_by_category():
    """B3 - Nhóm danh sách mua theo loại/quầy hàng."""
    items = [
        ShoppingItem(
            ingredient_id=uuid4(),
            ingredient_name="Thịt bò",
            needed_quantity=Decimal("300"),
            unit=QuantityUnit.GRAM,
            category="thit",
        ),
        ShoppingItem(
            ingredient_id=uuid4(),
            ingredient_name="Rau cải",
            needed_quantity=Decimal("400"),
            unit=QuantityUnit.GRAM,
            category="rau_cu",
        ),
        ShoppingItem(
            ingredient_id=uuid4(),
            ingredient_name="Nước mắm",
            needed_quantity=Decimal("50"),
            unit=QuantityUnit.MILLILITER,
            category="nuoc_cham_dau",
        ),
        ShoppingItem(
            ingredient_id=uuid4(),
            ingredient_name="Khăn giấy",
            needed_quantity=Decimal("1"),
            unit=QuantityUnit.PIECE,
            category="khac",
        ),
    ]

    grouped = group_shopping_items_by_category(items)
    assert "thit" in grouped
    assert "rau_cu" in grouped
    assert "nuoc_cham_dau" in grouped
    assert "khac" in grouped
    assert len(grouped["thit"]) == 1
    assert grouped["thit"][0].ingredient_name == "Thịt bò"


def test_swap_dish_in_meal_success_and_protection():
    """B1 & B2 - Đổi 1 món cụ thể trong bữa và kiểm tra bảo vệ bữa đã ăn."""
    repo = InMemoryRepository()
    recipes = repo.get_recipes()
    plans, _ = generate_period_plan(
        start_date=date(2026, 10, 26),
        end_date=date(2026, 10, 26),
        recipes=recipes,
        current_pantry_lots=[],
        periods=[MealPeriod.LUNCH],
        allow_leftovers=False,
    )
    plan = plans[0]
    old_dish = plan.dishes[0]

    # Tìm một món mới chưa có trong bữa
    existing_recipe_ids = {d.recipe_id for d in plan.dishes}
    new_recipe = [r for r in recipes if r.id not in existing_recipe_ids][0]

    # Đổi món thành công
    updated = swap_dish_in_meal(plan, old_dish.id, new_recipe, all_plans_in_period=plans)
    assert any(d.recipe_id == new_recipe.id for d in updated.dishes)
    assert not any(d.id == old_dish.id for d in updated.dishes)

    # Đánh dấu đã ăn -> đổi món phải ném MealAlreadyEatenError
    updated.eaten_at = datetime.now()
    another_recipe = [r for r in recipes if r.id not in {d.recipe_id for d in updated.dishes}][0]
    with pytest.raises(MealAlreadyEatenError):
        swap_dish_in_meal(updated, updated.dishes[0].id, another_recipe)


def test_add_and_remove_dish_in_meal():
    """B1 & B2 - Thêm món, kiểm tra giới hạn nhóm (<=2 món/nhóm), bỏ món và bảo vệ bữa đã ăn."""
    repo = InMemoryRepository()
    recipes = repo.get_recipes()
    plans, _ = generate_period_plan(
        start_date=date(2026, 10, 26),
        end_date=date(2026, 10, 26),
        recipes=recipes,
        current_pantry_lots=[],
        periods=[MealPeriod.LUNCH],
        allow_leftovers=False,
    )
    plan = plans[0]

    # Tìm một món mặn chưa có
    man_recipe = [
        r
        for r in recipes
        if r.category == DishCategory.MAN and r.id not in {d.recipe_id for d in plan.dishes}
    ][0]

    # Thêm món mặn thứ 2 (hợp lệ)
    initial_count = len(plan.dishes)
    add_dish_to_meal(plan, man_recipe)
    assert len(plan.dishes) == initial_count + 1

    # Thử thêm món mặn thứ 3 -> phải ném ValueError vì vượt trần 2 món/nhóm
    extra_man = [
        r
        for r in recipes
        if r.category == DishCategory.MAN and r.id not in {d.recipe_id for d in plan.dishes}
    ][0]
    with pytest.raises(ValueError, match="giới hạn tối đa 2 món"):
        add_dish_to_meal(plan, extra_man)

    # Bỏ món vừa thêm
    dish_to_remove = next(d for d in plan.dishes if d.recipe_id == man_recipe.id)
    remove_dish_from_meal(plan, dish_to_remove.id)
    assert len(plan.dishes) == initial_count

    # Bỏ đến khi chỉ còn 1 món thì không được bỏ tiếp
    while len(plan.dishes) > 1:
        plan.dishes.pop()
    with pytest.raises(ValueError, match="Không thể bỏ món duy nhất"):
        remove_dish_from_meal(plan, plan.dishes[0].id)


def test_reschedule_meal_and_conflict_check():
    """B1 & B2 - Chuyển ngày/bữa, kiểm tra trùng lặp và bảo vệ bữa đã ăn."""
    repo = InMemoryRepository()
    recipes = repo.get_recipes()
    plans, _ = generate_period_plan(
        start_date=date(2026, 10, 26),
        end_date=date(2026, 10, 27),
        recipes=recipes,
        current_pantry_lots=[],
        allow_leftovers=False,
    )
    # plans có 4 bữa: (26 trưa, 26 tối, 27 trưa, 27 tối)
    target = plans[0]  # 26 trưa

    # Chuyển tới 28 trưa (chưa có bữa nào) -> thành công
    reschedule_meal(target, date(2026, 10, 28), MealPeriod.LUNCH, plans)
    assert target.planned_for == date(2026, 10, 28)

    # Chuyển tới 27 tối (đã có bữa tối ngày 27) -> phải báo lỗi xung đột
    with pytest.raises(ValueError, match="Đã có bữa ăn khác"):
        reschedule_meal(target, date(2026, 10, 27), MealPeriod.DINNER, plans)

    # Đã ăn thì không được chuyển
    target.eaten_at = datetime.now()
    with pytest.raises(MealAlreadyEatenError):
        reschedule_meal(target, date(2026, 10, 29), MealPeriod.LUNCH, plans)


def test_merge_compatible_shopping_items():
    """B3 - Gộp các món đi chợ cùng nguyên liệu và cùng thứ nguyên (g + kg, ml + l)."""
    ing_id = uuid4()
    items = [
        ShoppingItem(
            ingredient_id=ing_id,
            ingredient_name="Thịt ba chỉ",
            needed_quantity=Decimal("300"),
            unit=QuantityUnit.GRAM,
            dish_names=["Thịt kho"],
            price=Decimal("45000"),
        ),
        ShoppingItem(
            ingredient_id=ing_id,
            ingredient_name="Thịt ba chỉ",
            needed_quantity=Decimal("0.5"),
            unit=QuantityUnit.KILOGRAM,
            dish_names=["Thịt luộc"],
            price=Decimal("75000"),
        ),
    ]

    merged = merge_compatible_shopping_items(items)
    assert len(merged) == 1
    # 300g + 0.5kg (500g) = 800g
    assert merged[0].needed_quantity == Decimal("800")
    assert merged[0].unit == QuantityUnit.GRAM
    assert "Thịt kho" in merged[0].dish_names
    assert "Thịt luộc" in merged[0].dish_names
    assert merged[0].price == Decimal("120000")
