"""Stateless Computational Endpoints for meal planning, dish deduction, and undo."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_repo
from app.domain.inventory import (
    InsufficientStockError,
    deduct_recipe_stock_fifo,
    reverse_stock_movements,
)
from app.domain.models import (
    IncompatibleUnitError,
    PantryLot,
    StockMovement,
)
from app.domain.planner import generate_period_plan
from app.schemas import (
    MealPlanResponse,
    PantryLotInput,
    PlannedDishResponse,
    ShoppingItemResponse,
    StatelessEatRequest,
    StatelessEatResponse,
    StatelessGeneratePlanRequest,
    StatelessGeneratePlanResponse,
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

    try:
        meal_plans, shopping_items = generate_period_plan(
            start_date=payload.start_date,
            end_date=end_date,
            recipes=recipes,
            current_pantry_lots=domain_lots,
            allow_leftovers=payload.options.allow_leftovers,
        )
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

        multiplier = Decimal(str(dish.servings)) / Decimal(str(recipe.servings))

        try:
            deduction = deduct_recipe_stock_fifo(
                pantry_lots=current_lots,
                recipe=recipe,
                meal_plan_id=payload.meal_plan_id,
                idempotency_key=payload.idempotency_key,
                multiplier=multiplier,
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
