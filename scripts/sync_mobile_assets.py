"""Đồng bộ assets từ kho dữ liệu chuẩn vào các dự án native mobile (Android & iOS).

Nguồn:
- data/catalogue.json
- tests/fixtures/engine_test_cases.json

Đích:
- mobile/android/app/src/main/assets/catalogue.json
- mobile/android/app/src/test/resources/engine_test_cases.json
- mobile/ios/EasyMeals/Resources/catalogue.json
- mobile/ios/EasyMealsTests/Resources/engine_test_cases.json

Kiểm tra:
- Toàn vẹn dữ liệu
- Tính toán SHA-256 hash và xác thực sau khi sao chép
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SRC_CATALOGUE = ROOT / "data" / "catalogue.json"
SRC_ENGINE_TESTS = ROOT / "tests" / "fixtures" / "engine_test_cases.json"

ANDROID_ASSETS_DIR = ROOT / "mobile" / "android" / "app" / "src" / "main" / "assets"
ANDROID_TEST_RESOURCES_DIR = ROOT / "mobile" / "android" / "app" / "src" / "test" / "resources"

IOS_RESOURCES_DIR = ROOT / "mobile" / "ios" / "EasyMeals" / "Resources"
IOS_TEST_RESOURCES_DIR = ROOT / "mobile" / "ios" / "EasyMealsTests" / "Resources"


def calc_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def validate_catalogue_contract(cat_data: dict) -> None:
    required_keys = ["catalogue_version", "etag", "ingredients", "recipes"]
    for k in required_keys:
        if k not in cat_data or cat_data[k] is None:
            raise ValueError(f"Catalogue JSON vi phạm hợp đồng: thiếu khoá '{k}'")

    if not isinstance(cat_data["ingredients"], list) or not cat_data["ingredients"]:
        raise ValueError("Catalogue JSON vi phạm hợp đồng: 'ingredients' phải là mảng không rỗng")

    if not isinstance(cat_data["recipes"], list) or not cat_data["recipes"]:
        raise ValueError("Catalogue JSON vi phạm hợp đồng: 'recipes' phải là mảng không rỗng")

    for ing in cat_data["ingredients"]:
        if not ing.get("id") or not ing.get("name") or not ing.get("normalized_name"):
            raise ValueError(f"Nguyên liệu vi phạm hợp đồng thiếu id/name/normalized_name: {ing}")

    for rec in cat_data["recipes"]:
        if (
            not rec.get("id")
            or not rec.get("name")
            or not rec.get("category")
            or not rec.get("ingredients")
        ):
            raise ValueError(f"Món ăn vi phạm hợp đồng thiếu id/name/category/ingredients: {rec}")


def sync_assets(check_only: bool = False) -> dict[str, str]:
    if not SRC_CATALOGUE.exists():
        raise FileNotFoundError(f"Không tìm thấy file nguồn catalogue: {SRC_CATALOGUE}")
    if not SRC_ENGINE_TESTS.exists():
        raise FileNotFoundError(f"Không tìm thấy file nguồn test cases: {SRC_ENGINE_TESTS}")

    # Xác thực JSON hợp lệ và đúng hợp đồng
    with open(SRC_CATALOGUE, encoding="utf-8") as f:
        cat_data = json.load(f)
    validate_catalogue_contract(cat_data)

    with open(SRC_ENGINE_TESTS, encoding="utf-8") as f:
        test_data = json.load(f)

    cat_hash = calc_sha256(SRC_CATALOGUE)
    test_hash = calc_sha256(SRC_ENGINE_TESTS)

    targets = [
        (SRC_CATALOGUE, ANDROID_ASSETS_DIR / "catalogue.json", cat_hash),
        (SRC_CATALOGUE, ANDROID_TEST_RESOURCES_DIR / "catalogue.json", cat_hash),
        (SRC_ENGINE_TESTS, ANDROID_TEST_RESOURCES_DIR / "engine_test_cases.json", test_hash),
        (SRC_CATALOGUE, IOS_RESOURCES_DIR / "catalogue.json", cat_hash),
        (SRC_ENGINE_TESTS, IOS_TEST_RESOURCES_DIR / "engine_test_cases.json", test_hash),
    ]

    mismatches = []
    for src, dst, expected_hash in targets:
        if check_only:
            if not dst.exists() or calc_sha256(dst) != expected_hash:
                mismatches.append(str(dst))
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            actual_hash = calc_sha256(dst)
            if actual_hash != expected_hash:
                raise ValueError(f"Hash không khớp sau khi sao chép {dst}!")

    if check_only and mismatches:
        msg = f"Có {len(mismatches)} file asset mobile bị lệch hoặc chưa đồng bộ: {mismatches}"
        raise ValueError(msg)

    return {
        "catalogue_recipes_count": len(cat_data.get("recipes", [])),
        "catalogue_ingredients_count": len(cat_data.get("ingredients", [])),
        "catalogue_sha256": cat_hash,
        "engine_cases_count": len(test_data.get("meal_plans", [])),
        "engine_cases_sha256": test_hash,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Đồng bộ assets vào dự án mobile native.")
    parser.add_argument(
        "--check", action="store_true", help="Chỉ kiểm tra tính đồng bộ, không ghi file"
    )
    args = parser.parse_args()

    try:
        info = sync_assets(check_only=args.check)
        mode = "Kiểm tra" if args.check else "Đồng bộ"
        print(f"-> {mode} assets mobile THÀNH CÔNG:")
        r_cnt = info["catalogue_recipes_count"]
        i_cnt = info["catalogue_ingredients_count"]
        print(f"   + Danh mục: {r_cnt} món, {i_cnt} nguyên liệu")
        print(f"   + Hash catalogue: {info['catalogue_sha256'][:16]}...")
        print(f"   + Hash engine fixtures: {info['engine_cases_sha256'][:16]}...")
    except Exception as e:
        print(f"Lỗi: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
