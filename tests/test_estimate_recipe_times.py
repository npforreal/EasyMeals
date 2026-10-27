"""Kiểm thử công cụ tạo bảng rà soát thời gian nấu (E2-data)."""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "estimate_recipe_times",
    Path(__file__).resolve().parents[1] / "scripts" / "estimate_recipe_times.py",
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def _recipe(rid, category, steps, n_ing=3):
    return {
        "id": rid,
        "name": f"Món {rid}",
        "category": category,
        "ingredients": [{"ingredient_id": str(i)} for i in range(n_ing)],
        "instructions": steps,
    }


def _catalogue(tmp_path):
    recipes = [
        _recipe("b", "man", ["Ướp thịt 20 phút.", "Kho 8-10 phút đến khi sệt."]),
        _recipe("a", "canh", ["Hầm xương 2 giờ.", "Nêm gia vị."]),
        _recipe("c", "rau", ["Xào rau."]),
    ]
    path = tmp_path / "cat.json"
    path.write_text(json.dumps({"recipes": recipes}), encoding="utf-8")
    return path


def _read(path):
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_draft_estimates(tmp_path):
    out = tmp_path / "draft.csv"
    assert mod.write_draft(_catalogue(tmp_path), out) == 3
    rows = {r["recipe_id"]: r for r in _read(out)}
    assert list(rows["b"]) == mod.COLUMNS
    assert rows["b"]["est_cook_min"] == "10"  # 8-10 -> trung điểm 9 -> làm tròn 5 -> 10
    assert rows["a"]["est_cook_min"] == "120"
    assert rows["c"]["est_cook_min"] == ""
    assert rows["b"]["est_prep_min"] == "35"  # 5+6+2=13, +20 ướp = 33 -> 35
    assert rows["a"]["est_difficulty"] == "kho" or rows["a"]["est_difficulty"] == "trung_binh"
    assert all(r["reviewer"] == "" and r["reviewed_prep_min"] == "" for r in rows.values())
    assert {r["batch"] for r in rows.values()} <= {"1", "2"}


def test_batch_quota():
    rows = [
        {
            "recipe_id": str(i),
            "category": "man",
            "ingredient_count": i,
            "step_count": 2,
            "_has_duration": True,
        }
        for i in range(30)
    ]
    mod.assign_batches(rows)
    assert sum(r["batch"] == 1 for r in rows) == 18
    assert rows[0]["batch"] == 1 and rows[29]["batch"] == 2


def test_draft_deterministic(tmp_path):
    cat = _catalogue(tmp_path)
    mod.write_draft(cat, tmp_path / "1.csv")
    mod.write_draft(cat, tmp_path / "2.csv")
    assert (tmp_path / "1.csv").read_bytes() == (tmp_path / "2.csv").read_bytes()


def _csv(tmp_path, rows):
    path = tmp_path / "rev.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=mod.COLUMNS, restval="")
        w.writeheader()
        w.writerows(rows)
    return path


def test_apply_nothing_for_unreviewed(tmp_path, capsys):
    path = _csv(tmp_path, [{"recipe_id": "a", "est_prep_min": "10", "reviewed_prep_min": "10"}])
    out = tmp_path / "o.jsonl"
    assert mod.main(["apply", "--csv", str(path), "--out", str(out)]) == 0
    assert not out.exists()
    assert "không ghi" in capsys.readouterr().out


def test_apply_emits_sorted_deterministic(tmp_path):
    rows = [
        {"recipe_id": "z", "reviewer": "An", "verified_at": "2026-10-01", "reviewed_prep_min": "15",
         "reviewed_difficulty": "de", "source_url": "https://example.org/z"},
        {"recipe_id": "m", "reviewer": "An", "verified_at": "2026-10-01",
         "reviewed_cook_min": "40", "source_url": "https://example.org/m"},
    ]  # fmt: skip
    path = _csv(tmp_path, rows)
    out = tmp_path / "o.jsonl"
    assert mod.main(["apply", "--csv", str(path), "--out", str(out)]) == 0
    first = out.read_bytes()
    mod.main(["apply", "--csv", str(path), "--out", str(out)])
    assert out.read_bytes() == first
    items = [json.loads(line) for line in first.decode().splitlines()]
    assert [i["recipe_id"] for i in items] == ["m", "z"]
    assert items[0] == {
        "recipe_id": "m",
        "cook_time_minutes": 40,
        "cook_time_source_url": "https://example.org/m",
        "cook_time_verified_at": "2026-10-01",
    }
    assert items[1]["difficulty_source_url"] == "https://example.org/z"
    assert "cook_time_minutes" not in items[1]


@pytest.mark.parametrize(
    "bad",
    [
        {"reviewed_prep_min": "0"},
        {"reviewed_prep_min": "601"},
        {"reviewed_cook_min": "abc"},
        {"reviewed_difficulty": "hard"},
        {"verified_at": "01/10/2026"},
        {"source_url": "project-review:An"},
    ],
)
def test_apply_rejects_bad_rows(tmp_path, capsys, bad):
    row = {
        "recipe_id": "bad-1",
        "reviewer": "An",
        "verified_at": "2026-10-01",
        "source_url": "https://example.org/bad",
    } | bad
    out = tmp_path / "o.jsonl"
    assert mod.main(["apply", "--csv", str(_csv(tmp_path, [row])), "--out", str(out)]) == 1
    assert "bad-1" in capsys.readouterr().err
    assert not out.exists()


def test_apply_skips_rows_without_source(tmp_path, capsys):
    row = {
        "recipe_id": "n",
        "reviewer": "An",
        "verified_at": "2026-10-01",
        "reviewed_cook_min": "9",
    }
    out = tmp_path / "o.jsonl"
    assert mod.main(["apply", "--csv", str(_csv(tmp_path, [row])), "--out", str(out)]) == 0
    assert not out.exists()
