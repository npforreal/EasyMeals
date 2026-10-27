"""Tạo bảng rà soát thủ công (E2-data) cho thời gian chuẩn bị, thời gian nấu và độ khó.

Quy tắc dự án: không đưa số chưa kiểm chứng vào catalogue. Script này chỉ GỢI Ý (cột est_*)
để người rà soát có điểm xuất phát; giá trị chỉ vào overlay khi có người rà soát có tên
và ngày xác nhận.

Lệnh:
  draft  Đọc data/catalogue.json, ghi data/review/recipe_time_draft.csv.
  apply  Đọc CSV đã rà soát (--csv), ghi data/open/recipe_metadata.jsonl.

Quy tắc chọn batch=1 (~40 món rà soát trước): cân theo nhóm (18 man, 11 canh, 11 rau);
trong mỗi nhóm lấy món có ít nguyên liệu + ít bước nhất, ưu tiên món có thời lượng
ghi rõ trong lời văn. Điểm = số nguyên liệu + số bước (+4 nếu không có thời lượng rõ).
Các món còn lại là batch=2.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOGUE = ROOT / "data" / "catalogue.json"
DEFAULT_DRAFT = ROOT / "data" / "review" / "recipe_time_draft.csv"
DEFAULT_OVERLAY = ROOT / "data" / "open" / "recipe_metadata.jsonl"

COLUMNS = [
    "batch", "recipe_id", "name", "category", "step_count", "ingredient_count",
    "est_prep_min", "est_cook_min", "est_difficulty", "basis",
    "reviewed_prep_min", "reviewed_cook_min", "reviewed_difficulty",
    "reviewer", "verified_at", "note",
]  # fmt: skip
BATCH1_QUOTA = {"man": 18, "canh": 11, "rau": 11}
DIFFICULTIES = {"de", "trung_binh", "kho"}
MAX_MINUTES = 600
PASSIVE_PREP_LIMIT = 30

# Khoảng thời gian: "10 phút", "8-10 phút", "1,5 giờ", "1 giờ 30 phút" (giờ + phút tính riêng).
_NUM = r"(\d+(?:[.,]\d+)?)"
DURATION_RE = re.compile(_NUM + r"(?:\s*(?:-|–|đến)\s*" + _NUM + r")?\s*(phút|giờ|tiếng)")
PASSIVE_WORDS = ("ướp", "ngâm")
COOK_WORDS = ("hầm", "kho", "luộc", "nướng", "chiên", "xào", "om", "rim", "nấu", "đun", "sôi")


def _num(text: str) -> float:
    return float(text.replace(",", "."))


def _word_in(word: str, text: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", text) is not None


def find_durations(step: str) -> list[tuple[float, int]]:
    """Trả về [(số phút, vị trí bắt đầu)] cho mọi thời lượng trong một bước."""
    found = []
    for m in DURATION_RE.finditer(step):
        low = _num(m.group(1))
        value = (low + _num(m.group(2))) / 2 if m.group(2) else low
        if m.group(3) in ("giờ", "tiếng"):
            value *= 60
        found.append((value, m.start()))
    return found


def classify_steps(steps: list[str]) -> tuple[float, float]:
    """Tách thời lượng rõ ràng thành (phút nấu chủ động, phút ướp/ngâm thụ động)."""
    cook = passive = 0.0
    for step in steps:
        text = step.lower()
        for minutes, pos in find_durations(text):
            before = text[max(0, pos - 40) : pos]
            if any(w in before for w in PASSIVE_WORDS):
                passive += minutes
            elif any(_word_in(w, text) for w in COOK_WORDS):
                cook += minutes
    return cook, passive


def _round5(value: float) -> int:
    return max(5, int(round(value / 5.0)) * 5)


def estimate(recipe: dict) -> dict:
    steps = [s for s in recipe.get("instructions") or [] if isinstance(s, str)]
    n_steps, n_ing = len(steps), len(recipe.get("ingredients") or [])
    cook, passive = classify_steps(steps)

    prep = 5 + 2 * n_ing + n_steps
    basis = [f"sơ chế ước lượng 5 + 2×{n_ing} nguyên liệu + {n_steps} bước"]
    if passive:
        if passive <= PASSIVE_PREP_LIMIT:
            prep += passive
            basis.append(f"cộng {passive:.0f} phút ướp/ngâm")
        else:
            basis.append(f"có ướp/ngâm {passive:.0f} phút (không tính vào sơ chế)")
    cook_est = _round5(cook) if cook else None
    if cook:
        basis.append(f"nấu {cook:.0f} phút theo thời lượng ghi trong các bước")
    else:
        basis.append("không có thời lượng nấu rõ trong các bước")

    points = (
        (n_steps >= 6) + (n_ing >= 8) + ((cook_est or 0) >= 45) + (passive > PASSIVE_PREP_LIMIT)
    )
    difficulty = "de" if points == 0 else "kho" if points >= 3 else "trung_binh"
    return {
        "step_count": n_steps,
        "ingredient_count": n_ing,
        "est_prep_min": _round5(prep),
        "est_cook_min": cook_est,
        "est_difficulty": difficulty,
        "basis": "; ".join(basis),
        "_has_duration": bool(cook or passive),
    }


def assign_batches(rows: list[dict]) -> None:
    """Gán batch=1 cho các món đơn giản nhất mỗi nhóm theo quota, còn lại batch=2."""
    for row in rows:
        row["batch"] = 2
    for category, quota in BATCH1_QUOTA.items():
        pool = [r for r in rows if r["category"] == category]
        pool.sort(
            key=lambda r: (
                r["ingredient_count"] + r["step_count"] + (0 if r["_has_duration"] else 4),
                r["recipe_id"],
            )
        )
        for row in pool[:quota]:
            row["batch"] = 1


def build_draft_rows(catalogue: dict) -> list[dict]:
    rows = []
    for recipe in catalogue.get("recipes", []):
        est = estimate(recipe)
        rows.append(
            {
                "recipe_id": recipe["id"],
                "name": recipe.get("name", ""),
                "category": recipe.get("category", ""),
                **est,
            }
        )
    assign_batches(rows)
    rows.sort(key=lambda r: (r["batch"], r["category"], r["name"], r["recipe_id"]))
    return rows


def write_draft(catalogue_path: Path, out_path: Path) -> int:
    catalogue = json.loads(catalogue_path.read_text(encoding="utf-8"))
    rows = build_draft_rows(catalogue)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore", restval="")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("" if row.get(k) is None else row.get(k, "")) for k in COLUMNS})
    return len(rows)


def _parse_minutes(raw: str, label: str, where: str) -> int | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    if not re.fullmatch(r"\d+", raw) or not 1 <= int(raw) <= MAX_MINUTES:
        raise ValueError(f"{where}: {label}={raw!r} phải là số nguyên 1..{MAX_MINUTES}")
    return int(raw)


def build_overlay(csv_path: Path) -> list[dict]:
    out = []
    with csv_path.open(encoding="utf-8", newline="") as fh:
        for line_no, row in enumerate(csv.DictReader(fh), start=2):
            reviewer = (row.get("reviewer") or "").strip()
            verified_at = (row.get("verified_at") or "").strip()
            if not reviewer or not verified_at:
                continue  # chưa rà soát: bỏ qua, không bao giờ lấy est_*
            rid = (row.get("recipe_id") or "").strip()
            where = f"dòng {line_no} (recipe_id={rid or '?'})"
            if not rid:
                raise ValueError(f"{where}: thiếu recipe_id")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", verified_at):
                raise ValueError(f"{where}: verified_at={verified_at!r} phải theo YYYY-MM-DD")
            prep = _parse_minutes(row.get("reviewed_prep_min", ""), "reviewed_prep_min", where)
            cook = _parse_minutes(row.get("reviewed_cook_min", ""), "reviewed_cook_min", where)
            diff = (row.get("reviewed_difficulty") or "").strip()
            if diff and diff not in DIFFICULTIES:
                raise ValueError(
                    f"{where}: reviewed_difficulty={diff!r} không thuộc {sorted(DIFFICULTIES)}"
                )
            source = f"project-review:{reviewer}"
            item: dict = {"recipe_id": rid}
            for name, value in (
                ("prep_time_minutes", prep),
                ("cook_time_minutes", cook),
                ("difficulty", diff or None),
            ):
                if value is None:
                    continue
                stem = "difficulty" if name == "difficulty" else name.removesuffix("_minutes")
                item[name] = value
                item[f"{stem}_source_url"] = source
                item[f"{stem}_verified_at"] = verified_at
            if len(item) > 1:
                out.append(item)
    out.sort(key=lambda r: r["recipe_id"])
    return out


def write_overlay(csv_path: Path, out_path: Path) -> int:
    items = build_overlay(csv_path)
    if not items:
        print("Không có dòng nào đã rà soát (cần reviewer và verified_at); không ghi gì.")
        return 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(i, ensure_ascii=False, sort_keys=True) + "\n" for i in items)
    out_path.write_text(text, encoding="utf-8")
    print(f"Đã ghi {len(items)} dòng vào {out_path}")
    return len(items)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draft", help="ghi bảng rà soát CSV với gợi ý est_*")
    d.add_argument("--catalogue", type=Path, default=DEFAULT_CATALOGUE)
    d.add_argument("--out", type=Path, default=DEFAULT_DRAFT)
    a = sub.add_parser("apply", help="ghi overlay JSONL từ CSV đã rà soát")
    a.add_argument("--csv", type=Path, required=True)
    a.add_argument("--out", type=Path, default=DEFAULT_OVERLAY)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "draft":
            print(f"Đã ghi {write_draft(args.catalogue, args.out)} dòng vào {args.out}")
        else:
            write_overlay(args.csv, args.out)
    except ValueError as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
