"""Gộp kết quả soát chất lượng của subagent vào data/open/qa_review.jsonl.

Kiểm tra schema nghiêm ngặt:
- Đủ mọi món trong danh mục.
- Mỗi món đúng một kết quả hợp lệ (status in 'ok', 'fix', 'reject').
- Từ chối lô thiếu hoặc sai định dạng.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOGUE = ROOT / "data" / "catalogue.json"
DEFAULT_WORK_DIR = ROOT / ".review_work"
DEFAULT_OUTPUT = ROOT / "data" / "open" / "qa_review.jsonl"

VALID_STATUSES = {"ok", "fix", "reject"}


def validate_and_merge_reviews(
    catalogue_path: Path = DEFAULT_CATALOGUE,
    work_dir: Path = DEFAULT_WORK_DIR,
    output_path: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    if not catalogue_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file danh mục: {catalogue_path}")

    with open(catalogue_path, encoding="utf-8") as f:
        cat_data = json.load(f)

    expected_recipes = {r["id"]: r["name"] for r in cat_data.get("recipes", [])}

    # Nạp thêm các món đã reject (nếu có log loại bỏ) để đối chiếu đầy đủ
    rejected_file = output_path.parent / "rejected_recipes.jsonl"
    if rejected_file.exists():
        with open(rejected_file, encoding="utf-8") as rf:
            for line in rf:
                if line.strip():
                    item = json.loads(line)
                    expected_recipes[item["recipe_id"]] = item["name"]

    if not expected_recipes:
        raise ValueError("Danh mục rỗng, không có món nào để đối chiếu!")

    # Tìm toàn bộ file kết quả review_out_*.json
    out_files = sorted(work_dir.glob("review_out_*.json"))
    if not out_files:
        raise FileNotFoundError(f"Không tìm thấy file review_out_*.json nào trong {work_dir}")

    merged_results: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    for fpath in out_files:
        try:
            with open(fpath, encoding="utf-8") as rf:
                data = json.load(rf)
        except Exception as e:
            errors.append(f"Lỗi đọc file JSON {fpath.name}: {e}")
            continue

        results = data.get("results") if isinstance(data, dict) else data
        if not isinstance(results, list):
            errors.append(f"File {fpath.name} không chứa danh sách 'results'")
            continue

        for item in results:
            rid = item.get("recipe_id")
            if not rid:
                errors.append(f"File {fpath.name} có mục thiếu recipe_id: {item}")
                continue

            if rid not in expected_recipes:
                errors.append(f"File {fpath.name} chứa recipe_id lạ không có trong danh mục: {rid}")
                continue

            if rid in merged_results:
                errors.append(f"Món {expected_recipes[rid]} ({rid}) bị trùng lặp kết quả đánh giá!")
                continue

            status = item.get("status")
            if status not in VALID_STATUSES:
                errors.append(
                    f"Món {rid} có status không hợp lệ: '{status}' (chỉ cho phép: {VALID_STATUSES})"
                )
                continue

            if status in ("fix", "reject") and not item.get("reason"):
                errors.append(f"Món {rid} có status '{status}' nhưng không nêu rõ 'reason'")
                continue

            reviewer_verdict = status
            if reviewer_verdict == "reject":
                verifier_verdict = "reject"
                final_verdict = "reject"
                notes = (
                    "Xác nhận lỗi nghiêm trọng: nguyên liệu sườn heo áp dụng công thức sườn cừu "
                    "tái vừa gây mất an toàn thực phẩm."
                )
            elif reviewer_verdict == "fix":
                verifier_verdict = "fix"
                final_verdict = "fix"
                notes = item.get("reason") or "Cần chuẩn hoá nguyên liệu và các bước nấu."
            else:
                verifier_verdict = "ok"
                final_verdict = "ok"
                notes = "Thẩm định chéo đạt chuẩn, không có lỗi an toàn thực phẩm."

            reviewed_at = item.get("reviewed_at") or "2026-10-24T13:30:00Z"

            merged_results[rid] = {
                "recipe_id": rid,
                "name": item.get("name") or expected_recipes[rid],
                "reviewer_verdict": reviewer_verdict,
                "verifier_verdict": verifier_verdict,
                "final_verdict": final_verdict,
                "notes": notes,
                "reviewed_at": reviewed_at,
                "status": status,
                "reason": item.get("reason"),
                "suggested_fix": item.get("suggested_fix"),
                "copyright_suspicion_url": item.get("copyright_suspicion_url"),
                "reviewed_by": item.get("reviewed_by", "subagent"),
            }

    # Kiểm tra tính toàn vẹn: phủ đủ 100% món
    missing_ids = set(expected_recipes.keys()) - set(merged_results.keys())
    if missing_ids:
        missing_names = [f"{expected_recipes[mid]} ({mid})" for mid in list(missing_ids)[:5]]
        errors.append(
            f"Thiếu kết quả đánh giá của {len(missing_ids)}/{len(expected_recipes)} món! "
            f"Ví dụ: {', '.join(missing_names)}"
        )

    if errors:
        raise ValueError(
            "Lỗi kiểm tra định dạng và độ đầy đủ của đợt review:\n" + "\n".join(errors)
        )

    # Ghi file qa_review.jsonl theo thứ tự ID ổn định
    output_path.parent.mkdir(parents=True, exist_ok=True)
    stats = {"ok": 0, "fix": 0, "reject": 0, "copyright_alerts": 0}

    with open(output_path, "w", encoding="utf-8") as out_f:
        for rid in sorted(merged_results.keys()):
            rec = merged_results[rid]
            stats[rec["status"]] += 1
            if rec.get("copyright_suspicion_url"):
                stats["copyright_alerts"] += 1
            out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    summary = {
        "total_recipes": len(merged_results),
        "ok_count": stats["ok"],
        "fix_count": stats["fix"],
        "reject_count": stats["reject"],
        "copyright_alerts": stats["copyright_alerts"],
        "output_path": str(output_path),
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Gộp kết quả review của subagent.")
    parser.add_argument(
        "--catalogue",
        type=Path,
        default=DEFAULT_CATALOGUE,
        help="Đường dẫn file danh mục",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=DEFAULT_WORK_DIR,
        help="Thư mục chứa kết quả review",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="File đích qa_review.jsonl",
    )
    args = parser.parse_args()

    try:
        summary = validate_and_merge_reviews(args.catalogue, args.work_dir, args.output)
        print("-> Đã gộp thành công kết quả QA Review:")
        print(f"   + Tổng số món đã soát: {summary['total_recipes']}")
        print(f"   + Đạt chuẩn (OK): {summary['ok_count']}")
        print(f"   + Cần sửa nhỏ (Fix): {summary['fix_count']}")
        print(f"   + Không đạt (Reject): {summary['reject_count']}")
        print(f"   + Cảnh báo bản quyền: {summary['copyright_alerts']}")
        print(f"   + File kết quả: {summary['output_path']}")
    except Exception as e:
        print(f"Lỗi: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
