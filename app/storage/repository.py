"""Repository interface and implementations for EasyMeals shared catalogue.

In the new architecture:
- Personal data (pantry, plans, stock movements) is stored exclusively on the client (IndexedDB).
- This repository is strictly READ-ONLY and manages shared culinary catalogue data:
  ingredients, aliases, recipes, and recipe ingredients.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
import uuid
from abc import ABC, abstractmethod
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from app.domain.models import DishCategory, Ingredient, QuantityUnit, Recipe, RecipeIngredient

ROOT = Path(__file__).resolve().parents[2]

CATALOGUE_VERSION = "2026.10.26"
SUPABASE_PAGE_SIZE = 1000

NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # DNS namespace UUID


def normalize_text(text: str) -> str:
    """Normalize Vietnamese text for matching (lowercase, no diacritics, single spaces)."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    without_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    cleaned = without_marks.replace("đ", "d").replace("Đ", "d")
    return " ".join(cleaned.split())


def _sanitize_postgrest_search(search: str) -> str:
    """Strip PostgREST filter control characters to prevent filter injection."""
    return re.sub(r'[,().:*%_\\"]', "", search).strip()


class Repository(ABC):
    """Abstract base class for read-only catalogue access."""

    @abstractmethod
    def get_ingredients(self, search: str | None = None) -> list[Ingredient]:
        """List ingredients, optionally filtered by keyword."""
        pass

    @abstractmethod
    def get_ingredient_by_id(self, ingredient_id: UUID) -> Ingredient | None:
        """Get an ingredient by its ID."""
        pass

    @abstractmethod
    def get_recipes(self, category: DishCategory | None = None) -> list[Recipe]:
        """List recipes, optionally filtered by dish category."""
        pass

    @abstractmethod
    def get_recipe_by_id(self, recipe_id: UUID) -> Recipe | None:
        """Get a recipe by its ID with full ingredients."""
        pass

    @abstractmethod
    def get_catalogue_bundle(self) -> dict[str, Any]:
        """Get complete catalogue bundle for offline syncing with client IndexedDB."""
        pass


class FixtureCatalogueRepository(Repository):
    """In-memory catalogue repository using canonical Vietnamese culinary seed data.

    Used for offline testing, CI, and local dev without live database connections.
    """

    def __init__(self) -> None:
        self.ingredients: dict[UUID, Ingredient] = {}
        self.recipes: dict[UUID, Recipe] = {}
        self._ingredients = self.ingredients
        self._recipes = self.recipes
        self._seed_starter_data()

    def _seed_starter_data(self) -> None:
        raw_ingredients = [
            (
                "11111111-0001-0000-0000-000000000001",
                "Thịt ba chỉ",
                "thit ba chi",
                "meat",
                ["Thịt rọi"],
            ),
            (
                "11111111-0001-0000-0000-000000000002",
                "Thịt heo nạc dăm",
                "thit heo nac dam",
                "meat",
                ["Thịt băm", "Thịt xay"],
            ),
            ("11111111-0001-0000-0000-000000000003", "Sườn non heo", "suon non heo", "meat", []),
            ("11111111-0001-0000-0000-000000000004", "Thịt bò thăn", "thit bo than", "meat", []),
            ("11111111-0001-0000-0000-000000000005", "Thịt gà", "thit ga", "poultry", []),
            ("11111111-0001-0000-0000-000000000006", "Cá lóc", "ca loc", "seafood", []),
            ("11111111-0001-0000-0000-000000000007", "Tôm sú", "tom su", "seafood", []),
            ("11111111-0001-0000-0000-000000000008", "Trứng gà", "trung ga", "egg", []),
            ("11111111-0001-0000-0000-000000000009", "Trứng vịt", "trung vit", "egg", []),
            (
                "11111111-0001-0000-0000-000000000010",
                "Đậu hũ trắng",
                "dau hu trang",
                "tofu",
                ["Tàu hũ"],
            ),
            ("11111111-0001-0000-0000-000000000011", "Rau muống", "rau muong", "vegetable", []),
            ("11111111-0001-0000-0000-000000000012", "Cải ngọt", "cai ngot", "vegetable", []),
            (
                "11111111-0001-0000-0000-000000000013",
                "Rau mồng tơi",
                "rau mong toi",
                "vegetable",
                [],
            ),
            ("11111111-0001-0000-0000-000000000014", "Bắp cải", "bap cai", "vegetable", []),
            ("11111111-0001-0000-0000-000000000015", "Cà chua", "ca chua", "vegetable", []),
            ("11111111-0001-0000-0000-000000000016", "Dưa leo", "dua leo", "vegetable", []),
            ("11111111-0001-0000-0000-000000000017", "Bí đỏ", "bi do", "vegetable", []),
            ("11111111-0001-0000-0000-000000000018", "Khoai tây", "khoai tay", "root", []),
            ("11111111-0001-0000-0000-000000000019", "Cà rốt", "ca rot", "root", []),
            ("11111111-0001-0000-0000-000000000020", "Đậu cô ve", "dau co ve", "vegetable", []),
            (
                "11111111-0001-0000-0000-000000000021",
                "Thơm (Dứa)",
                "thom dua",
                "fruit_vegetable",
                ["Dứa", "Khóm"],
            ),
            ("11111111-0001-0000-0000-000000000022", "Đậu bắp", "dau bap", "vegetable", []),
            ("11111111-0001-0000-0000-000000000023", "Giá đỗ", "gia do", "vegetable", []),
            ("11111111-0001-0000-0000-000000000024", "Nấm rơm", "nam rom", "mushroom", []),
            ("11111111-0001-0000-0000-000000000025", "Tỏi", "toi", "spice", []),
            ("11111111-0001-0000-0000-000000000026", "Hành tím", "hanh tim", "spice", []),
            ("11111111-0001-0000-0000-000000000027", "Hành lá", "hanh la", "herb", []),
            ("11111111-0001-0000-0000-000000000028", "Gừng", "gung", "spice", []),
            ("11111111-0001-0000-0000-000000000029", "Cần tây", "can tay", "vegetable", []),
        ]
        for ing_id, name, norm, cat, aliases in raw_ingredients:
            uid = UUID(ing_id)
            self.ingredients[uid] = Ingredient(
                id=uid,
                name=name,
                normalized_name=norm,
                category=cat,
                aliases=aliases,
            )

        raw_recipes = [
            (
                "22222222-0001-0000-0000-000000000001",
                "Thịt kho tàu",
                DishCategory.MAN,
                4,
                [
                    "Ướp thịt ba chỉ với hành tím băm, nước mắm, tiêu trong 20 phút.",
                    "Luộc trứng vịt chín rồi bóc vỏ.",
                    "Thắng nước màu caramen, trút thịt vào đảo săn đều.",
                    "Thêm nước vào nồi ngập thịt, kho riu riu.",
                    "Cho trứng vịt vào kho cùng đến khi thịt mềm rục.",
                ],
                [
                    (
                        "11111111-0001-0000-0000-000000000001",
                        "Thịt ba chỉ",
                        Decimal("500"),
                        QuantityUnit.GRAM,
                    ),
                    (
                        "11111111-0001-0000-0000-000000000009",
                        "Trứng vịt",
                        Decimal("4"),
                        QuantityUnit.PIECE,
                    ),
                    (
                        "11111111-0001-0000-0000-000000000026",
                        "Hành tím",
                        Decimal("20"),
                        QuantityUnit.GRAM,
                    ),
                ],
            ),
            (
                "22222222-0001-0000-0000-000000000002",
                "Sườn xào chua ngọt",
                DishCategory.MAN,
                4,
                [
                    "Sườn non chặt miếng vừa ăn, chần qua nước sôi rồi để ráo.",
                    "Chiên sườn vàng đều 2 mặt trên chảo dầu nóng.",
                    "Pha sốt chua ngọt từ nước mắm, giấm gạo, đường và tương cà chua.",
                    "Phi thơm tỏi, cho sườn và sốt đảo đều đến khi ngấm vị.",
                ],
                [
                    (
                        "11111111-0001-0000-0000-000000000003",
                        "Sườn non heo",
                        Decimal("500"),
                        QuantityUnit.GRAM,
                    ),
                    (
                        "11111111-0001-0000-0000-000000000025",
                        "Tỏi",
                        Decimal("15"),
                        QuantityUnit.GRAM,
                    ),
                    (
                        "11111111-0001-0000-0000-000000000015",
                        "Cà chua",
                        Decimal("100"),
                        QuantityUnit.GRAM,
                    ),
                ],
            ),
            (
                "22222222-0002-0000-0000-000000000001",
                "Rau muống xào tỏi",
                DishCategory.RAU,
                4,
                [
                    "Rau muống nhặt sạch, chần nhanh qua nước sôi.",
                    "Phi thơm tỏi đập dập với dầu ăn trên chảo lửa lớn.",
                    "Cho rau muống vào đảo nhanh tay, nêm gia vị vừa ăn rồi tắt bếp.",
                ],
                [
                    (
                        "11111111-0001-0000-0000-000000000011",
                        "Rau muống",
                        Decimal("400"),
                        QuantityUnit.GRAM,
                    ),
                    (
                        "11111111-0001-0000-0000-000000000025",
                        "Tỏi",
                        Decimal("25"),
                        QuantityUnit.GRAM,
                    ),
                ],
            ),
            (
                "22222222-0003-0000-0000-000000000001",
                "Canh chua cá lóc",
                DishCategory.CANH,
                4,
                [
                    "Cá lóc cắt khúc, cà chua bổ múi cau, thơm thái lát, đậu bắp cắt xéo.",
                    "Phi thơm tỏi, cho cà chua và thơm vào xào lấy màu.",
                    "Thêm nước sôi, thả cá lóc vào đun chín ngọt nước.",
                    "Cho đậu bắp, giá đỗ vào nấu sôi lại, nêm nếm gia vị và rau ngò.",
                ],
                [
                    (
                        "11111111-0001-0000-0000-000000000006",
                        "Cá lóc",
                        Decimal("400"),
                        QuantityUnit.GRAM,
                    ),
                    (
                        "11111111-0001-0000-0000-000000000015",
                        "Cà chua",
                        Decimal("150"),
                        QuantityUnit.GRAM,
                    ),
                    (
                        "11111111-0001-0000-0000-000000000021",
                        "Thơm (Dứa)",
                        Decimal("150"),
                        QuantityUnit.GRAM,
                    ),
                    (
                        "11111111-0001-0000-0000-000000000022",
                        "Đậu bắp",
                        Decimal("100"),
                        QuantityUnit.GRAM,
                    ),
                    (
                        "11111111-0001-0000-0000-000000000023",
                        "Giá đỗ",
                        Decimal("100"),
                        QuantityUnit.GRAM,
                    ),
                ],
            ),
        ]
        for rec_id, name, cat, servings, instructions, ing_list in raw_recipes:
            uid = UUID(rec_id)
            ingredients = [
                RecipeIngredient(
                    recipe_id=uid,
                    ingredient_id=UUID(ing_id),
                    ingredient_name=ing_name,
                    quantity=qty,
                    unit=unit,
                )
                for ing_id, ing_name, qty, unit in ing_list
            ]
            self.recipes[uid] = Recipe(
                id=uid,
                name=name,
                category=cat,
                servings=servings,
                instructions=instructions,
                ingredients=ingredients,
            )

        self._load_expanded_datasets()

    def _load_expanded_datasets(self) -> None:
        """Load enriched Vietnamese family dishes and curated international dishes if available."""
        import uuid
        from pathlib import Path

        namespace = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
        data_dir = Path(__file__).resolve().parents[2] / "data" / "open"
        files = [
            data_dir / "vietnamese_recipes.jsonl",
            data_dir / "international_recipes_vi.jsonl",
        ]

        ing_by_norm: dict[str, Ingredient] = {}
        for ing in self.ingredients.values():
            ing_by_norm[ing.normalized_name] = ing
            ing_by_norm[normalize_text(ing.name)] = ing
            for a in ing.aliases:
                ing_by_norm[normalize_text(a)] = ing

        for fpath in files:
            if not fpath.exists():
                continue
            with open(fpath, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    seed_key = f"rec:{row.get('source_id') or row['name']}"
                    rec_id = uuid.uuid5(namespace, seed_key)
                    if rec_id in self.recipes:
                        continue

                    cat_val = row.get("dish_category")
                    try:
                        cat = DishCategory(cat_val)
                    except (ValueError, TypeError):
                        continue

                    recipe_ings: list[RecipeIngredient] = []
                    for ing_dict in row.get("ingredients", []):
                        ing_name = ing_dict.get("name", "").strip()
                        if not ing_name:
                            continue
                        ing_norm = (
                            ing_dict.get("normalized_name") or ""
                        ).strip() or normalize_text(ing_name)
                        if ing_norm in ing_by_norm:
                            ing_obj = ing_by_norm[ing_norm]
                        elif normalize_text(ing_name) in ing_by_norm:
                            ing_obj = ing_by_norm[normalize_text(ing_name)]
                        else:
                            ing_id = uuid.uuid5(namespace, f"ing:{ing_norm}")
                            ing_obj = Ingredient(
                                id=ing_id,
                                name=ing_name,
                                normalized_name=ing_norm,
                                category=ing_dict.get("category", "vegetable"),
                                aliases=ing_dict.get("aliases", []),
                            )
                            self.ingredients[ing_id] = ing_obj
                            ing_by_norm[ing_norm] = ing_obj
                            ing_by_norm[normalize_text(ing_name)] = ing_obj

                        try:
                            qty = Decimal(str(ing_dict.get("quantity") or "100"))
                            unit = QuantityUnit(ing_dict.get("unit") or "g")
                        except Exception:
                            continue
                        if qty <= 0:
                            continue

                        recipe_ings.append(
                            RecipeIngredient(
                                recipe_id=rec_id,
                                ingredient_id=ing_obj.id,
                                ingredient_name=ing_obj.name,
                                quantity=qty,
                                unit=unit,
                            )
                        )

                    # Hop nhat nguyen lieu bi lap trong cung mot cong thuc
                    merged_ings: dict[UUID, RecipeIngredient] = {}
                    for ri in recipe_ings:
                        if ri.ingredient_id not in merged_ings:
                            merged_ings[ri.ingredient_id] = ri
                        else:
                            curr = merged_ings[ri.ingredient_id]
                            if curr.unit == ri.unit:
                                curr.quantity += ri.quantity
                            elif curr.unit == QuantityUnit.PIECE and ri.unit == QuantityUnit.GRAM:
                                merged_ings[ri.ingredient_id] = ri
                    recipe_ings = list(merged_ings.values())

                    if recipe_ings:
                        self.recipes[rec_id] = Recipe(
                            id=rec_id,
                            name=row["name"],
                            category=cat,
                            servings=int(row.get("servings") or 4),
                            instructions=row.get("instructions", []),
                            ingredients=recipe_ings,
                        )

    def get_ingredients(self, search: str | None = None) -> list[Ingredient]:
        if not search:
            return list(self.ingredients.values())
        norm_query = normalize_text(search)
        results = []
        for ing in self.ingredients.values():
            if norm_query in ing.normalized_name:
                results.append(ing)
            elif any(norm_query in normalize_text(a) for a in ing.aliases):
                results.append(ing)
        return results

    def get_ingredient_by_id(self, ingredient_id: UUID) -> Ingredient | None:
        return self.ingredients.get(ingredient_id)

    def get_recipes(self, category: DishCategory | None = None) -> list[Recipe]:
        recipes = list(self.recipes.values())
        if category:
            return [r for r in recipes if r.category == category]
        return recipes

    def get_recipe_by_id(self, recipe_id: UUID) -> Recipe | None:
        return self.recipes.get(recipe_id)

    def get_catalogue_bundle(self) -> dict[str, Any]:
        ingredients_data = [
            {
                "id": str(i.id),
                "name": i.name,
                "normalized_name": i.normalized_name,
                "category": i.category,
                "aliases": i.aliases,
            }
            for i in self.ingredients.values()
        ]
        recipes_data = [
            {
                "id": str(r.id),
                "name": r.name,
                "category": r.category.value,
                "servings": r.servings,
                "instructions": r.instructions,
                "ingredients": [
                    {
                        "ingredient_id": str(ri.ingredient_id),
                        "ingredient_name": ri.ingredient_name,
                        "quantity": str(ri.quantity),
                        "unit": ri.unit.value,
                    }
                    for ri in r.ingredients
                ],
            }
            for r in self.recipes.values()
        ]
        bundle = {
            "catalogue_version": CATALOGUE_VERSION,
            "ingredients": ingredients_data,
            "recipes": recipes_data,
        }
        raw_json = json.dumps(bundle, sort_keys=True).encode("utf-8")
        bundle_hash = hashlib.sha256(raw_json).hexdigest()[:16]
        bundle["etag"] = f'"{CATALOGUE_VERSION}-{bundle_hash}"'
        return bundle


class SupabaseRepository(Repository):
    """Read-only Supabase catalogue repository using public anon key."""

    def __init__(self, supabase_url: str, anon_key: str) -> None:
        from supabase import create_client

        self.client = create_client(supabase_url, anon_key)

    @staticmethod
    def _fetch_all(query: Any) -> list[dict[str, Any]]:
        """Đọc toàn bộ kết quả theo trang, vì PostgREST cắt mặc định ở 1.000 dòng/truy vấn."""
        rows: list[dict[str, Any]] = []
        start = 0
        while True:
            page = query.range(start, start + SUPABASE_PAGE_SIZE - 1).execute().data or []
            rows.extend(page)
            if len(page) < SUPABASE_PAGE_SIZE:
                return rows
            start += SUPABASE_PAGE_SIZE

    def get_ingredients(self, search: str | None = None) -> list[Ingredient]:
        query = self.client.table("ingredients").select(
            "id, name, normalized_name, category, ingredient_aliases(alias)"
        )
        if search:
            # PostgREST filter injection protection: remove control characters
            clean_search = _sanitize_postgrest_search(search)
            if clean_search:
                norm_q = normalize_text(clean_search)
                query = query.ilike("normalized_name", f"%{norm_q}%")

        data = self._fetch_all(query.order("name").order("id"))
        results: list[Ingredient] = []
        for row in data:
            aliases = [a["alias"] for a in row.get("ingredient_aliases", [])]
            results.append(
                Ingredient(
                    id=UUID(row["id"]),
                    name=row["name"],
                    normalized_name=row["normalized_name"],
                    category=row.get("category"),
                    aliases=aliases,
                )
            )
        return results

    def get_ingredient_by_id(self, ingredient_id: UUID) -> Ingredient | None:
        response = (
            self.client.table("ingredients")
            .select("id, name, normalized_name, category, ingredient_aliases(alias)")
            .eq("id", str(ingredient_id))
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        row = response.data[0]
        aliases = [a["alias"] for a in row.get("ingredient_aliases", [])]
        return Ingredient(
            id=UUID(row["id"]),
            name=row["name"],
            normalized_name=row["normalized_name"],
            category=row.get("category"),
            aliases=aliases,
        )

    def get_recipes(self, category: DishCategory | None = None) -> list[Recipe]:
        query = self.client.table("recipes").select(
            "id, name, category, servings, instructions, "
            "recipe_ingredients(ingredient_id, quantity, unit, ingredients(name))"
        )
        if category:
            query = query.eq("category", category.value)
        data = self._fetch_all(query.order("name").order("id"))

        recipes: list[Recipe] = []
        for row in data:
            recipe_id = UUID(row["id"])
            ingredients: list[RecipeIngredient] = []
            for ri in row.get("recipe_ingredients", []):
                ing_data = ri.get("ingredients") or {}
                ing_name = ing_data.get("name") or "Nguyên liệu"
                ingredients.append(
                    RecipeIngredient(
                        recipe_id=recipe_id,
                        ingredient_id=UUID(ri["ingredient_id"]),
                        ingredient_name=ing_name,
                        quantity=Decimal(str(ri["quantity"])),
                        unit=QuantityUnit(ri["unit"]),
                    )
                )
            recipes.append(
                Recipe(
                    id=recipe_id,
                    name=row["name"],
                    category=DishCategory(row["category"]),
                    instructions=row.get("instructions") or [],
                    servings=row.get("servings", 1),
                    ingredients=ingredients,
                )
            )
        return recipes

    def get_recipe_by_id(self, recipe_id: UUID) -> Recipe | None:
        response = (
            self.client.table("recipes")
            .select(
                "id, name, category, servings, instructions, "
                "recipe_ingredients(ingredient_id, quantity, unit, ingredients(name))"
            )
            .eq("id", str(recipe_id))
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        row = response.data[0]
        uid = UUID(row["id"])
        ingredients: list[RecipeIngredient] = []
        for ri in row.get("recipe_ingredients", []):
            ing_data = ri.get("ingredients") or {}
            ing_name = ing_data.get("name") or "Nguyên liệu"
            ingredients.append(
                RecipeIngredient(
                    recipe_id=uid,
                    ingredient_id=UUID(ri["ingredient_id"]),
                    ingredient_name=ing_name,
                    quantity=Decimal(str(ri["quantity"])),
                    unit=QuantityUnit(ri["unit"]),
                )
            )
        return Recipe(
            id=uid,
            name=row["name"],
            category=DishCategory(row["category"]),
            instructions=row.get("instructions") or [],
            servings=row.get("servings", 1),
            ingredients=ingredients,
        )

    def get_catalogue_bundle(self) -> dict[str, Any]:
        ingredients = self.get_ingredients()
        recipes = self.get_recipes()

        ingredients_data = [
            {
                "id": str(i.id),
                "name": i.name,
                "normalized_name": i.normalized_name,
                "category": i.category,
                "aliases": i.aliases,
            }
            for i in ingredients
        ]
        recipes_data = [
            {
                "id": str(r.id),
                "name": r.name,
                "category": r.category.value,
                "servings": r.servings,
                "instructions": r.instructions,
                "ingredients": [
                    {
                        "ingredient_id": str(ri.ingredient_id),
                        "ingredient_name": ri.ingredient_name,
                        "quantity": str(ri.quantity),
                        "unit": ri.unit.value,
                    }
                    for ri in r.ingredients
                ],
            }
            for r in recipes
        ]
        bundle = {
            "catalogue_version": CATALOGUE_VERSION,
            "ingredients": ingredients_data,
            "recipes": recipes_data,
        }
        raw_json = json.dumps(bundle, sort_keys=True).encode("utf-8")
        bundle_hash = hashlib.sha256(raw_json).hexdigest()[:16]
        bundle["etag"] = f'"{CATALOGUE_VERSION}-{bundle_hash}"'
        return bundle


_default_repository: Repository | None = None


def get_repository() -> Repository:
    """Dependency provider returning singleton catalogue repository.

    Strict security rule: In production, Supabase MUST be configured with anon key.
    Falling back silently to in-memory fixtures is forbidden in production.
    """
    global _default_repository
    if _default_repository is not None:
        return _default_repository

    is_prod = (
        bool(os.environ.get("VERCEL_ENV"))
        or bool(os.environ.get("VERCEL"))
        or os.environ.get("APP_ENV", "").lower() not in ("development", "dev", "test")
    )

    # Hard security rule: refuse service_role key in runtime environment
    if os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY được phát hiện trong runtime environment. "
            "Khoá service_role bị cấm tuyệt đối trên server web để bảo vệ an toàn."
        )

    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    anon_key = (
        os.environ.get("SUPABASE_ANON_KEY")
        or os.environ.get("SUPABASE_PUBLISHABLE_KEY")
        or os.environ.get("SUPABASE_KEY")
        or ""
    ).strip()

    if supabase_url and anon_key and not supabase_url.startswith("https://your-"):
        _default_repository = SupabaseRepository(supabase_url, anon_key)
        return _default_repository

    if is_prod:
        raise RuntimeError("Supabase URL hoặc ANON key chưa được cấu hình ở môi trường production.")

    _default_repository = FixtureCatalogueRepository()
    return _default_repository


InMemoryRepository = FixtureCatalogueRepository
