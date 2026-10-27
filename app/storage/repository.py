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
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from app.domain.models import DishCategory, Ingredient, QuantityUnit, Recipe, RecipeIngredient

ROOT = Path(__file__).resolve().parents[2]

CATALOGUE_VERSION = "2026.10.28"
SUPABASE_PAGE_SIZE = 1000

NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # DNS namespace UUID

STANDARD_CATEGORIES: list[dict[str, Any]] = [
    {"id": "thit", "name": "Thịt", "name_vi": "Thịt", "display_order": 1},
    {"id": "gia_cam", "name": "Gia cầm", "name_vi": "Gia cầm", "display_order": 2},
    {"id": "hai_san", "name": "Hải sản", "name_vi": "Hải sản", "display_order": 3},
    {"id": "trung_sua", "name": "Trứng & Sữa", "name_vi": "Trứng & Sữa", "display_order": 4},
    {"id": "rau_cu", "name": "Rau củ", "name_vi": "Rau củ", "display_order": 5},
    {"id": "cu_qua", "name": "Củ quả", "name_vi": "Củ quả", "display_order": 6},
    {"id": "gao_bot_mi", "name": "Gạo, Bột & Mì", "name_vi": "Gạo, Bột & Mì", "display_order": 7},
    {"id": "gia_vi", "name": "Gia vị", "name_vi": "Gia vị", "display_order": 8},
    {
        "id": "nuoc_cham_dau",
        "name": "Nước chấm & Dầu",
        "name_vi": "Nước chấm & Dầu",
        "display_order": 9,
    },
    {"id": "khac", "name": "Khác", "name_vi": "Khác", "display_order": 10},
]

STANDARD_CONVERSIONS: list[dict[str, Any]] = [
    {
        "from_ingredient_id": "0738fdf0-710e-5aed-bbb5-5ba1f0c05f3b",
        "to_ingredient_id": "412a8c08-4863-5000-aedd-13e2ba3adb69",
        "ratio": "2.5",
        "from_unit": "g",
        "to_unit": "g",
        "note": "1g gạo nấu ra khoảng 2.5g cơm nóng chín (xấp xỉ)",
    },
    {
        "from_ingredient_id": "0738fdf0-710e-5aed-bbb5-5ba1f0c05f3b",
        "to_ingredient_id": "16ddda98-781e-5ecf-9778-aedb4d1cd9ef",
        "ratio": "2.5",
        "from_unit": "g",
        "to_unit": "g",
        "note": "1g gạo nấu ra khoảng 2.5g cơm nguội (xấp xỉ)",
    },
]


def classify_ingredient(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ["gà", "vịt", "lòng gà", "ức gà"]):
        return "gia_cam"
    if any(k in n for k in ["cá ", "tôm", "mực", "ngao", "hến", "cua", "thịt ếch", "đầu cá"]):
        return "hai_san"
    if any(
        k in n for k in ["thịt", "sườn", "lạp xưởng", "xúc xích", "tai heo", "huyết heo", "chả lụa"]
    ):
        return "thit"
    if any(k in n for k in ["trứng", "sữa", "phô mai", "bơ", "kem tươi"]):
        return "trung_sua"
    if any(
        k in n
        for k in [
            "dầu ",
            "nước mắm",
            "nước tương",
            "giấm",
            "tương cà",
            "tương ớt",
            "tương bần",
            "sốt bbq",
            "sốt mayonnaise",
            "cốt me",
        ]
    ):
        return "nuoc_cham_dau"
    if any(k in n for k in ["gạo", "cơm", "mì ", "mì ý", "miến", "bánh mì", "bánh tráng", "bột "]):
        return "gao_bot_mi"
    if any(
        k in n
        for k in [
            "tỏi",
            "hành tím",
            "hành lá",
            "gừng",
            "cần tây",
            "sả",
            "tiêu",
            "rau răm",
            "rau thơm",
            "rau om",
            "mùi tàu",
            "đường",
            "lá chanh",
            "thì là",
            "bột cà ri",
            "mật ong",
            "ớt",
            "ngò gai",
            "nghệ",
            "rau mùi",
            "rau ngò",
            "chanh",
            "quả sấu",
            "mè rang",
        ]
    ):
        return "gia_vi"
    if any(
        k in n
        for k in [
            "nấm",
            "rong biển",
            "rau",
            "cải",
            "bắp cải",
            "xà lách",
            "măng tây",
            "bông cải",
        ]
    ):
        return "rau_cu"
    if any(
        k in n
        for k in [
            "cà chua",
            "dưa leo",
            "bí đỏ",
            "khoai",
            "cà rốt",
            "đậu cô ve",
            "thơm",
            "đậu bắp",
            "giá đỗ",
            "khế",
            "đu đủ",
            "măng",
            "hành tây",
            "hoa chuối",
            "hoa thiên lý",
            "đậu hà lan",
            "su hào",
            "bầu",
            "khổ qua",
            "bí đao",
            "mướp",
            "cà tím",
            "ngó sen",
            "bắp ngọt",
            "su su",
            "ớt chuông",
            "bông bí",
        ]
    ):
        return "cu_qua"
    return "khac"


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

    def get_conversions(self) -> list[Any]:
        """Get conversions list as domain IngredientConversion objects."""
        from app.domain.models import IngredientConversion, QuantityUnit

        bundle = self.get_catalogue_bundle()
        raw = bundle.get("conversions", STANDARD_CONVERSIONS)
        return [
            IngredientConversion(
                from_ingredient_id=UUID(c["from_ingredient_id"]),
                to_ingredient_id=UUID(c["to_ingredient_id"]),
                ratio=Decimal(str(c["ratio"])),
                from_unit=QuantityUnit(c.get("from_unit", "g")),
                to_unit=QuantityUnit(c.get("to_unit", "g")),
                note=c.get("note"),
            )
            for c in raw
        ]


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
            (
                "0738fdf0-710e-5aed-bbb5-5ba1f0c05f3b",
                "Gạo",
                "gao",
                "gao_bot_mi",
                ["Gạo tẻ", "Gạo trắng"],
            ),
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
                            prep_time_minutes=row.get("prep_time_minutes"),
                            prep_time_source_url=row.get("prep_time_source_url"),
                            prep_time_verified_at=date.fromisoformat(row["prep_time_verified_at"])
                            if row.get("prep_time_verified_at")
                            else None,
                            cook_time_minutes=row.get("cook_time_minutes"),
                            cook_time_source_url=row.get("cook_time_source_url"),
                            cook_time_verified_at=date.fromisoformat(row["cook_time_verified_at"])
                            if row.get("cook_time_verified_at")
                            else None,
                            difficulty=row.get("difficulty"),
                            difficulty_source_url=row.get("difficulty_source_url"),
                            difficulty_verified_at=date.fromisoformat(row["difficulty_verified_at"])
                            if row.get("difficulty_verified_at")
                            else None,
                            storage_tips=row.get("storage_tips") or [],
                            storage_source_url=row.get("storage_source_url"),
                            storage_verified_at=date.fromisoformat(row["storage_verified_at"])
                            if row.get("storage_verified_at")
                            else None,
                        )

        # Cập nhật category chuẩn và default_unit cho tất cả nguyên liệu dựa trên công thức
        unit_counts: dict[UUID, dict[QuantityUnit, int]] = {}
        for rec in self.recipes.values():
            for ri in rec.ingredients:
                unit_counts.setdefault(ri.ingredient_id, {})
                unit_counts[ri.ingredient_id][ri.unit] = (
                    unit_counts[ri.ingredient_id].get(ri.unit, 0) + 1
                )

        for ing in self.ingredients.values():
            ing.category = classify_ingredient(ing.name)
            counts = unit_counts.get(ing.id)
            if counts:
                ing.default_unit = max(counts.keys(), key=lambda u: counts[u])
            else:
                ing.default_unit = QuantityUnit.GRAM

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
                "default_unit": i.default_unit.value,
                "aliases": sorted(i.aliases),
                "allergens": sorted(i.allergens),
                "allergen_verification_status": i.allergen_verification_status,
                "allergen_source_url": i.allergen_source_url,
                "allergen_verified_at": i.allergen_verified_at.isoformat()
                if i.allergen_verified_at
                else None,
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
                "dietary_status": r.dietary_status,
                "dietary_source_url": r.dietary_source_url,
                "dietary_verified_at": r.dietary_verified_at.isoformat()
                if r.dietary_verified_at
                else None,
                "spice_level": r.spice_level,
                "spice_source_url": r.spice_source_url,
                "spice_verified_at": r.spice_verified_at.isoformat()
                if r.spice_verified_at
                else None,
                "prep_time_minutes": r.prep_time_minutes,
                "prep_time_source_url": r.prep_time_source_url,
                "prep_time_verified_at": r.prep_time_verified_at.isoformat()
                if r.prep_time_verified_at
                else None,
                "cook_time_minutes": r.cook_time_minutes,
                "cook_time_source_url": r.cook_time_source_url,
                "cook_time_verified_at": r.cook_time_verified_at.isoformat()
                if r.cook_time_verified_at
                else None,
                "difficulty": r.difficulty,
                "difficulty_source_url": r.difficulty_source_url,
                "difficulty_verified_at": r.difficulty_verified_at.isoformat()
                if r.difficulty_verified_at
                else None,
                "storage_tips": r.storage_tips,
                "storage_source_url": r.storage_source_url,
                "storage_verified_at": r.storage_verified_at.isoformat()
                if r.storage_verified_at
                else None,
            }
            for r in self.recipes.values()
        ]
        bundle = {
            "catalogue_version": CATALOGUE_VERSION,
            "categories": STANDARD_CATEGORIES,
            "conversions": STANDARD_CONVERSIONS,
            "ingredients": sorted(ingredients_data, key=lambda x: x["id"]),
            "recipes": sorted(recipes_data, key=lambda x: x["id"]),
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
            "id, name, normalized_name, category, default_unit, allergens, "
            "allergen_verification_status, allergen_source_url, allergen_verified_at, "
            "ingredient_aliases(alias)"
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
            raw_u = row.get("default_unit") or "g"
            try:
                du = QuantityUnit(raw_u)
            except Exception:
                du = QuantityUnit.GRAM
            results.append(
                Ingredient(
                    id=UUID(row["id"]),
                    name=row["name"],
                    normalized_name=row["normalized_name"],
                    category=row.get("category") or "khac",
                    default_unit=du,
                    aliases=aliases,
                    allergens=row.get("allergens") or [],
                    allergen_verification_status=row.get("allergen_verification_status")
                    or "unknown",
                    allergen_source_url=row.get("allergen_source_url"),
                    allergen_verified_at=date.fromisoformat(row["allergen_verified_at"])
                    if row.get("allergen_verified_at")
                    else None,
                )
            )
        return results

    def get_ingredient_by_id(self, ingredient_id: UUID) -> Ingredient | None:
        response = (
            self.client.table("ingredients")
            .select(
                "id, name, normalized_name, category, default_unit, allergens, "
                "allergen_verification_status, allergen_source_url, allergen_verified_at, "
                "ingredient_aliases(alias)"
            )
            .eq("id", str(ingredient_id))
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        row = response.data[0]
        aliases = [a["alias"] for a in row.get("ingredient_aliases", [])]
        raw_u = row.get("default_unit") or "g"
        try:
            du = QuantityUnit(raw_u)
        except Exception:
            du = QuantityUnit.GRAM
        return Ingredient(
            id=UUID(row["id"]),
            name=row["name"],
            normalized_name=row["normalized_name"],
            category=row.get("category") or "khac",
            default_unit=du,
            aliases=aliases,
            allergens=row.get("allergens") or [],
            allergen_verification_status=row.get("allergen_verification_status") or "unknown",
            allergen_source_url=row.get("allergen_source_url"),
            allergen_verified_at=date.fromisoformat(row["allergen_verified_at"])
            if row.get("allergen_verified_at")
            else None,
        )

    def get_recipes(self, category: DishCategory | None = None) -> list[Recipe]:
        query = self.client.table("recipes").select(
            "id, name, category, servings, instructions, dietary_status, "
            "dietary_source_url, dietary_verified_at, "
            "spice_level, spice_source_url, spice_verified_at, "
            "prep_time_minutes, prep_time_source_url, prep_time_verified_at, "
            "cook_time_minutes, cook_time_source_url, cook_time_verified_at, "
            "difficulty, difficulty_source_url, difficulty_verified_at, "
            "storage_tips, storage_source_url, storage_verified_at, "
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
                    dietary_status=row.get("dietary_status") or "unknown",
                    dietary_source_url=row.get("dietary_source_url"),
                    dietary_verified_at=date.fromisoformat(row["dietary_verified_at"])
                    if row.get("dietary_verified_at")
                    else None,
                    spice_level=row.get("spice_level"),
                    spice_source_url=row.get("spice_source_url"),
                    spice_verified_at=date.fromisoformat(row["spice_verified_at"])
                    if row.get("spice_verified_at")
                    else None,
                    prep_time_minutes=row.get("prep_time_minutes"),
                    prep_time_source_url=row.get("prep_time_source_url"),
                    prep_time_verified_at=date.fromisoformat(row["prep_time_verified_at"])
                    if row.get("prep_time_verified_at")
                    else None,
                    cook_time_minutes=row.get("cook_time_minutes"),
                    cook_time_source_url=row.get("cook_time_source_url"),
                    cook_time_verified_at=date.fromisoformat(row["cook_time_verified_at"])
                    if row.get("cook_time_verified_at")
                    else None,
                    difficulty=row.get("difficulty"),
                    difficulty_source_url=row.get("difficulty_source_url"),
                    difficulty_verified_at=date.fromisoformat(row["difficulty_verified_at"])
                    if row.get("difficulty_verified_at")
                    else None,
                    storage_tips=row.get("storage_tips") or [],
                    storage_source_url=row.get("storage_source_url"),
                    storage_verified_at=date.fromisoformat(row["storage_verified_at"])
                    if row.get("storage_verified_at")
                    else None,
                )
            )
        return recipes

    def get_recipe_by_id(self, recipe_id: UUID) -> Recipe | None:
        response = (
            self.client.table("recipes")
            .select(
                "id, name, category, servings, instructions, dietary_status, "
                "dietary_source_url, dietary_verified_at, spice_level, spice_source_url, "
                "prep_time_minutes, prep_time_source_url, prep_time_verified_at, "
                "cook_time_minutes, cook_time_source_url, cook_time_verified_at, "
                "difficulty, difficulty_source_url, difficulty_verified_at, "
                "storage_tips, storage_source_url, storage_verified_at, "
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
            dietary_status=row.get("dietary_status") or "unknown",
            dietary_source_url=row.get("dietary_source_url"),
            dietary_verified_at=date.fromisoformat(row["dietary_verified_at"])
            if row.get("dietary_verified_at")
            else None,
            spice_level=row.get("spice_level"),
            spice_source_url=row.get("spice_source_url"),
            spice_verified_at=date.fromisoformat(row["spice_verified_at"])
            if row.get("spice_verified_at")
            else None,
            prep_time_minutes=row.get("prep_time_minutes"),
            prep_time_source_url=row.get("prep_time_source_url"),
            prep_time_verified_at=date.fromisoformat(row["prep_time_verified_at"])
            if row.get("prep_time_verified_at")
            else None,
            cook_time_minutes=row.get("cook_time_minutes"),
            cook_time_source_url=row.get("cook_time_source_url"),
            cook_time_verified_at=date.fromisoformat(row["cook_time_verified_at"])
            if row.get("cook_time_verified_at")
            else None,
            difficulty=row.get("difficulty"),
            difficulty_source_url=row.get("difficulty_source_url"),
            difficulty_verified_at=date.fromisoformat(row["difficulty_verified_at"])
            if row.get("difficulty_verified_at")
            else None,
            storage_tips=row.get("storage_tips") or [],
            storage_source_url=row.get("storage_source_url"),
            storage_verified_at=date.fromisoformat(row["storage_verified_at"])
            if row.get("storage_verified_at")
            else None,
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
                "default_unit": i.default_unit.value,
                "aliases": sorted(i.aliases),
                "allergens": sorted(i.allergens),
                "allergen_verification_status": i.allergen_verification_status,
                "allergen_source_url": i.allergen_source_url,
                "allergen_verified_at": i.allergen_verified_at.isoformat()
                if i.allergen_verified_at
                else None,
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
                "dietary_status": r.dietary_status,
                "dietary_source_url": r.dietary_source_url,
                "dietary_verified_at": r.dietary_verified_at.isoformat()
                if r.dietary_verified_at
                else None,
                "spice_level": r.spice_level,
                "spice_source_url": r.spice_source_url,
                "spice_verified_at": r.spice_verified_at.isoformat()
                if r.spice_verified_at
                else None,
                "prep_time_minutes": r.prep_time_minutes,
                "prep_time_source_url": r.prep_time_source_url,
                "prep_time_verified_at": r.prep_time_verified_at.isoformat()
                if r.prep_time_verified_at
                else None,
                "cook_time_minutes": r.cook_time_minutes,
                "cook_time_source_url": r.cook_time_source_url,
                "cook_time_verified_at": r.cook_time_verified_at.isoformat()
                if r.cook_time_verified_at
                else None,
                "difficulty": r.difficulty,
                "difficulty_source_url": r.difficulty_source_url,
                "difficulty_verified_at": r.difficulty_verified_at.isoformat()
                if r.difficulty_verified_at
                else None,
                "storage_tips": r.storage_tips,
                "storage_source_url": r.storage_source_url,
                "storage_verified_at": r.storage_verified_at.isoformat()
                if r.storage_verified_at
                else None,
            }
            for r in recipes
        ]
        categories = STANDARD_CATEGORIES
        conversions = STANDARD_CONVERSIONS
        try:
            res_c = (
                self.client.table("ingredient_categories")
                .select("*")
                .order("display_order")
                .execute()
            )
            if res_c.data:
                categories = res_c.data
        except Exception:
            pass
        try:
            res_v = self.client.table("ingredient_conversions").select("*").execute()
            if res_v.data:
                conversions = res_v.data
        except Exception:
            pass

        bundle = {
            "catalogue_version": CATALOGUE_VERSION,
            "categories": categories,
            "conversions": conversions,
            "ingredients": sorted(ingredients_data, key=lambda x: x["id"]),
            "recipes": sorted(recipes_data, key=lambda x: x["id"]),
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
