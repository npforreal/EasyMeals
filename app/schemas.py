"""Pydantic schemas for EasyMeals stateless API endpoints."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.constants import (
    LEFTOVER_DEFAULT_DAYS,
    LEFTOVER_MAX_DAYS,
    LEFTOVER_MIN_DAYS,
    PLAN_DEFAULT_DAYS,
    PLAN_MAX_DAYS,
    PLAN_MIN_DAYS,
)
from app.domain.models import DishCategory, MealPeriod, QuantityUnit, StockMovementReason


# 1. Catalogue Schemas
class IngredientResponse(BaseModel):
    id: UUID
    name: str
    normalized_name: str
    category: str | None = None
    aliases: list[str] = Field(default_factory=list)


class RecipeIngredientResponse(BaseModel):
    ingredient_id: UUID
    ingredient_name: str
    quantity: Decimal
    unit: QuantityUnit


class RecipeResponse(BaseModel):
    id: UUID
    name: str
    category: DishCategory
    instructions: list[str]
    servings: int
    ingredients: list[RecipeIngredientResponse]


class CatalogueBundleResponse(BaseModel):
    catalogue_version: str
    etag: str
    ingredients: list[IngredientResponse]
    recipes: list[RecipeResponse]


# 2. Stateless Pantry & Plan Schemas
class PantryLotInput(BaseModel):
    model_config = {"extra": "forbid"}

    id: UUID
    ingredient_id: UUID
    ingredient_name: str = Field(default="", max_length=150)
    purchased_quantity: Decimal = Field(
        gt=0, le=100000, description="Số lượng ban đầu phải > 0 và <= 100,000"
    )
    remaining_quantity: Decimal = Field(
        ge=0, le=100000, description="Số lượng còn lại phải >= 0 và <= 100,000"
    )
    unit: QuantityUnit
    purchased_at: datetime = Field(default_factory=datetime.now)
    expires_at: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class HouseholdSettingsInput(BaseModel):
    model_config = {"extra": "forbid"}

    household_size: int = Field(default=1, ge=1, le=20, description="Số người trong hộ gia đình.")
    default_servings: int = Field(
        default=2, ge=1, le=50, description="Khẩu phần mặc định cho mỗi người."
    )
    meal_periods: list[str] = Field(
        default_factory=lambda: ["lunch", "dinner"],
        description="Các bữa cần lập mỗi ngày (breakfast, lunch, dinner).",
    )
    skip_dates: list[str] = Field(
        default_factory=list,
        description="Ngày không nấu / ăn ngoài (ISO 'YYYY-MM-DD'), bỏ qua khi lập kế hoạch.",
    )
    plan_days: int = Field(
        default=3,
        ge=PLAN_MIN_DAYS,
        le=PLAN_MAX_DAYS,
        description=f"Số ngày lập thực đơn (từ {PLAN_MIN_DAYS} đến {PLAN_MAX_DAYS} ngày).",
    )


class PlanOptions(BaseModel):
    model_config = {"extra": "forbid"}

    allow_leftovers: bool = True
    # Đồ dư dùng lại tối đa 2 ngày sau ngày nấu (quyết định chủ dự án), cấu hình 1-3.
    leftover_days: int = Field(
        default=LEFTOVER_DEFAULT_DAYS, ge=LEFTOVER_MIN_DAYS, le=LEFTOVER_MAX_DAYS
    )
    household_settings: HouseholdSettingsInput | None = Field(
        default=None, description="Cài đặt hộ gia đình cục bộ (không lưu lên server)."
    )


class StatelessGeneratePlanRequest(BaseModel):
    model_config = {"extra": "forbid"}

    pantry: list[PantryLotInput] = Field(
        default_factory=list,
        max_length=500,
        description="Danh sách thực phẩm trong kho (tối đa 500 lots)",
    )
    start_date: date
    days: int = Field(
        default=PLAN_DEFAULT_DAYS,
        ge=PLAN_MIN_DAYS,
        le=PLAN_MAX_DAYS,
        description=f"Số ngày lập thực đơn (từ {PLAN_MIN_DAYS} đến {PLAN_MAX_DAYS} ngày)",
    )
    options: PlanOptions = Field(default_factory=PlanOptions)


class PlannedDishResponse(BaseModel):
    id: UUID
    meal_plan_id: UUID
    recipe_id: UUID
    recipe_name: str
    category: DishCategory
    is_leftover: bool = False
    servings: int = 1


class MealPlanResponse(BaseModel):
    id: UUID
    planned_for: date
    meal_period: MealPeriod
    period_id: UUID | None = None
    eaten_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=500)
    dishes: list[PlannedDishResponse]


class ShoppingItemResponse(BaseModel):
    id: UUID | None = None
    ingredient_id: UUID
    ingredient_name: str
    needed_quantity: Decimal
    unit: QuantityUnit
    dish_names: list[str] = Field(default_factory=list)
    category: str | None = "khac"
    price: Decimal | None = None
    is_bought: bool = False
    bought_quantity: Decimal | None = None
    source: str = "plan"


class StatelessGeneratePlanResponse(BaseModel):
    period_id: UUID
    start_date: date
    end_date: date
    meals: list[MealPlanResponse]
    shopping_list: list[ShoppingItemResponse]


# 3. Stateless Eat & Undo-Eat Schemas
class StatelessEatDishInput(BaseModel):
    model_config = {"extra": "forbid"}

    recipe_id: UUID
    is_leftover: bool = False
    # None = nấu trọn công thức (khớp với cách lập thực đơn tính nguyên liệu cho cả công thức).
    servings: int | None = Field(default=None, ge=1, le=20)


class StatelessEatRequest(BaseModel):
    model_config = {"extra": "forbid"}

    pantry: list[PantryLotInput] = Field(max_length=500, description="Danh sách kho hiện tại")
    meal_plan_id: UUID
    dishes: list[StatelessEatDishInput] = Field(
        max_length=10, description="Các món ăn trong bữa cần trừ kho"
    )
    idempotency_key: str = Field(min_length=1, max_length=128, description="Khoá chống trừ đúp")
    allow_partial: bool = Field(default=False, description="Cho phép trừ kho phần đang có dù thiếu")


class StockMovementResponse(BaseModel):
    id: UUID
    pantry_lot_id: UUID
    quantity_delta: Decimal
    reason: StockMovementReason
    meal_plan_id: UUID | None = None
    idempotency_key: str | None = None
    created_at: datetime


class StatelessEatResponse(BaseModel):
    success: bool
    pantry: list[PantryLotInput]
    movements: list[StockMovementResponse]


class StockMovementInput(BaseModel):
    model_config = {"extra": "ignore"}

    id: UUID
    pantry_lot_id: UUID
    quantity_delta: Decimal
    reason: StockMovementReason = StockMovementReason.MEAL_CONSUMPTION
    meal_plan_id: UUID | None = None
    idempotency_key: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)


class StatelessUndoEatRequest(BaseModel):
    model_config = {"extra": "forbid"}

    pantry: list[PantryLotInput] = Field(max_length=500, description="Danh sách kho hiện tại")
    meal_plan_id: UUID
    movements: list[StockMovementInput] = Field(
        max_length=100, description="Các biến động trừ kho cần đảo ngược"
    )


class StatelessUndoEatResponse(BaseModel):
    success: bool
    pantry: list[PantryLotInput]
    reversal_movements: list[StockMovementResponse]


# 4. Plan Editing & Recomputing Schemas (Round 13 Phase B)
class PlannedDishInput(BaseModel):
    id: UUID
    meal_plan_id: UUID
    recipe_id: UUID
    recipe_name: str
    category: DishCategory
    is_leftover: bool = False
    original_dish_id: UUID | None = None
    servings: int = 1


class MealPlanInput(BaseModel):
    id: UUID
    planned_for: date
    meal_period: MealPeriod
    period_id: UUID | None = None
    eaten_at: datetime | None = None
    notes: str | None = None
    dishes: list[PlannedDishInput] = Field(default_factory=list)


class StatelessRegenerateMealRequest(BaseModel):
    model_config = {"extra": "forbid"}

    target_meal_plan_id: UUID
    all_meal_plans: list[MealPlanInput] = Field(max_length=50)
    pantry: list[PantryLotInput] = Field(default_factory=list, max_length=500)
    options: PlanOptions = Field(default_factory=PlanOptions)


class StatelessRegenerateMealResponse(BaseModel):
    success: bool
    meal: MealPlanResponse


class StatelessRecomputeShoppingRequest(BaseModel):
    model_config = {"extra": "forbid"}

    meal_plans: list[MealPlanInput] = Field(max_length=50)
    pantry: list[PantryLotInput] = Field(default_factory=list, max_length=500)


class StatelessRecomputeShoppingResponse(BaseModel):
    shopping_list: list[ShoppingItemResponse]
    total_estimated_budget: Decimal
    total_spent: Decimal
    items_with_price_count: int
    total_items_count: int


class StatelessSwapDishRequest(BaseModel):
    model_config = {"extra": "forbid"}

    meal_plan: MealPlanInput
    old_dish_id: UUID
    new_recipe_id: UUID
    all_plans_in_period: list[MealPlanInput] = Field(default_factory=list, max_length=50)


class StatelessAddDishRequest(BaseModel):
    model_config = {"extra": "forbid"}

    meal_plan: MealPlanInput
    recipe_id: UUID
    servings: int | None = Field(default=None, ge=1, le=20)


class StatelessRemoveDishRequest(BaseModel):
    model_config = {"extra": "forbid"}

    meal_plan: MealPlanInput
    dish_id: UUID


class StatelessRescheduleMealRequest(BaseModel):
    model_config = {"extra": "forbid"}

    meal_plan: MealPlanInput
    new_date: date
    new_period: MealPeriod
    all_meal_plans: list[MealPlanInput] = Field(max_length=50)


class StatelessMergeShoppingRequest(BaseModel):
    model_config = {"extra": "forbid"}

    items: list[ShoppingItemResponse] = Field(max_length=200)
