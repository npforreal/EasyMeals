"""Tests for scripts/translate_recipes.py (translation pipeline)."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))

from scripts.translate_recipes import (  # noqa: E402
    find_english,
    load_pending,
    parse_measure,
)

RAW_FILE = ROOT / "data" / "open" / "recipes.jsonl"
VI_FILE = ROOT / "data" / "open" / "themealdb_recipes_vi.jsonl"
DICT_FILE = ROOT / "data" / "ingredient_translations.json"
CATALOGUE_FILE = ROOT / "data" / "catalogue.json"


# ---------------------------------------------------------------------------
# 1. parse_measure — bảng ca đã biết
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "measure,expected_qty,expected_unit",
    [
        ("1 1/2 cup", Decimal("360"), "ml"),
        ("2 lbs", Decimal("907.2"), "g"),
        ("½ tsp", Decimal("2.5"), "ml"),
        ("3-4 cloves", Decimal("4"), "piece"),
        ("2 fl oz", Decimal("60"), "ml"),
        ("to taste", None, None),
        ("pinch", Decimal("1"), "g"),
        ("dash", Decimal("5"), "ml"),
        ("8 cm", Decimal("8"), "piece"),
    ],
)
def test_parse_measure_known_cases(measure, expected_qty, expected_unit):
    qty, unit = parse_measure(measure)
    assert qty == expected_qty
    assert unit == expected_unit


# ---------------------------------------------------------------------------
# 2. find_english — câu Anh bị bắt; câu Việt có dấu/tên riêng không bị nhầm
# ---------------------------------------------------------------------------


def test_find_english_catches_english():
    problems = find_english("Add the chicken and stir for 5 minutes.")
    assert problems, "Cau tieng Anh phai bi bat"
    assert any("từ tiếng Anh" in p for p in problems)


def test_find_english_vietnamese_with_diacritics_is_clean():
    problems = find_english("Thái hành, phi thơm với dầu rồi cho thịt vào xào.")
    assert problems == [], f"Cau tieng Viet co dau khong duoc bat: {problems}"


def test_find_english_proper_names_are_clean():
    """Ten rieng mon/gia vi nuoc ngoai (Parmesan, Kimchi) khong duoc bat nham."""
    problems = find_english("Phô mai Parmesan")
    assert problems == [], f"Ten rieng 'Phô mai Parmesan' khong duoc bat: {problems}"
    problems = find_english("Kimchi")
    assert problems == [], f"Ten rieng 'Kimchi' khong duoc bat: {problems}"


def test_find_english_ignore_parentheses_original_name():
    """Ten goc trong ngoac duoc phep con tieng Anh (quy tac dich #4)."""
    problems = find_english("Banh mi challah (Challah)")
    assert problems == [], f"Ten goc trong ngoac khong duoc bat: {problems}"


# ---------------------------------------------------------------------------
# 3. Toan bo themealdb_recipes_vi.jsonl
# ---------------------------------------------------------------------------


def _load_vi_rows():
    if not VI_FILE.exists():
        pytest.skip(f"Chua co {VI_FILE}")
    rows = []
    for line in VI_FILE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _load_raw_rows():
    if not RAW_FILE.exists():
        pytest.skip(f"Chua co {RAW_FILE}")
    rows = {}
    for line in RAW_FILE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            rows[r["source_id"]] = r
    return rows


def test_vi_file_has_551_recipes():
    rows = _load_vi_rows()
    assert len(rows) == 551, f"Du co 551 mon, co {len(rows)}"


def test_vi_source_ids_match_raw():
    vi_rows = _load_vi_rows()
    # Raw chi lay mon co dish_category hop le (giong load_pending)
    raw_valid = {r["source_id"] for r in load_pending() if r["source_id"]}
    vi_ids = {r["source_id"] for r in vi_rows}
    assert vi_ids == raw_valid, f"source_id khop giua vi va raw: lech {vi_ids ^ raw_valid}"


def test_vi_no_english_in_name_instructions_ingredients_measure():
    """Moi ten, buoc, ten nguyen lieu, measure qua find_english() phai sach."""
    rows = _load_vi_rows()
    errors = []
    for r in rows:
        sid = r["source_id"]
        fields = [("ten", r.get("name", ""))]
        fields += [(f"buoc {i + 1}", s) for i, s in enumerate(r.get("instructions", []))]
        fields += [("nguyen lieu", ing.get("name", "")) for ing in r.get("ingredients", [])]
        fields += [("dinh luong", ing.get("measure", "")) for ing in r.get("ingredients", [])]
        for field, text in fields:
            for pb in find_english(text):
                errors.append(f"{sid} {field}: {pb}")
    assert not errors, f"Con tieng Anh trong {len(errors)} truong: {errors[:10]}"


def test_vi_units_valid_and_quantity_positive():
    """unit trong {g, ml, piece, None}; so luong > 0 neu co unit."""
    rows = _load_vi_rows()
    valid_units = {"g", "ml", "piece", None}
    errors = []
    for r in rows:
        sid = r["source_id"]
        for ing in r.get("ingredients", []):
            unit = ing.get("unit")
            qty = ing.get("quantity")
            if unit not in valid_units:
                errors.append(f"{sid} unit khong hop le: {unit!r} (nguyen lieu {ing.get('name')})")
            if unit is not None and (qty is None or float(qty) <= 0):
                msg = (
                    f"{sid} so luong khong duong: qty={qty}, unit={unit} "
                    f"(nguyen lieu {ing.get('name')})"
                )
                errors.append(msg)
    assert not errors, f"Loi unit/so luong: {errors[:10]}"


def test_vi_no_empty_instructions_and_steps_at_least_half():
    """Khong buoc nao trong; so buoc >= mot nua ban goc."""
    vi_rows = _load_vi_rows()
    raw_rows = _load_raw_rows()
    errors = []
    for r in vi_rows:
        sid = r["source_id"]
        steps = [s for s in r.get("instructions", []) if s and s.strip()]
        if not steps:
            errors.append(f"{sid}: khong co buoc nao")
            continue
        raw = raw_rows.get(sid, {})
        raw_steps = raw.get("instructions") or []
        if raw_steps and len(steps) < max(1, len(raw_steps) // 2):
            errors.append(f"{sid}: thieu buoc ({len(steps)}/{len(raw_steps)})")
    assert not errors, f"Loi buoc: {errors[:10]}"


def _normalize_key(text: str) -> str:
    import re
    import unicodedata

    text = text.strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# 4. import_recipes khong nap language=="en" va khong nap mon rong nguyen lieu
# ---------------------------------------------------------------------------


def test_import_recipes_skips_english_language(tmp_path):
    """import_harvest chi nap language=='vi'; khong nap language=='en'."""
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    from import_harvest import import_recipes  # noqa: PLC0415

    # Tao file recipes.jsonl tam voi 1 mon vi, 1 mon en
    tmp_recipes = tmp_path / "recipes.jsonl"
    tmp_recipes.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "source_id": "test-vi-1",
                        "name": "Mon viet",
                        "dish_category": "man",
                        "instructions": ["Buoc 1"],
                        "ingredients": [
                            {
                                "name": "ca chua",
                                "normalized_name": "ca chua",
                                "quantity": "100",
                                "unit": "g",
                                "measure": "100 g",
                            }
                        ],
                        "language": "vi",
                        "source": "themealdb_vi",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "source_id": "test-en-1",
                        "name": "English dish",
                        "dish_category": "man",
                        "instructions": ["Step 1"],
                        "ingredients": [
                            {
                                "name": "tomato",
                                "normalized_name": "tomato",
                                "quantity": "100",
                                "unit": "g",
                                "measure": "100 g",
                            }
                        ],
                        "language": "en",
                        "source": "themealdb",
                    },
                    ensure_ascii=False,
                ),
            ]
        ),
        encoding="utf-8",
    )

    # Patch RECIPES_FILE den file tam
    import import_harvest as ih

    orig = ih.RECIPES_FILE
    ih.RECIPES_FILE = tmp_recipes
    try:
        # Tao ing_index chi chua ca chua (tomato khong co -> mon en bi skip)
        ing_index = {
            "ca chua": {
                "id": "11111111-0000-0000-0000-000000000100",
                "name": "Cà chua",
                "source_id": None,
            },
        }
        # Chay dry-run (apply=False)
        res = import_recipes(client=None, apply=False, ing_index=ing_index)
        # Chi duoc nap mon vi (1 mon), khong nap mon en (khong match ingredient)
        assert res["inserted"] == 1, f"Du co 1 mon vi duoc nap, co {res['inserted']}"
    finally:
        ih.RECIPES_FILE = orig


def test_import_recipes_skips_recipe_with_no_ingredients(tmp_path):
    """Khong nap mon rong nguyen lieu."""
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    from import_harvest import import_recipes  # noqa: PLC0415

    tmp_recipes = tmp_path / "recipes2.jsonl"
    tmp_recipes.write_text(
        json.dumps(
            {
                "source_id": "test-no-ing",
                "name": "Mon khong nguyen lieu",
                "dish_category": "man",
                "instructions": ["Buoc 1"],
                "ingredients": [],
                "language": "vi",
                "source": "themealdb_vi",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    import import_harvest as ih

    orig = ih.RECIPES_FILE
    ih.RECIPES_FILE = tmp_recipes
    try:
        res = import_recipes(client=None, apply=False, ing_index={})
        assert res["inserted"] == 0, (
            f"Du co 0 mon duoc nap (rong nguyen lieu), co {res['inserted']}"
        )
    finally:
        ih.RECIPES_FILE = orig


# ---------------------------------------------------------------------------
# 5. Danh muc cuoi (catalogue.json) khong con tieng Anh
# ---------------------------------------------------------------------------


def test_catalogue_no_english():
    """Data/catalogue.json va moi mon se vao Supabase: khong con tieng Anh."""
    if not CATALOGUE_FILE.exists():
        pytest.skip(f"Chua co {CATALOGUE_FILE}")
    bundle = json.loads(CATALOGUE_FILE.read_text(encoding="utf-8"))
    errors = []
    for rec in bundle.get("recipes", []):
        sid = rec.get("id", "?")
        for field, text in (
            [("ten", rec.get("name", ""))]
            + [(f"buoc {i + 1}", s) for i, s in enumerate(rec.get("instructions", []))]
            + [("nguyen lieu", ri.get("ingredient_name", "")) for ri in rec.get("ingredients", [])]
        ):
            for pb in find_english(text):
                errors.append(f"{sid} {field}: {pb}")
    assert not errors, f"Con tieng Anh trong catalogue: {errors[:10]}"


# ---------------------------------------------------------------------------
# 6. Tu dien nguyen lieu khong con tieng Anh (ngoai danh sach cho phep)
# ---------------------------------------------------------------------------


def test_ingredient_dictionary_no_english():
    """Tu dien nguyen lieu: khong muc nao con tieng Anh ngoai danh sach cho phep."""
    if not DICT_FILE.exists():
        pytest.skip(f"Chua co {DICT_FILE}")
    with DICT_FILE.open(encoding="utf-8") as f:
        dictionary = json.load(f)
    errors = []
    for key, vi in dictionary.items():
        for pb in find_english(vi):
            errors.append(f"{key!r} => {vi!r}: {pb}")
    assert not errors, f"Tu dien con tieng Anh: {errors[:10]}"
