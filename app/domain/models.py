"""Domain models and unit conversion rules for EasyMeals."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4


class QuantityUnit(StrEnum):
    GRAM = "g"
    KILOGRAM = "kg"
    MILLILITER = "ml"
    LITER = "l"
    PIECE = "piece"


class DishCategory(StrEnum):
    MAN = "man"
    RAU = "rau"
    CANH = "canh"


class MealPeriod(StrEnum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"


class StockMovementReason(StrEnum):
    PURCHASE = "purchase"
    MEAL_CONSUMPTION = "meal_consumption"
    CORRECTION = "correction"
    LEFTOVER_CONSUMED = "leftover_consumed"


UNIT_DIMENSIONS: dict[QuantityUnit, str] = {
    QuantityUnit.GRAM: "mass",
    QuantityUnit.KILOGRAM: "mass",
    QuantityUnit.MILLILITER: "volume",
    QuantityUnit.LITER: "volume",
    QuantityUnit.PIECE: "count",
}

# Conversion multiplier to canonical base unit (g for mass, ml for volume, piece for count)
UNIT_BASE_MULTIPLIER: dict[QuantityUnit, Decimal] = {
    QuantityUnit.GRAM: Decimal("1"),
    QuantityUnit.KILOGRAM: Decimal("1000"),
    QuantityUnit.MILLILITER: Decimal("1"),
    QuantityUnit.LITER: Decimal("1000"),
    QuantityUnit.PIECE: Decimal("1"),
}


class IncompatibleUnitError(ValueError):
    """Raised when attempting to convert between incompatible unit dimensions."""

    pass


def convert_quantity(
    quantity: Decimal,
    from_unit: QuantityUnit | str,
    to_unit: QuantityUnit | str,
) -> Decimal:
    """Safely convert quantity between compatible units.

    Supports:
      - g <-> kg
      - ml <-> l
      - piece <-> piece
    Raises IncompatibleUnitError if converting across different dimensions.
    """
    from_u = QuantityUnit(from_unit)
    to_u = QuantityUnit(to_unit)

    if from_u == to_u:
        return quantity

    dim_from = UNIT_DIMENSIONS[from_u]
    dim_to = UNIT_DIMENSIONS[to_u]

    if dim_from != dim_to:
        raise IncompatibleUnitError(
            f"Không thể chuyển đổi đơn vị '{from_u.value}' ({dim_from}) "
            f"sang '{to_u.value}' ({dim_to}) vì khác thứ nguyên."
        )

    # Convert to base, then to target unit
    base_qty = quantity * UNIT_BASE_MULTIPLIER[from_u]
    target_qty = base_qty / UNIT_BASE_MULTIPLIER[to_u]
    return target_qty


@dataclass
class IngredientCategory:
    id: str
    name: str
    display_order: int = 0


@dataclass
class IngredientConversion:
    from_ingredient_id: UUID
    to_ingredient_id: UUID
    ratio: Decimal
    from_unit: QuantityUnit = QuantityUnit.GRAM
    to_unit: QuantityUnit = QuantityUnit.GRAM
    note: str | None = None


@dataclass
class Ingredient:
    id: UUID
    name: str
    normalized_name: str
    category: str | None = "khac"
    default_unit: QuantityUnit = QuantityUnit.GRAM
    aliases: list[str] = field(default_factory=list)
    allergens: list[str] = field(default_factory=list)
    allergen_verification_status: str = "unknown"
    allergen_source_url: str | None = None
    allergen_verified_at: date | None = None


@dataclass
class RecipeIngredient:
    recipe_id: UUID
    ingredient_id: UUID
    ingredient_name: str
    quantity: Decimal
    unit: QuantityUnit


@dataclass
class Recipe:
    id: UUID
    name: str
    category: DishCategory
    instructions: list[str]
    servings: int
    ingredients: list[RecipeIngredient] = field(default_factory=list)
    dietary_status: str = "unknown"
    dietary_source_url: str | None = None
    dietary_verified_at: date | None = None
    spice_level: int | None = None
    spice_source_url: str | None = None
    spice_verified_at: date | None = None


@dataclass
class PantryLot:
    id: UUID
    ingredient_id: UUID
    ingredient_name: str
    purchased_quantity: Decimal
    remaining_quantity: Decimal
    unit: QuantityUnit
    purchased_at: datetime
    expires_at: date | None = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class PlannedDish:
    id: UUID
    meal_plan_id: UUID
    recipe_id: UUID
    recipe_name: str
    category: DishCategory
    is_leftover: bool = False
    original_dish_id: UUID | None = None
    servings: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    selection_reason: str | None = None


@dataclass
class HouseholdSettings:
    """Cài đặt hộ gia đình cục bộ (không lưu lên server).

    plan_days mặc định 3 khớp với design-tokens/tokens.json (plan_limits.default_days)
    và app.constants.PLAN_DEFAULT_DAYS; giá trị này được đồng bộ khi khởi tạo
    từ caller thay vì import hằng số để tránh circular import (constants import models).
    """

    household_size: int = 1
    default_servings: int = 2
    # Bữa cần lập trong mỗi ngày: mặc định trưa + tối.
    meal_periods: list[str] = field(default_factory=lambda: ["lunch", "dinner"])
    # Ngày không nấu / ăn ngoài (ISO "YYYY-MM-DD"): bỏ qua khi lập kế hoạch.
    skip_dates: list[str] = field(default_factory=list)
    plan_days: int = 3


@dataclass
class MealPlan:
    id: UUID
    planned_for: date
    meal_period: MealPeriod
    period_id: UUID | None = None
    eaten_at: datetime | None = None
    notes: str | None = None
    dishes: list[PlannedDish] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class StockMovement:
    id: UUID
    pantry_lot_id: UUID
    quantity_delta: Decimal
    reason: StockMovementReason
    meal_plan_id: UUID | None = None
    idempotency_key: str | None = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ShoppingItem:
    ingredient_id: UUID
    ingredient_name: str
    needed_quantity: Decimal
    unit: QuantityUnit
    dish_names: list[str] = field(default_factory=list)
    category: str | None = "khac"
    price: Decimal | None = None
    is_bought: bool = False
    bought_quantity: Decimal | None = None
    source: str = "plan"
    id: UUID = field(default_factory=uuid4)
