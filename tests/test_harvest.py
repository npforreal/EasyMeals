"""Tests for the open-data harvester (no network: the API is faked)."""

import json
from argparse import Namespace
from pathlib import Path

from scripts.harvest.cli import build_parser, run
from scripts.harvest.normalize import match_keys, normalize
from scripts.harvest.store import DatasetStore
from scripts.harvest.themealdb import (
    dish_category,
    ingredient_record,
    meal_to_record,
    parse_quantity,
    split_steps,
)


def test_normalize_strips_diacritics_case_and_punctuation():
    assert normalize("  Thịt  Ba-Chỉ! ") == "thit ba chi"
    assert normalize("Đậu hũ") == "dau hu"


def test_match_keys_fold_plural_and_include_aliases():
    assert match_keys("Red Onions") & match_keys("red onion")
    assert match_keys("Thơm (Dứa)", ["Khóm"]) & match_keys("khom")
    assert not (match_keys("Glass") & match_keys("Gla"))  # "ss" is not a plural


def test_parse_quantity_only_unambiguous():
    assert parse_quantity("200g") == ("200", "g")
    assert parse_quantity("1.5 l") == ("1.5", "l")
    assert parse_quantity("1/2 kg") == ("0.5", "kg")
    assert parse_quantity("2") == ("2", "piece")
    assert parse_quantity("1 1/2 g") == ("1.5", "g")
    assert parse_quantity("1 tbsp") is None
    assert parse_quantity("To taste") is None
    assert parse_quantity("0g") is None
    assert parse_quantity("") is None


def test_dish_category_mapping():
    assert dish_category("Beef Stew", "Beef") == "man"
    assert dish_category("Greek Salad", "Vegetarian") == "rau"
    assert dish_category("Tomato Soup", "Starter") == "canh"
    assert dish_category("Apple Pie", "Dessert") is None


def test_split_steps_drops_step_markers_and_blank_lines():
    assert split_steps("STEP 1\r\nChop onions.\r\n\r\n2\r\nFry.") == ["Chop onions.", "Fry."]


def _meal(id_, name, ingredients, **extra):
    meal = {"idMeal": id_, "strMeal": name, "strCategory": "Chicken", "strInstructions": "Cook."}
    for i, (ing, measure) in enumerate(ingredients, 1):
        meal[f"strIngredient{i}"] = ing
        meal[f"strMeasure{i}"] = measure
    meal.update(extra)
    return meal


def test_meal_to_record_dedupes_ingredients_within_recipe():
    record = meal_to_record(
        _meal("1", "Pad Thai", [("Onion", "1"), ("onions", "2"), ("Garlic", "2 cloves")])
    )
    assert [i["name"] for i in record["ingredients"]] == ["Onion", "Garlic"]
    garlic = record["ingredients"][-1]
    assert garlic["quantity"] is None and garlic["measure"] == "2 cloves"
    assert record["source"] == "themealdb" and record["language"] == "en"


def _read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_store_skips_known_items_and_writes_new_ones(tmp_path):
    store = DatasetStore(tmp_path)
    store.add_baseline(ingredients=[("Thịt ba chỉ", ["Thịt rọi"])], recipes=["Thịt kho tàu"])

    assert store.add_ingredient(ingredient_record("thit roi")) == "baseline"  # via alias
    assert store.add_ingredient(ingredient_record("Garlic")) is None
    assert store.add_ingredient(ingredient_record("garlic")) == "run"  # same run
    assert store.add_recipe({"name": "THỊT KHO TÀU"}) == "baseline"
    assert store.add_recipe({"name": "Pad Thai", "aliases": ["Phad Thai"]}) is None
    assert store.add_recipe({"name": "phad thai"}) == "run"  # alias of an accepted item

    assert [r["name"] for r in _read(tmp_path / "ingredients.jsonl")] == ["Garlic"]
    assert [r["name"] for r in _read(tmp_path / "recipes.jsonl")] == ["Pad Thai"]
    assert store.ingredient_stats.added == 1 and store.ingredient_stats.duplicates == 2


def test_store_reloads_existing_files_so_reruns_save_nothing(tmp_path):
    first = DatasetStore(tmp_path)
    first.add_ingredient(ingredient_record("Garlic"))
    first.add_recipe({"name": "Pad Thai"})

    second = DatasetStore(tmp_path)
    assert second.add_ingredient(ingredient_record("Garlics")) == "dataset"
    assert second.add_recipe({"name": "pad thai"}) == "dataset"
    assert len(_read(tmp_path / "ingredients.jsonl")) == 1


def test_dry_run_writes_nothing(tmp_path):
    store = DatasetStore(tmp_path, dry_run=True)
    assert store.add_ingredient(ingredient_record("Garlic")) is None
    assert store.ingredient_stats.added == 1
    assert not (tmp_path / "ingredients.jsonl").exists()


def _fake_api(url: str) -> dict:
    if "list.php" in url:
        return {
            "meals": [
                {"idIngredient": "1", "strIngredient": "Chicken", "strType": None},
                {"idIngredient": "2", "strIngredient": "Gừng", "strType": None},  # in app seed
            ]
        }
    if url.endswith("search.php?f=a"):
        return {
            "meals": [
                _meal("10", "Adobo", [("Chicken", "500g"), ("Soy Sauce", "3 tbsp")]),
                _meal("11", "Thịt kho tàu", [("Pork", "500g")]),  # in app seed
            ]
        }
    return {"meals": None}


def _args(tmp_path, *extra):
    return build_parser().parse_args(["--data-dir", str(tmp_path), *extra])


def test_run_end_to_end_dedupes_against_seed_and_is_idempotent(tmp_path):
    out: list[str] = []
    run(_args(tmp_path), get_json=_fake_api, out=out.append)

    ingredients = {r["name"] for r in _read(tmp_path / "ingredients.jsonl")}
    recipes = {r["name"] for r in _read(tmp_path / "recipes.jsonl")}
    assert recipes == {"Adobo"}  # "Thịt kho tàu" already in the app seed
    assert ingredients == {"Chicken", "Soy Sauce"}  # "Gừng" seed; Chicken once only

    out.clear()
    run(_args(tmp_path), get_json=_fake_api, out=out.append)
    assert len(_read(tmp_path / "ingredients.jsonl")) == 2
    assert len(_read(tmp_path / "recipes.jsonl")) == 1
    assert any("0 new" in line for line in out)


def test_limit_and_what_options(tmp_path):
    run(_args(tmp_path, "--what", "ingredients", "--limit", "1"), get_json=_fake_api, out=print)
    assert [r["name"] for r in _read(tmp_path / "ingredients.jsonl")] == ["Chicken"]
    assert not (tmp_path / "recipes.jsonl").exists()


def test_namespace_type_is_what_cli_builds():
    assert isinstance(build_parser().parse_args([]), Namespace)
