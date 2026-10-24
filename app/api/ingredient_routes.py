"""Endpoints for canonical ingredients and search/autocomplete."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_repo
from app.schemas import IngredientResponse
from app.storage.repository import Repository

router = APIRouter(prefix="/api/ingredients", tags=["Ingredients"])


@router.get("", response_model=list[IngredientResponse])
def list_ingredients(
    q: str | None = Query(default=None, max_length=100),
    repo: Repository = Depends(get_repo),
) -> list[IngredientResponse]:
    """Search ingredients with autocomplete support across names and aliases."""
    ings = repo.get_ingredients(search=q)
    return [
        IngredientResponse(
            id=i.id,
            name=i.name,
            normalized_name=i.normalized_name,
            category=i.category,
            aliases=i.aliases,
        )
        for i in ings
    ]


@router.get("/{ingredient_id}", response_model=IngredientResponse)
def get_ingredient(
    ingredient_id: UUID,
    repo: Repository = Depends(get_repo),
) -> IngredientResponse:
    ing = repo.get_ingredient_by_id(ingredient_id)
    if not ing:
        raise HTTPException(status_code=404, detail="Không tìm thấy nguyên liệu.")
    return IngredientResponse(
        id=ing.id,
        name=ing.name,
        normalized_name=ing.normalized_name,
        category=ing.category,
        aliases=ing.aliases,
    )
