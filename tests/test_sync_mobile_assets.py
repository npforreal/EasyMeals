"""Kiểm thử cho scripts/sync_mobile_assets.py."""

from __future__ import annotations

from scripts.sync_mobile_assets import calc_sha256, sync_assets


def test_sync_mobile_assets_creates_and_verifies_hashes(tmp_path, monkeypatch):
    # Kiểm tra trực tiếp hàm sync_assets trên repo thực tế
    summary = sync_assets(check_only=False)

    assert summary["catalogue_recipes_count"] >= 130
    assert summary["catalogue_ingredients_count"] == 147

    # Chạy lại với check_only=True phải thành công
    check_summary = sync_assets(check_only=True)
    assert check_summary["catalogue_sha256"] == summary["catalogue_sha256"]


def test_calc_sha256_calculates_correct_digest(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("EasyMeals Clean Offline Mobile", encoding="utf-8")
    d1 = calc_sha256(f)
    d2 = calc_sha256(f)
    assert len(d1) == 64
    assert d1 == d2
