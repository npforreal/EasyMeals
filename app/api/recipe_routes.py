"""Endpoints for recipes catalogue and cooking details."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_repo
from app.domain.models import DishCategory
from app.schemas import RecipeIngredientResponse, RecipeResponse
from app.storage.repository import Repository

router = APIRouter(prefix="/api/recipes", tags=["Recipes"])


@router.get("", response_model=list[RecipeResponse])
def list_recipes(
    category: DishCategory | None = Query(None, description="Lọc theo nhóm món: man, rau, canh"),
    repo: Repository = Depends(get_repo),
) -> list[RecipeResponse]:
    recipes = repo.get_recipes(category=category)
    return [
        RecipeResponse(
            id=r.id,
            name=r.name,
            category=r.category,
            instructions=r.instructions,
            servings=r.servings,
            ingredients=[
                RecipeIngredientResponse(
                    ingredient_id=ri.ingredient_id,
                    ingredient_name=ri.ingredient_name,
                    quantity=ri.quantity,
                    unit=ri.unit,
                )
                for ri in r.ingredients
            ],
            dietary_status=r.dietary_status,
            dietary_source_url=r.dietary_source_url,
            dietary_verified_at=r.dietary_verified_at,
            spice_level=r.spice_level,
            spice_source_url=r.spice_source_url,
            spice_verified_at=r.spice_verified_at,
            prep_time_minutes=r.prep_time_minutes,
            prep_time_source_url=r.prep_time_source_url,
            prep_time_verified_at=r.prep_time_verified_at,
            cook_time_minutes=r.cook_time_minutes,
            cook_time_source_url=r.cook_time_source_url,
            cook_time_verified_at=r.cook_time_verified_at,
            difficulty=r.difficulty,
            difficulty_source_url=r.difficulty_source_url,
            difficulty_verified_at=r.difficulty_verified_at,
            storage_tips=r.storage_tips,
            storage_source_url=r.storage_source_url,
            storage_verified_at=r.storage_verified_at,
        )
        for r in recipes
    ]


@router.get("/{recipe_id}", response_model=RecipeResponse)
def get_recipe(
    recipe_id: UUID,
    repo: Repository = Depends(get_repo),
) -> RecipeResponse:
    r = repo.get_recipe_by_id(recipe_id)
    if not r:
        raise HTTPException(status_code=404, detail="Không tìm thấy công thức món ăn.")
    return RecipeResponse(
        id=r.id,
        name=r.name,
        category=r.category,
        instructions=r.instructions,
        servings=r.servings,
        ingredients=[
            RecipeIngredientResponse(
                ingredient_id=ri.ingredient_id,
                ingredient_name=ri.ingredient_name,
                quantity=ri.quantity,
                unit=ri.unit,
            )
            for ri in r.ingredients
        ],
        dietary_status=r.dietary_status,
        dietary_source_url=r.dietary_source_url,
        dietary_verified_at=r.dietary_verified_at,
        spice_level=r.spice_level,
        spice_source_url=r.spice_source_url,
        spice_verified_at=r.spice_verified_at,
        prep_time_minutes=r.prep_time_minutes,
        prep_time_source_url=r.prep_time_source_url,
        prep_time_verified_at=r.prep_time_verified_at,
        cook_time_minutes=r.cook_time_minutes,
        cook_time_source_url=r.cook_time_source_url,
        cook_time_verified_at=r.cook_time_verified_at,
        difficulty=r.difficulty,
        difficulty_source_url=r.difficulty_source_url,
        difficulty_verified_at=r.difficulty_verified_at,
        storage_tips=r.storage_tips,
        storage_source_url=r.storage_source_url,
        storage_verified_at=r.storage_verified_at,
    )
