"""Inventory and stock movement operations for EasyMeals."""

from datetime import datetime
from decimal import Decimal
from typing import NamedTuple
from uuid import UUID, uuid4

from app.domain.models import (
    UNIT_DIMENSIONS,
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


class Requirement(NamedTuple):
    ingredient_id: UUID
    name: str
    quantity: Decimal
    unit: QuantityUnit


def units_compatible(a: QuantityUnit | str, b: QuantityUnit | str) -> bool:
    """True nếu hai đơn vị cùng thứ nguyên (khối lượng, thể tích, đếm)."""
    return UNIT_DIMENSIONS[QuantityUnit(a)] == UNIT_DIMENSIONS[QuantityUnit(b)]


def aggregate_requirements(recipe: Recipe, multiplier: Decimal = Decimal("1")) -> list[Requirement]:
    """Gộp các dòng nguyên liệu trùng nhau (cùng nguyên liệu, cùng thứ nguyên) của công thức."""
    merged: dict[tuple[UUID, str], Requirement] = {}
    for req in recipe.ingredients:
        qty = req.quantity * multiplier
        key = (req.ingredient_id, UNIT_DIMENSIONS[req.unit])
        if key in merged:
            prev = merged[key]
            merged[key] = prev._replace(
                quantity=prev.quantity + convert_quantity(qty, req.unit, prev.unit)
            )
        else:
            merged[key] = Requirement(req.ingredient_id, req.ingredient_name, qty, req.unit)
    return list(merged.values())


def _lot_sort_key(lot: PantryLot):
    exp = lot.expires_at.isoformat() if lot.expires_at else "9999-12-31"
    return (exp, lot.purchased_at)


def get_total_ingredient_stock(
    pantry_lots: list[PantryLot],
    ingredient_id: UUID,
    target_unit: QuantityUnit,
) -> Decimal:
    """Tổng tồn kho của nguyên liệu quy về target_unit.

    Lô có đơn vị khác thứ nguyên (ví dụ lô tính bằng cái trong khi công thức dùng g) bị bỏ
    qua thay vì làm hỏng cả phép tính: chúng không thể quy đổi nên không được tính là đủ hàng.
    """
    total = Decimal("0")
    for lot in pantry_lots:
        if (
            lot.ingredient_id == ingredient_id
            and lot.remaining_quantity > Decimal("0")
            and units_compatible(lot.unit, target_unit)
        ):
            total += convert_quantity(lot.remaining_quantity, lot.unit, target_unit)
    return total


def consume_available(
    pantry_lots: list[PantryLot],
    ingredient_id: UUID,
    quantity: Decimal,
    unit: QuantityUnit,
) -> Decimal:
    """Trừ tối đa `quantity` (theo FIFO, có quy đổi đơn vị) khỏi các lô; trả về lượng đã trừ.

    Dùng cho mô phỏng khi lập thực đơn: sửa trực tiếp `remaining_quantity` của các lô truyền vào.
    """
    needed = quantity
    consumed = Decimal("0")
    for lot in sorted(pantry_lots, key=_lot_sort_key):
        if needed <= 0:
            break
        if (
            lot.ingredient_id != ingredient_id
            or lot.remaining_quantity <= 0
            or not units_compatible(lot.unit, unit)
        ):
            continue
        available = convert_quantity(lot.remaining_quantity, lot.unit, unit)
        take = min(available, needed)
        lot.remaining_quantity -= convert_quantity(take, unit, lot.unit)
        needed -= take
        consumed += take
    return consumed


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

    for req in aggregate_requirements(recipe, multiplier):
        available = get_total_ingredient_stock(pantry_lots, req.ingredient_id, req.unit)
        if available < req.quantity:
            deficits[req.ingredient_id] = (req.name, req.quantity - available, req.unit)

    return len(deficits) == 0, deficits


def deduct_recipe_stock_fifo(
    pantry_lots: list[PantryLot],
    recipe: Recipe,
    meal_plan_id: UUID,
    idempotency_key: str,
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
    requirements = aggregate_requirements(recipe, multiplier)
    required_ids = {req.ingredient_id for req in requirements}
    candidate_lots = [lot for lot in pantry_lots if lot.ingredient_id in required_ids]
    candidate_lots.sort(key=_lot_sort_key)

    updated_lots: list[PantryLot] = []
    movements: list[StockMovement] = []

    for req in requirements:
        remaining_needed = req.quantity
        ingredient_lots = [
            lot
            for lot in candidate_lots
            if lot.ingredient_id == req.ingredient_id
            and lot.remaining_quantity > 0
            and units_compatible(lot.unit, req.unit)
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
) -> tuple[list[PantryLot], list[StockMovement]]:
    """Reverses stock consumption movements for a meal plan (undo consumption)."""
    lot_map = {lot.id: lot for lot in pantry_lots}
    restored_lots: list[PantryLot] = []
    reversal_movements: list[StockMovement] = []

    # Bỏ qua các biến động đã được hoàn tác (có biến động `reversal_<id>`), để hoàn tác lặp
    # lại không cộng kho thêm lần nữa.
    already_reversed = {
        m.idempotency_key.removeprefix("reversal_")
        for m in movements
        if m.idempotency_key and m.idempotency_key.startswith("reversal_")
    }

    for mov in movements:
        if (
            mov.meal_plan_id == meal_plan_id
            and mov.quantity_delta < Decimal("0")
            and mov.reason == StockMovementReason.MEAL_CONSUMPTION
            and str(mov.id) not in already_reversed
        ):
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
                        pantry_lot_id=lot.id,
                        quantity_delta=reversal_delta,
                        reason=StockMovementReason.CORRECTION,
                        meal_plan_id=meal_plan_id,
                        idempotency_key=f"reversal_{mov.id}",
                        created_at=datetime.now(),
                    )
                )

    return restored_lots, reversal_movements
