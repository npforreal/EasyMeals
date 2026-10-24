"""Tests for the open-data harvester (Vietnamese source and dataset store)."""

import json
from argparse import Namespace
from pathlib import Path

from scripts.harvest.cli import build_parser, run
from scripts.harvest.normalize import match_keys, normalize
from scripts.harvest.store import DatasetStore
from scripts.harvest.vietnam import VietnameseSource, ingredient_record


def test_normalize_strips_diacritics_case_and_punctuation():
    assert normalize("  Thịt  Ba-Chỉ! ") == "thit ba chi"
    assert normalize("Đậu hũ") == "dau hu"


def test_match_keys_fold_plural_and_include_aliases():
    assert match_keys("Red Onions") & match_keys("red onion")
    assert match_keys("Thơm (Dứa)", ["Khóm"]) & match_keys("khom")
    assert not (match_keys("Glass") & match_keys("Gla"))  # "ss" is not a plural


def _read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_store_skips_known_items_and_writes_new_ones(tmp_path):
    store = DatasetStore(tmp_path)
    store.add_baseline(ingredients=[("Thịt ba chỉ", ["Thịt rọi"])], recipes=["Thịt kho tàu"])

    assert store.add_ingredient(ingredient_record("thit roi")) == "baseline"  # via alias
    assert store.add_ingredient(ingredient_record("Tỏi")) is None
    assert store.add_ingredient(ingredient_record("toi")) == "run"  # same run
    assert store.add_recipe({"name": "THỊT KHO TÀU"}) == "baseline"
    assert store.add_recipe({"name": "Bò kho", "aliases": ["Bo kho"]}) is None
    assert store.add_recipe({"name": "bo kho"}) == "run"  # alias of an accepted item

    assert [r["name"] for r in _read(tmp_path / "ingredients.jsonl")] == ["Tỏi"]
    assert [r["name"] for r in _read(tmp_path / "recipes.jsonl")] == ["Bò kho"]
    assert store.ingredient_stats.added == 1 and store.ingredient_stats.duplicates == 2


def test_store_reloads_existing_files_so_reruns_save_nothing(tmp_path):
    first = DatasetStore(tmp_path)
    first.add_ingredient(ingredient_record("Tỏi"))
    first.add_recipe({"name": "Bò kho"})

    second = DatasetStore(tmp_path)
    assert second.add_ingredient(ingredient_record("Tỏi")) == "dataset"
    assert second.add_recipe({"name": "bo kho"}) == "dataset"
    assert len(_read(tmp_path / "ingredients.jsonl")) == 1


def test_dry_run_writes_nothing(tmp_path):
    store = DatasetStore(tmp_path, dry_run=True)
    assert store.add_ingredient(ingredient_record("Tỏi")) is None
    assert store.ingredient_stats.added == 1
    assert not (tmp_path / "ingredients.jsonl").exists()


def test_vietnamese_source_yields_valid_records():
    source = VietnameseSource()
    meals = list(source.meals())
    assert len(meals) >= 100
    first = meals[0]
    assert "name" in first
    assert "dish_category" in first
    assert "ingredients" in first
    assert first["language"] == "vi"

    ingredients = list(source.ingredients())
    assert len(ingredients) >= 100
    assert all(i["language"] == "vi" for i in ingredients)


def _args(tmp_path, *extra):
    return build_parser().parse_args(["--data-dir", str(tmp_path), *extra])


def test_run_cli_with_vietnamese_source(tmp_path):
    out: list[str] = []
    run(_args(tmp_path, "--no-app-baseline", "--limit", "2"), out=out.append)

    ing_path = tmp_path / "ingredients.jsonl"
    rec_path = tmp_path / "recipes.jsonl"
    assert ing_path.exists()
    assert rec_path.exists()
    assert len(_read(rec_path)) == 2


def test_namespace_type_is_what_cli_builds():
    assert isinstance(build_parser().parse_args([]), Namespace)
