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
    )
