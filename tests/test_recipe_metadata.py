"""Kiểm tra cobertura metadata công thức (E2-data / E3-data) trên catalogue.json.

Đảm bảo:
- Mỗi công thức có đầy đủ khoá metadata (prep_time / cook_time / difficulty /
  storage_tips cùng *_source_url và *_verified_at đi kèm), mặc dù giá trị có thể
  null / rỗng khi chưa có nguồn xác minh.
- Tính nhất quán của bằng chứng: giá trị có thì phải có nguồn + ngày xác minh;
  ngược lại nguồn / ngày có thì phải có giá trị. Không được để dữ liệu bị nuốt /
  swallow âm thầm.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE_PATH = ROOT / "data" / "catalogue.json"

METADATA_KEYS = (
    "prep_time_minutes",
    "prep_time_source_url",
    "prep_time_verified_at",
    "cook_time_minutes",
    "cook_time_source_url",
    "cook_time_verified_at",
    "difficulty",
    "difficulty_source_url",
    "difficulty_verified_at",
    "storage_tips",
    "storage_source_url",
    "storage_verified_at",
)

# (khoá giá trị, khoá nguồn, khoá ngày) — ba khoá này phải đi cùng nhau.
EVIDENCE_GROUPS = (
    ("prep_time_minutes", "prep_time_source_url", "prep_time_verified_at"),
    ("cook_time_minutes", "cook_time_source_url", "cook_time_verified_at"),
    ("difficulty", "difficulty_source_url", "difficulty_verified_at"),
    ("storage_tips", "storage_source_url", "storage_verified_at"),
)


def _load_catalogue() -> dict:
    with open(CATALOGUE_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_recipe_metadata_keys_present():
    data = _load_catalogue()
    recipes = data.get("recipes", [])
    assert recipes, "catalogue.json phải chứa ít nhất một công thức"
    for rec in recipes:
        rid = rec.get("id", "<unknown>")
        for key in METADATA_KEYS:
            assert key in rec, f"Công thức {rid} thiếu khoá metadata '{key}'"


def test_recipe_metadata_evidence_consistency():
    data = _load_catalogue()
    recipes = data.get("recipes", [])
    for rec in recipes:
        rid = rec.get("id", "<unknown>")
        for value_key, url_key, date_key in EVIDENCE_GROUPS:
            value = rec.get(value_key)
            has_evidence = bool(rec.get(url_key)) or bool(rec.get(date_key))
            has_value = value is not None and value != []
            # Giá trị có => phải có cả nguồn và ngày xác minh
            if has_value:
                assert rec.get(url_key) and rec.get(date_key), (
                    f"Công thức {rid} có {value_key} nhưng thiếu {url_key}/{date_key}"
                )
            # Nguồn/ngày có => phải có giá trị đi kèm (không được swallow bằng chứng)
            if has_evidence:
                assert has_value, (
                    f"Công thức {rid} có {url_key}/{date_key} nhưng thiếu giá trị {value_key}"
                )


def test_recipe_metadata_coverage_counts():
    """Ghi nhận cobertura thực tế (không bắt buộc > 0; không bịa dữ liệu)."""
    data = _load_catalogue()
    recipes = data.get("recipes", [])
    total = len(recipes)
    assert total > 0
    counts = {
        "prep_time_minutes": sum(1 for r in recipes if r.get("prep_time_minutes") is not None),
        "cook_time_minutes": sum(1 for r in recipes if r.get("cook_time_minutes") is not None),
        "difficulty": sum(1 for r in recipes if r.get("difficulty") is not None),
        "storage_tips": sum(1 for r in recipes if bool(r.get("storage_tips"))),
    }
    print(f"\n[metadata coverage] total_recipes={total} {counts}", file=sys.stderr)
