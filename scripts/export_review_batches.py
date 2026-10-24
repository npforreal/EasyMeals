"""Xuất danh mục công thức thành các lô độc lập để soát chất lượng (QA review).

Mỗi lô khoảng 12–14 món, lưu trong thư mục tạm ngoài git (.review_work/).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOGUE = ROOT / "data" / "catalogue.json"
DEFAULT_WORK_DIR = ROOT / ".review_work"

CHECKLIST_GUIDE = {
    "rubric": {
        "ok": (
            "Món đạt chuẩn: tiếng Việt tự nhiên, định lượng thực tế hợp lý, các bước logic, "
            "an toàn thực phẩm, không trùng chép bản quyền."
        ),
        "fix": (
            "Món cần sửa nhỏ: lỗi chính tả, sai đơn vị rõ ràng (ví dụ 100ml hành lá), "
            "sót từ tiếng Anh đơn giản, thiếu bước gia vị nhỏ."
        ),
        "reject": (
            "Món không đạt: nghi vấn sao chép nguyên văn bản quyền từ blog/trang web, "
            "sai hỏng nghiêm trọng, mất an toàn thực phẩm không thể sửa nhỏ."
        ),
    },
    "criteria": [
        "Tiếng Việt tự nhiên, đúng chính tả, không sót tiếng Anh ngoài tên gốc trong ngoặc.",
        "Tên món phổ biến, đúng nhóm (man/rau/canh).",
        (
            "Định lượng hợp lý theo khẩu phần (thịt g, mắm ml, trứng cái, rau g; "
            "không ghi ml cho chất rắn)."
        ),
        (
            "Thứ tự bước hợp lý, thời gian/nhiệt độ thực tế, an toàn thực phẩm "
            "(nấu chín thịt/hải sản)."
        ),
        "Nguyên liệu dùng đúng trong các bước và ngược lại (không có nguyên liệu ma).",
        "Nhận diện dị ứng/an toàn (đậu phộng, hải sản, trứng, sữa, gluten).",
        (
            "Tính nguyên bản: không chép nguyên văn văn phong blog/quảng cáo. "
            "Nếu nghi ngờ, tìm 1-2 cụm từ và báo URL."
        ),
    ],
    "output_format": {
        "recipe_id": "UUID của món",
        "name": "Tên món",
        "status": "ok | fix | reject",
        "reason": "Lý do ngắn gọn nếu fix hoặc reject",
        "suggested_fix": "Chi tiết đề xuất sửa đổi nếu status = fix",
        "copyright_suspicion_url": "URL nếu nghi ngờ trùng nguyên văn (hoặc null)",
    },
}


def export_batches(
    catalogue_path: Path = DEFAULT_CATALOGUE,
    output_dir: Path = DEFAULT_WORK_DIR,
    batch_size: int = 13,
) -> list[Path]:
    if not catalogue_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file danh mục: {catalogue_path}")

    with open(catalogue_path, encoding="utf-8") as f:
        data = json.load(f)

    recipes = data.get("recipes", [])
    if not recipes:
        raise ValueError("Danh mục không có công thức nào!")

    output_dir.mkdir(parents=True, exist_ok=True)
    num_batches = math.ceil(len(recipes) / batch_size)
    batch_files: list[Path] = []

    for idx in range(num_batches):
        start = idx * batch_size
        batch_recipes = recipes[start : start + batch_size]
        batch_num = idx + 1
        batch_id = f"batch_{batch_num:03d}"
        file_path = output_dir / f"{batch_id}.json"

        batch_payload: dict[str, Any] = {
            "batch_id": batch_id,
            "batch_number": batch_num,
            "total_batches": num_batches,
            "recipes_count": len(batch_recipes),
            "instructions": CHECKLIST_GUIDE,
            "recipes": [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "category": r["category"],
                    "servings": r.get("servings", 4),
                    "ingredients": [
                        {
                            "name": i.get("ingredient_name") or i.get("name"),
                            "quantity": i.get("quantity"),
                            "unit": i.get("unit"),
                        }
                        for i in r.get("ingredients", [])
                    ],
                    "instructions": r.get("instructions", []),
                }
                for r in batch_recipes
            ],
        }

        with open(file_path, "w", encoding="utf-8") as out_f:
            json.dump(batch_payload, out_f, ensure_ascii=False, indent=2)
            out_f.write("\n")

        batch_files.append(file_path)

    return batch_files


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Xuất các lô công thức để subagent soát chất lượng."
    )
    parser.add_argument(
        "--catalogue",
        type=Path,
        default=DEFAULT_CATALOGUE,
        help="Đường dẫn data/catalogue.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_WORK_DIR,
        help="Thư mục xuất file lô review (.review_work)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=13,
        help="Số lượng món mỗi lô (mặc định: 13)",
    )
    args = parser.parse_args()
    files = export_batches(args.catalogue, args.output_dir, args.batch_size)
    print(f"-> Đã xuất thành công {len(files)} lô review vào thư mục: {args.output_dir}")


if __name__ == "__main__":
    main()
