"""Pydantic schemas for EasyMeals stateless API endpoints."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

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


class PlanOptions(BaseModel):
    model_config = {"extra": "forbid"}

    allow_leftovers: bool = True


class StatelessGeneratePlanRequest(BaseModel):
    model_config = {"extra": "forbid"}

    pantry: list[PantryLotInput] = Field(
        default_factory=list,
        max_length=500,
        description="Danh sách thực phẩm trong kho (tối đa 500 lots)",
    )
    start_date: date
    days: int = Field(
        default=7,
        ge=1,
        le=31,
        description="Số ngày lập thực đơn (từ 1 đến 31 ngày)",
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
    ingredient_id: UUID
    ingredient_name: str
    needed_quantity: Decimal
    unit: QuantityUnit
    dish_names: list[str] = Field(default_factory=list)


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
