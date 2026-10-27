"""Kiểm tra luật bảo quản (data/open/storage_rules.json) và overlay metadata."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import storage_rules as sr  # noqa: E402


@pytest.fixture(scope="module")
def rules():
    return sr.load_rules()


@pytest.fixture(scope="module")
def catalogue():
    return json.loads((ROOT / "data" / "catalogue.json").read_text(encoding="utf-8"))


def test_rules_have_sources_and_valid_tips(rules):
    ids = {s["id"] for s in rules["sources"]}
    assert len(rules["rules"]) <= 8
    for s in rules["sources"]:
        assert s["url"].startswith("https://") and s["license_note"]
    for r in rules["rules"]:
        assert r["source_id"] in ids
        assert r["tips"]
        for t in r["tips"]:
            assert t.strip() and len(t) <= 140


def test_one_primary_rule_per_recipe(rules, catalogue):
    cats = {i["id"]: i["category"] for i in catalogue["ingredients"]}
    for rec in catalogue["recipes"]:
        ic = {cats.get(i["ingredient_id"], "") for i in rec["ingredients"]}
        matches = [
            r
            for r in rules["rules"]
            if r["kind"] == "primary" and sr.rule_matches(r, rec["category"], ic)
        ]
        chosen = sr.primary_rule(rules, rec["category"], ic)
        if matches:
            assert chosen is matches[0]  # theo precedence (order)


def test_recipe_tips_source_is_known(rules, catalogue):
    urls = {s["url"] for s in rules["sources"]}
    for rec in catalogue["recipes"]:
        if rec["storage_tips"]:
            assert rec["storage_source_url"] in urls
            assert rec["storage_verified_at"] == rules["fetched_at"]


def test_overlay_absent_is_noop(tmp_path):
    recs = [{"id": "a", "difficulty": None}]
    assert sr.apply_overlay(recs, tmp_path / "missing.jsonl") == 0
    assert recs == [{"id": "a", "difficulty": None}]


def test_overlay_merges_present_keys_only(tmp_path):
    p = tmp_path / "o.jsonl"
    p.write_text('{"recipe_id": "a", "prep_time_minutes": 10}\n', encoding="utf-8")
    recs = [{"id": "a", "prep_time_minutes": None, "difficulty": None}]
    assert sr.apply_overlay(recs, p) == 1
    assert recs[0] == {"id": "a", "prep_time_minutes": 10, "difficulty": None}


def test_overlay_unknown_id_raises(tmp_path):
    p = tmp_path / "o.jsonl"
    p.write_text('{"recipe_id": "zzz", "difficulty": "easy"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="zzz"):
        sr.apply_overlay([{"id": "a"}], p)
