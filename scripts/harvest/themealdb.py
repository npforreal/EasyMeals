"""TheMealDB source (https://www.themealdb.com/api.php): ingredients list and full recipes.

Content is in English and user-contributed. The free test key ("1") is meant for development and
education; check the provider's current terms (and a paid key) before using the data commercially.
"""

import re
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from .normalize import match_keys, normalize

SOURCE = "themealdb"
LICENSE_NOTE = "TheMealDB — check provider terms before commercial use"
LETTERS = "abcdefghijklmnopqrstuvwxyz0123456789"

_MAIN_CATEGORIES = {"beef", "chicken", "lamb", "pork", "seafood", "goat"}
_VEG_CATEGORIES = {"vegetarian", "vegan", "side"}
_STEP_MARKER = re.compile(r"^(step\s*)?\d+[.):]?$", re.IGNORECASE)
_QUANTITY = re.compile(
    r"^\s*(?P<num>\d+\s+\d+/\d+|\d+/\d+|\d+(?:[.,]\d+)?)\s*"
    r"(?P<unit>kg|g|gr|grams?|ml|l|litres?|liters?)?\s*$",
    re.IGNORECASE,
)
_UNIT_MAP = {
    "g": "g", "gr": "g", "gram": "g", "grams": "g", "kg": "kg",
    "ml": "ml", "l": "l", "litre": "l", "litres": "l", "liter": "l", "liters": "l",
}  # fmt: skip

GetJson = Callable[[str], dict]


def dish_category(name: str, source_category: str | None) -> str | None:
    """Best-effort mapping to the app's categories (man/rau/canh); None when unclear."""
    if "soup" in name.lower() or "broth" in name.lower():
        return "canh"
    cat = (source_category or "").strip().lower()
    if cat in _MAIN_CATEGORIES:
        return "man"
    if cat in _VEG_CATEGORIES:
        return "rau"
    return None


def parse_quantity(measure: str) -> tuple[str, str] | None:
    """Parse only unambiguous measures ("200g", "1.5 l", "2", "1/2 kg"); anything else is None.
    A bare number means pieces. Unknown units such as "tbsp" or "clove" stay in the raw text."""
    match = _QUANTITY.match(measure or "")
    if not match:
        return None
    text = match["num"].replace(",", ".")
    try:
        if "/" in text:
            whole, _, frac = text.rpartition(" ")
            top, bottom = frac.split("/")
            value = Decimal(top) / Decimal(bottom) + (Decimal(whole) if whole else 0)
        else:
            value = Decimal(text)
    except (InvalidOperation, ZeroDivisionError):
        return None
    if value <= 0:
        return None
    raw_unit = (match["unit"] or "").lower()
    unit = _UNIT_MAP.get(raw_unit, "piece" if not raw_unit else None)
    if unit is None:
        return None
    return format(value.normalize(), "f"), unit


def split_steps(instructions: str) -> list[str]:
    steps = []
    for line in re.split(r"[\r\n]+", instructions or ""):
        line = line.strip()
        if line and not _STEP_MARKER.match(line):
            steps.append(line)
    return steps


def meal_to_record(meal: dict) -> dict:
    ingredients, seen = [], set()
    for i in range(1, 21):
        name = (meal.get(f"strIngredient{i}") or "").strip()
        keys = match_keys(name)
        if not keys or keys & seen:
            continue
        seen |= keys
        measure = (meal.get(f"strMeasure{i}") or "").strip()
        parsed = parse_quantity(measure)
        ingredients.append(
            {
                "name": name,
                "normalized_name": normalize(name),
                "measure": measure,
                "quantity": parsed[0] if parsed else None,
                "unit": parsed[1] if parsed else None,
            }
        )
    name = meal["strMeal"].strip()
    alt = (meal.get("strMealAlternate") or "").strip()
    return {
        "name": name,
        "normalized_name": normalize(name),
        "aliases": [alt] if alt else [],
        "dish_category": dish_category(name, meal.get("strCategory")),
        "source_category": meal.get("strCategory"),
        "area": meal.get("strArea") or meal.get("strCountry"),
        "instructions": split_steps(meal.get("strInstructions", "")),
        "ingredients": ingredients,
        "language": "en",
        "source": SOURCE,
        "source_id": meal["idMeal"],
        "source_url": meal.get("strSource") or f"https://www.themealdb.com/meal/{meal['idMeal']}",
        "license": LICENSE_NOTE,
        "fetched_at": _now(),
    }


def ingredient_record(name: str, source_id: str | None = None, kind: str | None = None) -> dict:
    return {
        "name": name.strip(),
        "normalized_name": normalize(name),
        "aliases": [],
        "category": kind,
        "language": "en",
        "source": SOURCE,
        "source_id": source_id,
        "license": LICENSE_NOTE,
        "fetched_at": _now(),
    }


class TheMealDB:
    def __init__(self, get_json: GetJson, api_key: str = "1") -> None:
        self._get = get_json
        self._base = f"https://www.themealdb.com/api/json/v1/{api_key}/"

    def ingredients(self) -> Iterator[dict]:
        for item in self._get(self._base + "list.php?i=list").get("meals") or []:
            name = (item.get("strIngredient") or "").strip()
            if name:
                yield ingredient_record(name, item.get("idIngredient"), item.get("strType"))

    def meals(self) -> Iterator[dict]:
        for letter in LETTERS:
            for meal in self._get(self._base + f"search.php?f={letter}").get("meals") or []:
                yield meal_to_record(meal)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
