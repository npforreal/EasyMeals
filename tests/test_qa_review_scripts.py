"""Kiểm thử cho scripts/export_review_batches.py và scripts/merge_review.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.export_review_batches import export_batches
from scripts.merge_review import validate_and_merge_reviews


def test_export_batches_creates_valid_json_batches(tmp_path):
    catalogue_file = tmp_path / "cat.json"
    cat_data = {
        "recipes": [
            {
                "id": f"rec-{i}",
                "name": f"Món {i}",
                "category": "man",
                "servings": 4,
                "ingredients": [{"ingredient_name": "Thịt", "quantity": "200", "unit": "g"}],
                "instructions": ["Nấu"],
            }
            for i in range(25)
        ]
    }
    catalogue_file.write_text(json.dumps(cat_data), encoding="utf-8")

    out_dir = tmp_path / "work"
    files = export_batches(catalogue_file, out_dir, batch_size=10)

    assert len(files) == 3
    assert files[0].name == "batch_001.json"
    assert files[1].name == "batch_002.json"
    assert files[2].name == "batch_003.json"

    batch1 = json.loads(files[0].read_text(encoding="utf-8"))
    assert batch1["recipes_count"] == 10
    assert len(batch1["recipes"]) == 10
    assert "instructions" in batch1


def test_merge_reviews_validates_and_merges_properly(tmp_path):
    catalogue_file = tmp_path / "cat.json"
    cat_data = {
        "recipes": [
            {"id": "rec-1", "name": "Món 1"},
            {"id": "rec-2", "name": "Món 2"},
        ]
    }
    catalogue_file.write_text(json.dumps(cat_data), encoding="utf-8")

    work_dir = tmp_path / "work"
    work_dir.mkdir()

    # Viết review_out_001.json
    out1 = {
        "results": [
            {"recipe_id": "rec-1", "status": "ok"},
            {
                "recipe_id": "rec-2",
                "status": "fix",
                "reason": "Lỗi chính tả",
                "suggested_fix": "Sửa",
            },
        ]
    }
    (work_dir / "review_out_001.json").write_text(json.dumps(out1), encoding="utf-8")

    out_file = tmp_path / "qa_review.jsonl"
    summary = validate_and_merge_reviews(catalogue_file, work_dir, out_file)

    assert summary["total_recipes"] == 2
    assert summary["ok_count"] == 1
    assert summary["fix_count"] == 1
    assert out_file.exists()


def test_merge_reviews_rejects_missing_or_duplicate_recipes(tmp_path):
    catalogue_file = tmp_path / "cat.json"
    cat_data = {
        "recipes": [
            {"id": "rec-1", "name": "Món 1"},
            {"id": "rec-2", "name": "Món 2"},
        ]
    }
    catalogue_file.write_text(json.dumps(cat_data), encoding="utf-8")

    work_dir = tmp_path / "work"
    work_dir.mkdir()

    # Thiếu rec-2
    out1 = {"results": [{"recipe_id": "rec-1", "status": "ok"}]}
    (work_dir / "review_out_001.json").write_text(json.dumps(out1), encoding="utf-8")

    out_file = tmp_path / "qa_review.jsonl"
    with pytest.raises(ValueError, match="Thiếu kết quả đánh giá"):
        validate_and_merge_reviews(catalogue_file, work_dir, out_file)


def test_qa_review_and_rejected_recipes_dataset_conformance():
    """Kiểm tra file data/open/qa_review.jsonl và rejected_recipes.jsonl tuân thủ đặc tả."""
    root = Path(__file__).resolve().parents[1]
    qa_file = root / "data" / "open" / "qa_review.jsonl"
    rejected_file = root / "data" / "open" / "rejected_recipes.jsonl"
    catalogue_file = root / "data" / "catalogue.json"

    assert qa_file.exists(), "Thiếu file data/open/qa_review.jsonl"
    assert rejected_file.exists(), "Thiếu file data/open/rejected_recipes.jsonl"
    assert catalogue_file.exists(), "Thiếu file data/catalogue.json"

    required_keys = {
        "recipe_id",
        "name",
        "reviewer_verdict",
        "verifier_verdict",
        "final_verdict",
        "notes",
        "reviewed_at",
    }

    qa_records = []
    with open(qa_file, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                assert required_keys.issubset(item.keys()), f"Thiếu trường bắt buộc trong {item}"
                assert item["reviewer_verdict"] in {"ok", "fix", "reject"}
                assert item["verifier_verdict"] in {"ok", "fix", "reject"}
                assert item["final_verdict"] in {"ok", "fix", "reject"}
                qa_records.append(item)

    assert len(qa_records) == 134, f"Kỳ vọng 134 kết quả review, thực tế {len(qa_records)}"

    # Kiểm tra log reject
    rejected_records = []
    with open(rejected_file, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rejected_records.append(json.loads(line))

    assert len(rejected_records) >= 1
    rejected_ids = {r["recipe_id"] for r in rejected_records}
    assert "37eabc3e-5630-53fc-b9e7-4ebd80c70f5b" in rejected_ids

    # Kiểm tra món bị reject không còn nằm trong catalogue.json
    with open(catalogue_file, encoding="utf-8") as f:
        cat = json.load(f)

    cat_recipe_ids = {r["id"] for r in cat.get("recipes", [])}
    for rej_id in rejected_ids:
        assert rej_id not in cat_recipe_ids, f"Món reject {rej_id} vẫn còn sót trong catalogue.json"
