"""Inventory and stock movement operations for EasyMeals."""

from datetime import datetime
from decimal import Decimal
from typing import NamedTuple
from uuid import UUID, uuid4

from app.domain.models import (
    IncompatibleUnitError,
    PantryLot,
    QuantityUnit,
    Recipe,
    StockMovement,
    StockMovementReason,
    convert_quantity,
)


class InsufficientStockError(Exception):
    def __init__(self, message: str, deficits: dict[UUID, tuple[str, Decimal, QuantityUnit]]):
        super().__init__(message)
        self.deficits = deficits


class StockDeductionResult(NamedTuple):
    updated_lots: list[PantryLot]
    movements: list[StockMovement]


def get_total_ingredient_stock(
    pantry_lots: list[PantryLot],
    ingredient_id: UUID,
    target_unit: QuantityUnit,
) -> Decimal:
    """Calculate total available stock of an ingredient converted to target_unit."""
    total = Decimal("0")
    for lot in pantry_lots:
        if lot.ingredient_id == ingredient_id and lot.remaining_quantity > Decimal("0"):
            converted = convert_quantity(lot.remaining_quantity, lot.unit, target_unit)
            total += converted
    return total


def check_recipe_stock(
    recipe: Recipe,
    pantry_lots: list[PantryLot],
    multiplier: Decimal = Decimal("1"),
) -> tuple[bool, dict[UUID, tuple[str, Decimal, QuantityUnit]]]:
    """Check if available pantry lots can satisfy the recipe requirements.

    Returns:
        (can_cook, deficits_dict)
        deficits_dict maps ingredient_id -> (ingredient_name, missing_quantity, unit)
    """
    deficits: dict[UUID, tuple[str, Decimal, QuantityUnit]] = {}

    for req in recipe.ingredients:
        required_qty = req.quantity * multiplier
        try:
            available = get_total_ingredient_stock(pantry_lots, req.ingredient_id, req.unit)
        except IncompatibleUnitError:
            deficits[req.ingredient_id] = (req.ingredient_name, required_qty, req.unit)
            continue

        if available < required_qty:
            missing = required_qty - available
            deficits[req.ingredient_id] = (req.ingredient_name, missing, req.unit)

    return len(deficits) == 0, deficits


def deduct_recipe_stock_fifo(
    pantry_lots: list[PantryLot],
    recipe: Recipe,
    meal_plan_id: UUID,
    idempotency_key: str,
    user_id: UUID | None = None,
    multiplier: Decimal = Decimal("1"),
) -> StockDeductionResult:
    """Deduct recipe requirements from pantry lots using FIFO order.

    Idempotent and atomic in domain state.
    Raises InsufficientStockError if pantry doesn't have enough quantities.
    """
    can_cook, deficits = check_recipe_stock(recipe, pantry_lots, multiplier)
    if not can_cook:
        raise InsufficientStockError(
            f"Không đủ nguyên liệu để nấu món '{recipe.name}'",
            deficits=deficits,
        )

    # Sort lots by earliest expiration (None sorted last) then earliest purchase
    def lot_sort_key(lot: PantryLot):
        exp = lot.expires_at.isoformat() if lot.expires_at else "9999-12-31"
        return (exp, lot.purchased_at)

    candidate_lots = [
        lot
        for lot in pantry_lots
        if any(req.ingredient_id == lot.ingredient_id for req in recipe.ingredients)
    ]
    candidate_lots.sort(key=lot_sort_key)

    updated_lots: list[PantryLot] = []
    movements: list[StockMovement] = []

    for req in recipe.ingredients:
        remaining_needed = req.quantity * multiplier
        ingredient_lots = [
            lot
            for lot in candidate_lots
            if lot.ingredient_id == req.ingredient_id and lot.remaining_quantity > 0
        ]

        for lot in ingredient_lots:
            if remaining_needed <= Decimal("0"):
                break

            # Convert lot's available quantity to recipe's required unit
            lot_available_in_req_unit = convert_quantity(lot.remaining_quantity, lot.unit, req.unit)

            if lot_available_in_req_unit <= remaining_needed:
                # Deduct all remaining from this lot
                deducted_req_unit = lot_available_in_req_unit
                deducted_lot_unit = lot.remaining_quantity
                lot.remaining_quantity = Decimal("0")
                remaining_needed -= deducted_req_unit
            else:
                # Deduct partial from this lot
                deducted_req_unit = remaining_needed
                deducted_lot_unit = convert_quantity(deducted_req_unit, req.unit, lot.unit)
                lot.remaining_quantity -= deducted_lot_unit
                remaining_needed = Decimal("0")

            updated_lots.append(lot)
            movements.append(
                StockMovement(
                    id=uuid4(),
                    user_id=user_id,
                    pantry_lot_id=lot.id,
                    quantity_delta=-deducted_lot_unit,
                    reason=StockMovementReason.MEAL_CONSUMPTION,
                    meal_plan_id=meal_plan_id,
                    idempotency_key=f"{idempotency_key}_{lot.id}",
                    created_at=datetime.now(),
                )
            )

    return StockDeductionResult(updated_lots=updated_lots, movements=movements)


def reverse_stock_movements(
    pantry_lots: list[PantryLot],
    movements: list[StockMovement],
    meal_plan_id: UUID,
    user_id: UUID | None = None,
) -> tuple[list[PantryLot], list[StockMovement]]:
    """Reverses stock consumption movements for a meal plan (undo consumption)."""
    lot_map = {lot.id: lot for lot in pantry_lots}
    restored_lots: list[PantryLot] = []
    reversal_movements: list[StockMovement] = []

    for mov in movements:
        if mov.meal_plan_id == meal_plan_id and mov.quantity_delta < Decimal("0"):
            lot = lot_map.get(mov.pantry_lot_id)
            if lot:
                # Add back the deducted quantity
                reversal_delta = abs(mov.quantity_delta)
                lot.remaining_quantity = min(
                    lot.purchased_quantity, lot.remaining_quantity + reversal_delta
                )
                restored_lots.append(lot)

                reversal_movements.append(
                    StockMovement(
                        id=uuid4(),
                        user_id=user_id,
                        pantry_lot_id=lot.id,
                        quantity_delta=reversal_delta,
                        reason=StockMovementReason.CORRECTION,
                        meal_plan_id=meal_plan_id,
                        idempotency_key=f"reversal_{mov.id}",
                        created_at=datetime.now(),
                    )
                )

    return restored_lots, reversal_movements
