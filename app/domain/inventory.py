"""Inventory and stock movement operations for EasyMeals."""

from datetime import datetime
from decimal import Decimal
from typing import NamedTuple
from uuid import UUID, uuid4

from app.domain.models import (
    UNIT_DIMENSIONS,
    IngredientConversion,
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


def _find_conversions_for_target(
    ingredient_id: UUID,
    conversions: list[IngredientConversion] | None,
) -> list[IngredientConversion]:
    if not conversions:
        return []
    return [
        c for c in conversions if c.to_ingredient_id == ingredient_id and c.ratio > Decimal("0")
    ]


def get_total_ingredient_stock(
    pantry_lots: list[PantryLot],
    ingredient_id: UUID,
    target_unit: QuantityUnit,
    conversions: list[IngredientConversion] | None = None,
) -> Decimal:
    """Tổng tồn kho của nguyên liệu quy về target_unit (kèm quy đổi nếu có)."""
    total = Decimal("0")
    for lot in pantry_lots:
        if (
            lot.ingredient_id == ingredient_id
            and lot.remaining_quantity > Decimal("0")
            and units_compatible(lot.unit, target_unit)
        ):
            total += convert_quantity(lot.remaining_quantity, lot.unit, target_unit)

    # Thêm tồn kho quy đổi từ nguyên liệu gốc (ví dụ Gạo -> Cơm)
    target_convs = _find_conversions_for_target(ingredient_id, conversions)
    for conv in target_convs:
        if not units_compatible(conv.to_unit, target_unit):
            continue
        for lot in pantry_lots:
            if (
                lot.ingredient_id == conv.from_ingredient_id
                and lot.remaining_quantity > Decimal("0")
                and units_compatible(lot.unit, conv.from_unit)
            ):
                raw_in_from_unit = convert_quantity(
                    lot.remaining_quantity, lot.unit, conv.from_unit
                )
                prod_in_to_unit = raw_in_from_unit * conv.ratio
                total += convert_quantity(prod_in_to_unit, conv.to_unit, target_unit)

    return total


def consume_available(
    pantry_lots: list[PantryLot],
    ingredient_id: UUID,
    quantity: Decimal,
    unit: QuantityUnit,
    conversions: list[IngredientConversion] | None = None,
) -> Decimal:
    """Trừ tối đa `quantity` (theo FIFO, có quy đổi đơn vị và nguyên liệu) khỏi các lô;
    trả về lượng đã trừ.
    """
    needed = quantity
    consumed = Decimal("0")
    # 1. Trừ lô trực tiếp trước
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

    # 2. Nếu còn thiếu, trừ lô gốc qua bảng quy đổi (FIFO)
    if needed > 0:
        target_convs = _find_conversions_for_target(ingredient_id, conversions)
        for conv in target_convs:
            if needed <= 0:
                break
            if not units_compatible(conv.to_unit, unit):
                continue
            for lot in sorted(pantry_lots, key=_lot_sort_key):
                if needed <= 0:
                    break
                if (
                    lot.ingredient_id != conv.from_ingredient_id
                    or lot.remaining_quantity <= 0
                    or not units_compatible(lot.unit, conv.from_unit)
                ):
                    continue
                needed_in_to_unit = convert_quantity(needed, unit, conv.to_unit)
                needed_raw = needed_in_to_unit / conv.ratio
                raw_available = convert_quantity(lot.remaining_quantity, lot.unit, conv.from_unit)
                take_raw = min(raw_available, needed_raw)
                lot.remaining_quantity -= convert_quantity(take_raw, conv.from_unit, lot.unit)
                yielded_in_to_unit = take_raw * conv.ratio
                yielded_unit = convert_quantity(yielded_in_to_unit, conv.to_unit, unit)
                needed -= yielded_unit
                consumed += yielded_unit

    return consumed


def check_recipe_stock(
    recipe: Recipe,
    pantry_lots: list[PantryLot],
    multiplier: Decimal = Decimal("1"),
    conversions: list[IngredientConversion] | None = None,
) -> tuple[bool, dict[UUID, tuple[str, Decimal, QuantityUnit]]]:
    """Check if available pantry lots can satisfy the recipe requirements."""
    deficits: dict[UUID, tuple[str, Decimal, QuantityUnit]] = {}

    for req in aggregate_requirements(recipe, multiplier):
        available = get_total_ingredient_stock(
            pantry_lots, req.ingredient_id, req.unit, conversions=conversions
        )
        if available < req.quantity:
            deficits[req.ingredient_id] = (req.name, req.quantity - available, req.unit)

    return len(deficits) == 0, deficits


def _execute_stock_deduction(
    pantry_lots: list[PantryLot],
    recipe: Recipe,
    meal_plan_id: UUID,
    idempotency_key: str,
    multiplier: Decimal = Decimal("1"),
    conversions: list[IngredientConversion] | None = None,
    allow_partial: bool = False,
) -> tuple[StockDeductionResult, dict[UUID, tuple[str, Decimal, QuantityUnit]]]:
    requirements = aggregate_requirements(recipe, multiplier)
    updated_lots: list[PantryLot] = []
    movements: list[StockMovement] = []
    deficits: dict[UUID, tuple[str, Decimal, QuantityUnit]] = {}

    if not allow_partial:
        can_cook, deficits_check = check_recipe_stock(
            recipe, pantry_lots, multiplier, conversions=conversions
        )
        if not can_cook:
            raise InsufficientStockError(
                f"Không đủ nguyên liệu để nấu món '{recipe.name}'",
                deficits=deficits_check,
            )

    for req in requirements:
        remaining_needed = req.quantity

        # 1. Trừ các lô trực tiếp của nguyên liệu theo FIFO
        direct_lots = [
            lot
            for lot in pantry_lots
            if lot.ingredient_id == req.ingredient_id
            and lot.remaining_quantity > 0
            and units_compatible(lot.unit, req.unit)
        ]
        direct_lots.sort(key=_lot_sort_key)

        for lot in direct_lots:
            if remaining_needed <= Decimal("0"):
                break
            lot_available_in_req_unit = convert_quantity(lot.remaining_quantity, lot.unit, req.unit)
            if lot_available_in_req_unit <= remaining_needed:
                deducted_req_unit = lot_available_in_req_unit
                deducted_lot_unit = lot.remaining_quantity
                lot.remaining_quantity = Decimal("0")
                remaining_needed -= deducted_req_unit
            else:
                deducted_req_unit = remaining_needed
                deducted_lot_unit = convert_quantity(deducted_req_unit, req.unit, lot.unit)
                lot.remaining_quantity -= deducted_lot_unit
                remaining_needed = Decimal("0")

            if lot not in updated_lots:
                updated_lots.append(lot)
            movements.append(
                StockMovement(
                    id=uuid4(),
                    pantry_lot_id=lot.id,
                    quantity_delta=-deducted_lot_unit,
                    reason=StockMovementReason.MEAL_CONSUMPTION,
                    meal_plan_id=meal_plan_id,
                    idempotency_key=f"{idempotency_key}_{lot.id}_{len(movements)}",
                    created_at=datetime.now(),
                )
            )

        # 2. Nếu còn thiếu, trừ từ nguyên liệu gốc qua bảng quy đổi (FIFO)
        if remaining_needed > Decimal("0"):
            target_convs = _find_conversions_for_target(req.ingredient_id, conversions)
            for conv in target_convs:
                if remaining_needed <= Decimal("0"):
                    break
                if not units_compatible(conv.to_unit, req.unit):
                    continue

                raw_lots = [
                    lot
                    for lot in pantry_lots
                    if lot.ingredient_id == conv.from_ingredient_id
                    and lot.remaining_quantity > 0
                    and units_compatible(lot.unit, conv.from_unit)
                ]
                raw_lots.sort(key=_lot_sort_key)

                for lot in raw_lots:
                    if remaining_needed <= Decimal("0"):
                        break
                    needed_in_to_unit = convert_quantity(remaining_needed, req.unit, conv.to_unit)
                    needed_raw_in_from_unit = needed_in_to_unit / conv.ratio
                    lot_raw_in_from_unit = convert_quantity(
                        lot.remaining_quantity, lot.unit, conv.from_unit
                    )
                    take_raw_in_from_unit = min(lot_raw_in_from_unit, needed_raw_in_from_unit)
                    take_lot_unit = convert_quantity(
                        take_raw_in_from_unit, conv.from_unit, lot.unit
                    )
                    lot.remaining_quantity -= take_lot_unit
                    yielded_in_to_unit = take_raw_in_from_unit * conv.ratio
                    yielded_req_unit = convert_quantity(yielded_in_to_unit, conv.to_unit, req.unit)
                    remaining_needed -= yielded_req_unit

                    if lot not in updated_lots:
                        updated_lots.append(lot)
                    movements.append(
                        StockMovement(
                            id=uuid4(),
                            pantry_lot_id=lot.id,
                            quantity_delta=-take_lot_unit,
                            reason=StockMovementReason.MEAL_CONSUMPTION,
                            meal_plan_id=meal_plan_id,
                            idempotency_key=f"{idempotency_key}_{lot.id}_{len(movements)}",
                            created_at=datetime.now(),
                        )
                    )

        if remaining_needed > Decimal("0"):
            deficits[req.ingredient_id] = (req.name, remaining_needed, req.unit)

    return StockDeductionResult(updated_lots=updated_lots, movements=movements), deficits


def deduct_recipe_stock_fifo(
    pantry_lots: list[PantryLot],
    recipe: Recipe,
    meal_plan_id: UUID,
    idempotency_key: str,
    multiplier: Decimal = Decimal("1"),
    conversions: list[IngredientConversion] | None = None,
) -> StockDeductionResult:
    """Deduct recipe requirements from pantry lots using FIFO order.

    Raises InsufficientStockError if pantry doesn't have enough quantities.
    """
    res, _ = _execute_stock_deduction(
        pantry_lots=pantry_lots,
        recipe=recipe,
        meal_plan_id=meal_plan_id,
        idempotency_key=idempotency_key,
        multiplier=multiplier,
        conversions=conversions,
        allow_partial=False,
    )
    return res


def deduct_recipe_stock_available(
    pantry_lots: list[PantryLot],
    recipe: Recipe,
    meal_plan_id: UUID,
    idempotency_key: str,
    multiplier: Decimal = Decimal("1"),
    conversions: list[IngredientConversion] | None = None,
) -> tuple[StockDeductionResult, dict[UUID, tuple[str, Decimal, QuantityUnit]]]:
    """Trừ kho phần có sẵn (FIFO), không ném lỗi nếu thiếu,
    trả về (kết quả trừ kho, danh sách thiếu).
    """
    return _execute_stock_deduction(
        pantry_lots=pantry_lots,
        recipe=recipe,
        meal_plan_id=meal_plan_id,
        idempotency_key=idempotency_key,
        multiplier=multiplier,
        conversions=conversions,
        allow_partial=True,
    )


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
