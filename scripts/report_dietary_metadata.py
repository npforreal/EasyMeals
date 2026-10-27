"""Report evidence coverage for diet, allergen and spice catalogue metadata."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def audit_metadata(path: Path = ROOT / "data" / "catalogue.json") -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    ingredients = data.get("ingredients", [])
    recipes = data.get("recipes", [])
    return {
        "catalogue_version": data.get("catalogue_version"),
        "ingredient_count": len(ingredients),
        "allergen_status_counts": dict(
            Counter(i.get("allergen_verification_status", "unknown") for i in ingredients)
        ),
        "allergen_evidence_missing": sum(
            i.get("allergen_verification_status", "unknown") == "verified"
            and not (i.get("allergen_source_url") and i.get("allergen_verified_at"))
            for i in ingredients
        ),
        "recipe_count": len(recipes),
        "dietary_status_counts": dict(Counter(r.get("dietary_status", "unknown") for r in recipes)),
        "dietary_evidence_missing": sum(
            r.get("dietary_status", "unknown") in {"omnivore", "vegetarian", "vegan"}
            and not (r.get("dietary_source_url") and r.get("dietary_verified_at"))
            for r in recipes
        ),
        "spice_level_known": sum(r.get("spice_level") is not None for r in recipes),
        "spice_evidence_missing": sum(
            r.get("spice_level") is not None
            and not (r.get("spice_source_url") and r.get("spice_verified_at"))
            for r in recipes
        ),
        # E2-data: thời gian chuẩn bị, thời gian nấu, độ khó
        "prep_time_present": sum(r.get("prep_time_minutes") is not None for r in recipes),
        "prep_time_evidence_complete": sum(
            r.get("prep_time_minutes") is not None
            and r.get("prep_time_source_url")
            and r.get("prep_time_verified_at")
            for r in recipes
        ),
        "cook_time_present": sum(r.get("cook_time_minutes") is not None for r in recipes),
        "cook_time_evidence_complete": sum(
            r.get("cook_time_minutes") is not None
            and r.get("cook_time_source_url")
            and r.get("cook_time_verified_at")
            for r in recipes
        ),
        "difficulty_present": sum(r.get("difficulty") is not None for r in recipes),
        "difficulty_evidence_complete": sum(
            r.get("difficulty") is not None
            and r.get("difficulty_source_url")
            and r.get("difficulty_verified_at")
            for r in recipes
        ),
        # E3-data: mẹo bảo quản
        "storage_tips_present": sum(bool(r.get("storage_tips")) for r in recipes),
        "storage_tips_evidence_complete": sum(
            bool(r.get("storage_tips"))
            and r.get("storage_source_url")
            and r.get("storage_verified_at")
            for r in recipes
        ),
    }


if __name__ == "__main__":
    print(json.dumps(audit_metadata(), ensure_ascii=False, indent=2, sort_keys=True))
