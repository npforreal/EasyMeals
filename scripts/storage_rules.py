"""Áp dụng luật bảo quản (data/open/storage_rules.json) và overlay metadata công thức.

- Mỗi công thức nhận đúng một luật chính (theo `order`, luật đầu tiên khớp) cộng luật
  chung `kind == "universal"`. Không khớp luật nào -> storage_tips rỗng.
- Overlay tuỳ chọn `data/open/recipe_metadata.jsonl` (khoá `recipe_id`): chỉ ghi đè
  các khoá có mặt; thiếu file là no-op; recipe_id lạ -> ValueError.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "data" / "open" / "storage_rules.json"
OVERLAY_PATH = ROOT / "data" / "open" / "recipe_metadata.jsonl"

OVERLAY_KEYS = (
    "prep_time_minutes",
    "prep_time_source_url",
    "prep_time_verified_at",
    "cook_time_minutes",
    "cook_time_source_url",
    "cook_time_verified_at",
    "difficulty",
    "difficulty_source_url",
    "difficulty_verified_at",
)


def load_rules(path: Path = RULES_PATH) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def rule_matches(rule: dict[str, Any], recipe_category: str, ing_categories: set[str]) -> bool:
    """Khớp theo recipe_category và (nếu có danh sách không rỗng) category nguyên liệu.

    `any_ingredient_category: []` nghĩa là "không yêu cầu" (luật dự phòng, đứng sau
    các luật chặt hơn theo `order`).
    """
    m = rule.get("match", {})
    if m.get("all"):
        return True
    cats = m.get("recipe_category")
    if cats is not None and recipe_category not in cats:
        return False
    any_ing = m.get("any_ingredient_category")
    if any_ing:
        return bool(ing_categories & set(any_ing))
    return True


def primary_rule(
    rules: dict[str, Any], recipe_category: str, ing_categories: set[str]
) -> dict[str, Any] | None:
    primaries = sorted(
        (r for r in rules["rules"] if r.get("kind") == "primary"), key=lambda r: r["order"]
    )
    for r in primaries:
        if rule_matches(r, recipe_category, ing_categories):
            return r
    return None


def apply_storage_rules(
    recipes: list[dict[str, Any]],
    ingredient_category: dict[str, str],
    rules: dict[str, Any] | None = None,
) -> None:
    rules = rules or load_rules()
    sources = {s["id"]: s for s in rules["sources"]}
    universal = [r for r in rules["rules"] if r.get("kind") == "universal"]
    for rec in recipes:
        if rec.get("storage_tips"):
            continue  # đã có dữ liệu riêng, không ghi đè
        cats = {ingredient_category.get(i["ingredient_id"], "") for i in rec.get("ingredients", [])}
        prim = primary_rule(rules, rec.get("category", ""), cats)
        if prim is None:
            continue
        tips: list[str] = []
        for r in [prim, *universal]:
            for t in r["tips"]:
                if t not in tips:
                    tips.append(t)
        rec["storage_tips"] = tips
        rec["storage_source_url"] = sources[prim["source_id"]]["url"]
        rec["storage_verified_at"] = rules["fetched_at"]


def apply_overlay(recipes: list[dict[str, Any]], path: Path = OVERLAY_PATH) -> int:
    if not path.exists():
        return 0
    by_id = {r["id"]: r for r in recipes}
    n = 0
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            rid = row.get("recipe_id")
            if rid not in by_id:
                raise ValueError(
                    f"{path.name}:{lineno}: recipe_id không tồn tại trong catalogue: {rid}"
                )
            for k in OVERLAY_KEYS:
                if k in row:
                    by_id[rid][k] = row[k]
            n += 1
    return n
