"""Tests for scripts/export_catalogue.py (integrity and determinism)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from scripts.export_catalogue import export_catalogue, validate_catalogue_integrity


def test_export_catalogue_integrity_and_determinism():
    with tempfile.TemporaryDirectory() as tmpdir:
        out1 = Path(tmpdir) / "cat1.json"
        out2 = Path(tmpdir) / "cat2.json"

        bundle1 = export_catalogue(out1)
        bundle2 = export_catalogue(out2)

        # 1. Exact structure matching /api/catalogue
        assert "catalogue_version" in bundle1
        assert "etag" in bundle1
        assert len(bundle1["ingredients"]) >= 20
        assert len(bundle1["recipes"]) >= 4

        # 2. Determinism: byte-for-byte identical
        bytes1 = out1.read_bytes()
        bytes2 = out2.read_bytes()
        assert bytes1 == bytes2
        assert bundle1["etag"] == bundle2["etag"]


def test_validate_catalogue_integrity_rejects_duplicate_ingredients():
    bad_bundle = {
        "ingredients": [
            {"id": "ing-1", "name": "A", "category": "meat"},
            {"id": "ing-1", "name": "B", "category": "meat"},
        ],
        "recipes": [],
    }
    with pytest.raises(ValueError, match="Trùng lặp ID nguyên liệu"):
        validate_catalogue_integrity(bad_bundle)


def test_validate_catalogue_integrity_rejects_unknown_ingredient_ref():
    bad_bundle = {
        "ingredients": [
            {"id": "ing-1", "name": "A", "category": "meat"},
        ],
        "recipes": [
            {
                "id": "rec-1",
                "name": "Món lạ",
                "category": "man",
                "ingredients": [{"ingredient_id": "ing-ghost", "quantity": "100", "unit": "g"}],
            }
        ],
    }
    with pytest.raises(ValueError, match="tham chiếu nguyên liệu không tồn tại"):
        validate_catalogue_integrity(bad_bundle)


def test_validate_catalogue_integrity_rejects_invalid_unit():
    bad_bundle = {
        "ingredients": [
            {"id": "ing-1", "name": "A", "category": "meat"},
        ],
        "recipes": [
            {
                "id": "rec-1",
                "name": "Món lạ",
                "category": "man",
                "ingredients": [{"ingredient_id": "ing-1", "quantity": "100", "unit": "barrel"}],
            }
        ],
    }
    with pytest.raises(ValueError, match="đơn vị không được hỗ trợ"):
        validate_catalogue_integrity(bad_bundle)
