"""Stateless Computational Endpoints for meal planning, dish deduction, and undo."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_repo
from app.domain.inventory import (
    InsufficientStockError,
    deduct_recipe_stock_available,
    deduct_recipe_stock_fifo,
    reverse_stock_movements,
)
from app.domain.models import (
    HouseholdSettings,
    IncompatibleUnitError,
    MealPlan,
    PantryLot,
    PlannedDish,
    StockMovement,
)
from app.domain.planner import (
    MealAlreadyEatenError,
    add_dish_to_meal,
    calculate_shopping_budget,
    generate_period_plan,
    merge_compatible_shopping_items,
    recompute_shopping_list,
    regenerate_single_meal,
    remove_dish_from_meal,
    reschedule_meal,
    swap_dish_in_meal,
)
from app.schemas import (
    MealPlanInput,
    MealPlanResponse,
    PantryLotInput,
    PlannedDishResponse,
    ShoppingItemResponse,
    StatelessAddDishRequest,
    StatelessEatRequest,
    StatelessEatResponse,
    StatelessGeneratePlanRequest,
    StatelessGeneratePlanResponse,
    StatelessMergeShoppingRequest,
    StatelessRecomputeShoppingRequest,
    StatelessRecomputeShoppingResponse,
    StatelessRegenerateMealRequest,
    StatelessRegenerateMealResponse,
    StatelessRemoveDishRequest,
    StatelessRescheduleMealRequest,
    StatelessSwapDishRequest,
    StatelessUndoEatRequest,
    StatelessUndoEatResponse,
    StockMovementResponse,
)
from app.storage.repository import Repository

router = APIRouter(prefix="/api/planner", tags=["Stateless Planner"])


def _to_domain_lot(inp: PantryLotInput) -> PantryLot:
    return PantryLot(
        id=inp.id,
        ingredient_id=inp.ingredient_id,
        ingredient_name=inp.ingredient_name,
        purchased_quantity=inp.purchased_quantity,
        remaining_quantity=inp.remaining_quantity,
        unit=inp.unit,
        purchased_at=inp.purchased_at,
        expires_at=inp.expires_at,
    )


def _to_lot_input(lot: PantryLot) -> PantryLotInput:
    return PantryLotInput(
        id=lot.id,
        ingredient_id=lot.ingredient_id,
        ingredient_name=lot.ingredient_name,
        purchased_quantity=lot.purchased_quantity,
        remaining_quantity=lot.remaining_quantity,
        unit=lot.unit,
        purchased_at=lot.purchased_at,
        expires_at=lot.expires_at,
    )


@router.post("/generate", response_model=StatelessGeneratePlanResponse)
def generate_stateless_plan(
    payload: StatelessGeneratePlanRequest,
    repo: Repository = Depends(get_repo),
) -> StatelessGeneratePlanResponse:
    """Generate a meal plan and shopping list purely from client-provided state.

    No data is written to disk or database.
    """
    domain_lots = [_to_domain_lot(lot) for lot in payload.pantry]
    end_date = payload.start_date + timedelta(days=payload.days - 1)
    recipes = repo.get_recipes()

    # A7 - Vòng 13: mọi đường chạy lập thực đơn phải nhận quy đổi đơn vị/nguyên liệu
    # (gạo -> cơm) kèm tên nguyên liệu gốc để danh sách mua nêu đúng "Gạo" thay vì
    # "Nguyên liệu gốc cho Cơm".
    conversions = repo.get_conversions()
    raw_ingredient_names = {ing.id: ing.name for ing in repo.get_ingredients()}

    # C1 - Vòng 13: chuyển đổi cài đặt hộ gia đình từ client sang domain model.
    household_settings: HouseholdSettings | None = None
    if payload.options.household_settings is not None:
        hs = payload.options.household_settings
        household_settings = HouseholdSettings(
            household_size=hs.household_size,
            default_servings=hs.default_servings,
            meal_periods=hs.meal_periods,
            skip_dates=hs.skip_dates,
            plan_days=hs.plan_days,
        )

    try:
        generation = generate_period_plan(
            start_date=payload.start_date,
            end_date=end_date,
            recipes=recipes,
            current_pantry_lots=domain_lots,
            allow_leftovers=payload.options.allow_leftovers,
            leftover_days=payload.options.leftover_days,
            conversions=conversions,
            raw_ingredient_names=raw_ingredient_names,
            household_settings=household_settings,
            recently_cooked_recipe_ids=set(payload.options.recently_cooked_recipe_ids),
            avoided_ingredient_ids=set(payload.options.avoided_ingredient_ids),
        )
        meal_plans, shopping_items = generation
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    period_id = (
        meal_plans[0].period_id if meal_plans and meal_plans[0].period_id else meal_plans[0].id
    )

    meals_resp = [
        MealPlanResponse(
            id=p.id,
            planned_for=p.planned_for,
            meal_period=p.meal_period,
            period_id=p.period_id,
            eaten_at=p.eaten_at,
            notes=p.notes,
            warnings=p.warnings,
            dishes=[
                PlannedDishResponse(
                    id=d.id,
                    meal_plan_id=d.meal_plan_id,
                    recipe_id=d.recipe_id,
                    recipe_name=d.recipe_name,
                    category=d.category,
                    is_leftover=d.is_leftover,
                    servings=d.servings,
                    selection_reason=d.selection_reason,
                )
                for d in p.dishes
            ],
        )
        for p in meal_plans
    ]

    shopping_resp = [
        ShoppingItemResponse(
            ingredient_id=si.ingredient_id,
            ingredient_name=si.ingredient_name,
            needed_quantity=si.needed_quantity,
            unit=si.unit,
            dish_names=si.dish_names,
        )
        for si in shopping_items
    ]

    return StatelessGeneratePlanResponse(
        period_id=period_id,
        start_date=payload.start_date,
        end_date=end_date,
        meals=meals_resp,
        shopping_list=shopping_resp,
        warnings=generation.warnings,
        excluded_recipe_count=generation.excluded_recipe_count,
    )


@router.post("/eat", response_model=StatelessEatResponse)
def eat_stateless_meal(
    payload: StatelessEatRequest,
    repo: Repository = Depends(get_repo),
) -> StatelessEatResponse:
    """Calculate FIFO stock deductions for dishes in a meal plan purely in memory.

    No state is saved on the server.
    """
    lots_map = {lot.id: _to_domain_lot(lot) for lot in payload.pantry}
    current_lots = list(lots_map.values())
    accumulated_movements: list[StockMovement] = []

    for dish in payload.dishes:
        if dish.is_leftover:
            continue

        recipe = repo.get_recipe_by_id(dish.recipe_id)
        if not recipe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy công thức món ăn (ID: {dish.recipe_id})",
            )

        multiplier = (
            Decimal(1)
            if dish.servings is None
            else Decimal(str(dish.servings)) / Decimal(str(recipe.servings))
        )

        try:
            conversions = repo.get_conversions()
            if payload.allow_partial:
                deduction, _ = deduct_recipe_stock_available(
                    pantry_lots=current_lots,
                    recipe=recipe,
                    meal_plan_id=payload.meal_plan_id,
                    idempotency_key=payload.idempotency_key,
                    multiplier=multiplier,
                    conversions=conversions,
                )
            else:
                deduction = deduct_recipe_stock_fifo(
                    pantry_lots=current_lots,
                    recipe=recipe,
                    meal_plan_id=payload.meal_plan_id,
                    idempotency_key=payload.idempotency_key,
                    multiplier=multiplier,
                    conversions=conversions,
                )
            # Update lot state in current_lots for next dish
            for updated_lot in deduction.updated_lots:
                lots_map[updated_lot.id] = updated_lot
            current_lots = list(lots_map.values())
            accumulated_movements.extend(deduction.movements)
        except InsufficientStockError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": str(e),
                    "deficits": {
                        str(ing_id): {
                            "name": name,
                            "missing": str(qty),
                            "unit": unit.value,
                        }
                        for ing_id, (name, qty, unit) in e.deficits.items()
                    },
                },
            )
        except IncompatibleUnitError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            )

    movements_resp = [
        StockMovementResponse(
            id=m.id,
            pantry_lot_id=m.pantry_lot_id,
            quantity_delta=m.quantity_delta,
            reason=m.reason,
            meal_plan_id=m.meal_plan_id,
            idempotency_key=m.idempotency_key,
            created_at=m.created_at,
        )
        for m in accumulated_movements
    ]

    updated_pantry_resp = [_to_lot_input(lot) for lot in current_lots]

    return StatelessEatResponse(
        success=True,
        pantry=updated_pantry_resp,
        movements=movements_resp,
    )


@router.post("/undo-eat", response_model=StatelessUndoEatResponse)
def undo_eat_stateless_meal(
    payload: StatelessUndoEatRequest,
) -> StatelessUndoEatResponse:
    """Calculate reversal of stock movements purely in memory."""
    domain_lots = [_to_domain_lot(lot) for lot in payload.pantry]
    domain_movements = [
        StockMovement(
            id=m.id,
            pantry_lot_id=m.pantry_lot_id,
            quantity_delta=m.quantity_delta,
            reason=m.reason,
            meal_plan_id=m.meal_plan_id,
            idempotency_key=m.idempotency_key,
            created_at=m.created_at,
        )
        for m in payload.movements
    ]

    restored_lots, reversal_movements = reverse_stock_movements(
        pantry_lots=domain_lots,
        movements=domain_movements,
        meal_plan_id=payload.meal_plan_id,
    )

    restored_map = {lot.id: lot for lot in restored_lots}
    final_lots = [restored_map.get(lot.id, lot) for lot in domain_lots]

    return StatelessUndoEatResponse(
        success=True,
        pantry=[_to_lot_input(lot) for lot in final_lots],
        reversal_movements=[
            StockMovementResponse(
                id=rm.id,
                pantry_lot_id=rm.pantry_lot_id,
                quantity_delta=rm.quantity_delta,
                reason=rm.reason,
                meal_plan_id=rm.meal_plan_id,
                idempotency_key=rm.idempotency_key,
                created_at=rm.created_at,
            )
            for rm in reversal_movements
        ],
    )


def _to_domain_meal_plan(inp: MealPlanInput) -> MealPlan:
    return MealPlan(
        id=inp.id,
        planned_for=inp.planned_for,
        meal_period=inp.meal_period,
        period_id=inp.period_id,
        eaten_at=inp.eaten_at,
        notes=inp.notes,
        warnings=inp.warnings,
        dishes=[
            PlannedDish(
                id=d.id,
                meal_plan_id=d.meal_plan_id,
                recipe_id=d.recipe_id,
                recipe_name=d.recipe_name,
                category=d.category,
                is_leftover=d.is_leftover,
                original_dish_id=d.original_dish_id,
                servings=d.servings,
            )
            for d in inp.dishes
        ],
    )


@router.post("/regenerate-meal", response_model=StatelessRegenerateMealResponse)
def regenerate_stateless_meal(
    payload: StatelessRegenerateMealRequest,
    repo: Repository = Depends(get_repo),
) -> StatelessRegenerateMealResponse:
    """Sinh lại 1 bữa đơn lẻ trong đợt kế hoạch (B1 & B2)."""
    domain_lots = [_to_domain_lot(lot) for lot in payload.pantry]
    domain_plans = [_to_domain_meal_plan(p) for p in payload.all_meal_plans]
    recipes = repo.get_recipes()
    conversions = repo.get_conversions()
    raw_ingredient_names = {ing.id: ing.name for ing in repo.get_ingredients()}

    try:
        updated_meal = regenerate_single_meal(
            target_meal_plan_id=payload.target_meal_plan_id,
            all_meal_plans=domain_plans,
            recipes=recipes,
            current_pantry_lots=domain_lots,
            allow_leftovers=payload.options.allow_leftovers,
            conversions=conversions,
            raw_ingredient_names=raw_ingredient_names,
            leftover_days=payload.options.leftover_days,
            avoided_ingredient_ids=set(payload.options.avoided_ingredient_ids),
        )
    except MealAlreadyEatenError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    return StatelessRegenerateMealResponse(
        success=True,
        excluded_recipe_count=sum(
            any(
                ingredient.ingredient_id in set(payload.options.avoided_ingredient_ids)
                for ingredient in recipe.ingredients
            )
            for recipe in recipes
        ),
        meal=MealPlanResponse(
            id=updated_meal.id,
            planned_for=updated_meal.planned_for,
            meal_period=updated_meal.meal_period,
            period_id=updated_meal.period_id,
            eaten_at=updated_meal.eaten_at,
            notes=updated_meal.notes,
            warnings=updated_meal.warnings,
            dishes=[
                PlannedDishResponse(
                    id=d.id,
                    meal_plan_id=d.meal_plan_id,
                    recipe_id=d.recipe_id,
                    recipe_name=d.recipe_name,
                    category=d.category,
                    is_leftover=d.is_leftover,
                    servings=d.servings,
                    selection_reason=d.selection_reason,
                )
                for d in updated_meal.dishes
            ],
        ),
    )


@router.post("/recompute-shopping", response_model=StatelessRecomputeShoppingResponse)
def recompute_stateless_shopping(
    payload: StatelessRecomputeShoppingRequest,
    repo: Repository = Depends(get_repo),
) -> StatelessRecomputeShoppingResponse:
    """Tính lại danh sách mua từ các bữa chưa ăn (B1 & B3 & B4)."""
    domain_lots = [_to_domain_lot(lot) for lot in payload.pantry]
    domain_plans = [_to_domain_meal_plan(p) for p in payload.meal_plans]
    recipes = repo.get_recipes()
    conversions = repo.get_conversions()
    ingredients = repo.get_ingredients()
    raw_ingredient_names = {ing.id: ing.name for ing in ingredients}
    ingredient_categories = {ing.id: ing.category or "khac" for ing in ingredients}

    items = recompute_shopping_list(
        meal_plans=domain_plans,
        current_pantry_lots=domain_lots,
        recipes=recipes,
        conversions=conversions,
        raw_ingredient_names=raw_ingredient_names,
        ingredient_categories=ingredient_categories,
    )

    budget = calculate_shopping_budget(items)

    return StatelessRecomputeShoppingResponse(
        shopping_list=[
            ShoppingItemResponse(
                id=item.id,
                ingredient_id=item.ingredient_id,
                ingredient_name=item.ingredient_name,
                needed_quantity=item.needed_quantity,
                unit=item.unit,
                dish_names=item.dish_names,
                category=item.category,
                price=item.price,
                is_bought=item.is_bought,
                bought_quantity=item.bought_quantity,
                source=item.source,
            )
            for item in items
        ],
        total_estimated_budget=budget["total_estimated_budget"],
        total_spent=budget["total_spent"],
        items_with_price_count=budget["items_with_price_count"],
        total_items_count=budget["total_items_count"],
    )


def _to_plan_response(plan: MealPlan) -> MealPlanResponse:
    return MealPlanResponse(
        id=plan.id,
        planned_for=plan.planned_for,
        meal_period=plan.meal_period,
        period_id=plan.period_id,
        eaten_at=plan.eaten_at,
        notes=plan.notes,
        dishes=[
            PlannedDishResponse(
                id=d.id,
                meal_plan_id=d.meal_plan_id,
                recipe_id=d.recipe_id,
                recipe_name=d.recipe_name,
                category=d.category,
                is_leftover=d.is_leftover,
                servings=d.servings,
            )
            for d in plan.dishes
        ],
    )


@router.post("/swap-dish", response_model=MealPlanResponse)
def swap_dish(
    payload: StatelessSwapDishRequest,
    repo: Repository = Depends(get_repo),
) -> MealPlanResponse:
    """Đổi 1 món cụ thể trong bữa (B1 & B2)."""
    meal_plan = _to_domain_meal_plan(payload.meal_plan)
    new_recipe = repo.get_recipe_by_id(payload.new_recipe_id)
    if not new_recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy công thức món ăn (ID: {payload.new_recipe_id})",
        )
    all_plans = [_to_domain_meal_plan(p) for p in payload.all_plans_in_period]
    try:
        updated = swap_dish_in_meal(meal_plan, payload.old_dish_id, new_recipe, all_plans)
    except MealAlreadyEatenError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    return _to_plan_response(updated)


@router.post("/add-dish", response_model=MealPlanResponse)
def add_dish(
    payload: StatelessAddDishRequest,
    repo: Repository = Depends(get_repo),
) -> MealPlanResponse:
    """Thêm 1 món vào bữa ăn (B1 & B2)."""
    meal_plan = _to_domain_meal_plan(payload.meal_plan)
    recipe = repo.get_recipe_by_id(payload.recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy công thức món ăn (ID: {payload.recipe_id})",
        )
    try:
        updated = add_dish_to_meal(meal_plan, recipe, payload.servings)
    except MealAlreadyEatenError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    return _to_plan_response(updated)


@router.post("/remove-dish", response_model=MealPlanResponse)
def remove_dish(
    payload: StatelessRemoveDishRequest,
) -> MealPlanResponse:
    """Bỏ 1 món khỏi bữa ăn (B1 & B2)."""
    meal_plan = _to_domain_meal_plan(payload.meal_plan)
    try:
        updated = remove_dish_from_meal(meal_plan, payload.dish_id)
    except MealAlreadyEatenError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    return _to_plan_response(updated)


@router.post("/reschedule-meal", response_model=MealPlanResponse)
def reschedule(
    payload: StatelessRescheduleMealRequest,
) -> MealPlanResponse:
    """Chuyển ngày/bữa của một bữa ăn (B1 & B2)."""
    meal_plan = _to_domain_meal_plan(payload.meal_plan)
    all_plans = [_to_domain_meal_plan(p) for p in payload.all_meal_plans]
    try:
        updated = reschedule_meal(meal_plan, payload.new_date, payload.new_period, all_plans)
    except MealAlreadyEatenError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    return _to_plan_response(updated)


@router.post("/merge-shopping", response_model=list[ShoppingItemResponse])
def merge_shopping(
    payload: StatelessMergeShoppingRequest,
) -> list[ShoppingItemResponse]:
    """Gộp các món đi chợ cùng nguyên liệu và cùng thứ nguyên (B3)."""
    from app.domain.models import ShoppingItem

    domain_items = [
        ShoppingItem(
            id=it.id or UUID("00000000-0000-0000-0000-000000000000"),
            ingredient_id=it.ingredient_id,
            ingredient_name=it.ingredient_name,
            needed_quantity=it.needed_quantity,
            unit=it.unit,
            is_bought=it.is_bought,
            dish_names=it.dish_names,
            category=it.category,
            price=it.price,
            bought_quantity=it.bought_quantity,
            source=it.source,
        )
        for it in payload.items
    ]
    merged = merge_compatible_shopping_items(domain_items)
    return [
        ShoppingItemResponse(
            id=item.id,
            ingredient_id=item.ingredient_id,
            ingredient_name=item.ingredient_name,
            needed_quantity=item.needed_quantity,
            unit=item.unit,
            dish_names=item.dish_names,
            category=item.category,
            price=item.price,
            is_bought=item.is_bought,
            bought_quantity=item.bought_quantity,
            source=item.source,
        )
        for item in merged
    ]
