"""Vietnamese recipes source for EasyMeals harvest pipeline.

Provides structured Vietnamese recipes and curated translated international dishes
conforming to the meal planning structure (man/rau/canh) with metric units (g, kg, ml, piece).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .normalize import normalize

SOURCE = "vietnamese_standard"
LICENSE_NOTE = "EasyMeals Vietnamese Culinary Standard Collection"

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "open"
VN_RECIPES_FILE = DATA_DIR / "vietnamese_recipes.jsonl"
INTL_RECIPES_FILE = DATA_DIR / "international_recipes_vi.jsonl"


class VietnameseSource:
    """Source for curated Vietnamese family dishes and translated international recipes."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or DATA_DIR

    def meals(self) -> Iterator[dict[str, Any]]:
        """Yield recipe records from Vietnamese and translated international datasets."""
        files = [
            self.data_dir / "vietnamese_recipes.jsonl",
            self.data_dir / "international_recipes_vi.jsonl",
        ]
        now = datetime.now(UTC).isoformat()
        for fpath in files:
            if not fpath.exists():
                continue
            with fpath.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    record = {
                        "name": row["name"],
                        "normalized_name": row.get("normalized_name") or normalize(row["name"]),
                        "aliases": row.get("aliases", []),
                        "dish_category": row.get("dish_category"),
                        "source_category": row.get("area", "Vietnamese"),
                        "area": row.get("area", "Vietnamese"),
                        "instructions": row.get("instructions", []),
                        "servings": row.get("servings", 4),
                        "ingredients": row.get("ingredients", []),
                        "language": "vi",
                        "source": row.get("source", SOURCE),
                        "source_id": str(row.get("source_id", "")),
                        "source_url": row.get("source_url", ""),
                        "license": LICENSE_NOTE,
                        "fetched_at": now,
                    }
                    yield record

    def ingredients(self) -> Iterator[dict[str, Any]]:
        """Extract all unique ingredients used across the recipes."""
        seen = set()
        for meal in self.meals():
            for ing in meal.get("ingredients", []):
                name = ing.get("name", "").strip()
                norm = normalize(name)
                if norm and norm not in seen:
                    seen.add(norm)
                    yield {
                        "name": name,
                        "normalized_name": norm,
                        "aliases": [],
                        "category": None,
                        "language": "vi",
                        "source": SOURCE,
                        "source_id": norm,
                    }
