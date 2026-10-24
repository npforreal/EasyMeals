"""Dịch công thức TheMealDB (tiếng Anh) sang tiếng Việt và kiểm tra không còn tiếng Anh.

Quy trình (bản dịch văn bản do mô hình thực hiện theo lô, phần còn lại là code xác định):

1. `export`: tạo các file lô `in_NNN.json` trong thư mục làm việc. Mỗi món gồm tên, vùng,
   các bước làm và tên nguyên liệu đã được dịch bằng từ điển `ingredient_translations.json`
   (để bản dịch cách làm dùng đúng tên nguyên liệu).
2. Người/mô hình dịch viết `out_NNN.json`: {source_id: {"name": ..., "instructions": [...]}}.
3. `merge`: kiểm tra từng món (không còn tiếng Anh, đủ số bước, đủ nguyên liệu), đổi định lượng
   sang g / ml / piece bằng bộ phân tích `parse_measure`, rồi ghi
   `data/open/themealdb_recipes_vi.jsonl`.
4. `check`: quét lại toàn bộ file kết quả; thoát mã 1 nếu còn tiếng Anh. Chạy trong test.

Dữ liệu gốc `recipes.jsonl` không bị sửa. `import_harvest.py` chỉ nạp dòng tiếng Việt.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = ROOT / "data" / "open" / "recipes.jsonl"
OUT_FILE = ROOT / "data" / "open" / "themealdb_recipes_vi.jsonl"
DICT_FILE = ROOT / "data" / "ingredient_translations.json"
WORK_DIR = ROOT / ".translation_work"

VALID_CATEGORIES = {"man", "rau", "canh"}
BATCH_SIZE = 12

VN_CHARS = set("àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ")

# Từ tiếng Anh không trùng với tiếng Việt không dấu; chỉ cần gặp một từ là coi như còn tiếng Anh.
EN_WORDS = frozenset(
    """
    the and with until into then add minutes minute hours hour heat over from bowl pan oven cook
    cooked cooking stir mix serve remove place cover pour drain cut chop chopped slice sliced
    fry fried bake baked boil boiled simmer season seasoning taste for your you are is was be
    of in on at by or until about each all well when while after before until large small
    medium half whole cup cups tablespoon tablespoons teaspoon teaspoons ounces pounds
    salt pepper oil water butter cheese onion onions garlic chicken beef pork rice flour sugar
    egg eggs milk cream sauce tomato tomatoes potato potatoes carrot carrots lemon juice
    mixture mixing together gently until golden brown dough batter meat fish vegetables
    preheat degrees fahrenheit celsius fan gas mark knife board pot saucepan skillet tin tray
    """.split()
)

# Từ mượn được phép giữ nguyên dù trùng danh sách trên (để trống; thêm khi thật sự cần).
ALLOWED_LOANWORDS: frozenset[str] = frozenset()

_FRACTIONS = {"½": "1/2", "¼": "1/4", "¾": "3/4", "⅓": "1/3", "⅔": "2/3", "⅛": "1/8"}

_WEIGHT_G = {
    "g": Decimal(1),
    "gr": Decimal(1),
    "gram": Decimal(1),
    "grams": Decimal(1),
    "kg": Decimal(1000),
    "kilo": Decimal(1000),
    "oz": Decimal("28.35"),
    "ounce": Decimal("28.35"),
    "ounces": Decimal("28.35"),
    "lb": Decimal("453.6"),
    "lbs": Decimal("453.6"),
    "pound": Decimal("453.6"),
    "pounds": Decimal("453.6"),
}
_VOLUME_ML = {
    "ml": Decimal(1),
    "cl": Decimal(10),
    "dl": Decimal(100),
    "l": Decimal(1000),
    "litre": Decimal(1000),
    "litres": Decimal(1000),
    "liter": Decimal(1000),
    "liters": Decimal(1000),
    "cup": Decimal(240),
    "cups": Decimal(240),
    "tbsp": Decimal(15),
    "tbs": Decimal(15),
    "tblsp": Decimal(15),
    "tbl": Decimal(15),
    "tablespoon": Decimal(15),
    "tablespoons": Decimal(15),
    "tsp": Decimal(5),
    "teaspoon": Decimal(5),
    "teaspoons": Decimal(5),
    "dessertspoon": Decimal(10),
    "pint": Decimal(473),
    "pints": Decimal(473),
    "quart": Decimal(946),
    "quarts": Decimal(946),
}
_PIECE_WORDS = frozenset(
    """
    large medium small whole clove cloves slice slices piece pieces bunch bunches sprig sprigs
    stick sticks can cans tin tins fillet fillets head heads leaf leaves handful handfuls pack
    packs packet packets bag bags stalk stalks rasher rashers knob knobs ball balls sheet sheets
    jar jars bottle bottles cube cubes strip strips bulb bulbs
    """.split()
)
_SMALL_G = ("pinch",)
_SMALL_ML = ("dash", "splash", "drizzle", "squeeze", "drop", "drops")

_QTY_RE = re.compile(r"^(\d+\s+\d+/\d+|\d+/\d+|\d+(?:[.,]\d+)?)\s*([a-z]*)")


def _to_decimal(raw: str) -> Decimal | None:
    raw = raw.strip().replace(",", ".")
    try:
        if " " in raw and "/" in raw:
            whole, frac = raw.split(None, 1)
            num, den = frac.split("/")
            return Decimal(whole) + Decimal(num) / Decimal(den)
        if "/" in raw:
            num, den = raw.split("/")
            return Decimal(num) / Decimal(den)
        return Decimal(raw)
    except Exception:
        return None


def _round(value: Decimal) -> Decimal:
    rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return rounded.quantize(Decimal(1)) if rounded == rounded.to_integral() else rounded


def parse_measure(measure: str | None) -> tuple[Decimal | None, str | None]:
    """Đổi chuỗi định lượng tiếng Anh sang (so luong, don vi g/ml/piece)."""
    if not measure:
        return None, None
    text = measure.strip().lower()
    for ch, rep in _FRACTIONS.items():
        text = text.replace(ch, f" {rep} ")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None, None

    for word in _SMALL_G:
        if word in text and not re.match(r"^\d", text):
            return Decimal(1), "g"
    if not re.match(r"^\d", text):
        for word in _SMALL_ML:
            if word in text:
                return Decimal(5), "ml"
        return None, None

    # "2-3 cloves" -> lấy cận trên cho an toàn tồn kho; "2 x 400g" không hỗ trợ.
    text = re.sub(r"^(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)", r"\2", text)
    m = _QTY_RE.match(text)
    if not m:
        return None, None
    qty = _to_decimal(m.group(1))
    if qty is None or qty <= 0:
        return None, None
    word = m.group(2)
    if word == "fl" and "oz" in text[m.end() :]:
        return _round(qty * Decimal(30)), "ml"

    if word in _WEIGHT_G:
        return _round(qty * _WEIGHT_G[word]), "g"
    if word in _VOLUME_ML:
        return _round(qty * _VOLUME_ML[word]), "ml"
    if word == "" or word in _PIECE_WORDS or word.isalpha():
        # Số đứng riêng hoặc kèm danh từ đếm được (3 eggs, 2 large) -> cái/quả
        return _round(qty), "piece"
    return None, None


def format_measure_vi(qty: Decimal | None, unit: str | None) -> str:
    """Chuỗi định lượng tiếng Việt cho trường `measure`."""
    if qty is None or unit is None:
        return "vừa đủ"
    unit_vi = {"g": "g", "ml": "ml", "piece": "cái"}[unit]
    return f"{qty:f} {unit_vi}".replace(".0 ", " ")


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z]+", text.lower())


def _strip_parens(text: str) -> str:
    """Loại bỏ toàn bộ nội dung trong ngoặc đơn (bao gồm ngoặc lồng nhau)."""
    result = []
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            if depth > 0:
                depth -= 1
        elif depth == 0:
            result.append(ch)
    return "".join(result)


def find_english(text: str) -> list[str]:
    """Trả về danh sách dấu hiệu tiếng Anh trong một đoạn văn (rỗng nếu sạch).

    Nội dung trong ngoặc đơn (tên gốc món ăn) được bỏ qua vì đây là chỗ duy nhất
    được phép giữ tiếng Anh/nước ngoài (quy tắc dịch #4).
    """
    problems: list[str] = []
    text_check = _strip_parens(text)
    hits = [w for w in _words(text_check) if w in EN_WORDS and w not in ALLOWED_LOANWORDS]
    if hits:
        problems.append("từ tiếng Anh: " + ", ".join(sorted(set(hits))[:6]))
    for sentence in re.split(r"[.!?;\n]+", text_check):
        ws = _words(sentence)
        if len(ws) >= 6 and not any(c in VN_CHARS for c in sentence.lower()):
            problems.append("câu dài không có dấu tiếng Việt: " + sentence.strip()[:60])
            break
    return problems


def _norm(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    out = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return " ".join(out.replace("đ", "d").split())


def _load_dict() -> dict[str, str]:
    with DICT_FILE.open(encoding="utf-8") as fh:
        return {_norm(k): v for k, v in json.load(fh).items()}


def load_pending(raw_file: Path = RAW_FILE) -> list[dict[str, Any]]:
    rows = []
    with raw_file.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("source") == "themealdb" and row.get("dish_category") in VALID_CATEGORIES:
                rows.append(row)
    return rows


def vi_ingredient_name(name: str, mapping: dict[str, str]) -> str | None:
    return mapping.get(_norm(name))


def cmd_export(args: argparse.Namespace) -> int:
    mapping = _load_dict()
    rows = load_pending()
    WORK_DIR.mkdir(exist_ok=True)
    done: set[str] = set()
    for p in WORK_DIR.glob("out_*.json"):
        done.update(json.loads(p.read_text(encoding="utf-8")).keys())
    todo = [r for r in rows if r["source_id"] not in done]
    for old in WORK_DIR.glob("in_*.json"):
        old.unlink()
    n = 0
    for i in range(0, len(todo), BATCH_SIZE):
        chunk = todo[i : i + BATCH_SIZE]
        payload = [
            {
                "source_id": r["source_id"],
                "name": r["name"],
                "area": r.get("area"),
                "instructions": r.get("instructions") or [],
                "ingredients_vi": [
                    vi_ingredient_name(x["name"], mapping) or x["name"] for x in r["ingredients"]
                ],
            }
            for r in chunk
        ]
        (WORK_DIR / f"in_{n:03d}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        n += 1
    print(f"{len(rows)} món TheMealDB hợp lệ, đã dịch {len(done)}, còn {len(todo)} -> {n} lô.")
    return 0


def build_row(
    raw: dict[str, Any], tr: dict[str, Any], mapping: dict[str, str]
) -> tuple[dict, list[str]]:
    problems: list[str] = []
    name = (tr.get("name") or "").strip()
    steps = [s.strip() for s in tr.get("instructions") or [] if s and s.strip()]
    if not name:
        problems.append("thiếu tên")
    if not steps:
        problems.append("thiếu cách làm")
    raw_steps = raw.get("instructions") or []
    if raw_steps and len(steps) < max(1, len(raw_steps) // 2):
        problems.append(f"thiếu bước ({len(steps)}/{len(raw_steps)})")
    for field, text in [("tên", name), *[(f"bước {i + 1}", s) for i, s in enumerate(steps)]]:
        for pb in find_english(text):
            problems.append(f"{field}: {pb}")

    ingredients = []
    for ing in raw["ingredients"]:
        vi = vi_ingredient_name(ing["name"], mapping)
        if not vi:
            problems.append(f"nguyên liệu chưa có bản dịch: {ing['name']}")
            continue
        for pb in find_english(vi):
            problems.append(f"nguyên liệu '{vi}': {pb}")
        qty, unit = parse_measure(ing.get("measure"))
        ingredients.append(
            {
                "name": vi,
                "normalized_name": _norm(vi),
                "measure": format_measure_vi(qty, unit),
                "quantity": None if qty is None else f"{qty:f}",
                "unit": unit,
            }
        )
    row = {
        "source_id": raw["source_id"],
        "name": name,
        "normalized_name": _norm(name),
        "aliases": [],
        "dish_category": raw["dish_category"],
        "servings": 4,
        "area": raw.get("area"),
        "instructions": steps,
        "ingredients": ingredients,
        "language": "vi",
        "source": "themealdb_vi",
        "source_url": raw.get("source_url"),
        "license": raw.get("license"),
        "fetched_at": raw.get("fetched_at"),
        "translation": "llm-vi; kiểm tra tự động bằng scripts/translate_recipes.py",
    }
    return row, problems


def cmd_merge(args: argparse.Namespace) -> int:
    mapping = _load_dict()
    raw_by_id = {r["source_id"]: r for r in load_pending()}
    existing: dict[str, dict[str, Any]] = {}
    if OUT_FILE.exists():
        for line in OUT_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                existing[row["source_id"]] = row

    accepted = rejected = 0
    rejected_ids: dict[str, list[str]] = {}
    for p in sorted(WORK_DIR.glob("out_*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        for sid, tr in data.items():
            raw = raw_by_id.get(sid)
            if raw is None:
                rejected_ids[sid] = ["source_id không tồn tại"]
                rejected += 1
                continue
            row, problems = build_row(raw, tr, mapping)
            if problems:
                rejected_ids[sid] = problems
                rejected += 1
                continue
            existing[sid] = row
            accepted += 1
    ordered = [existing[k] for k in sorted(existing)]
    OUT_FILE.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in ordered), encoding="utf-8"
    )
    print(f"Nhận {accepted}, từ chối {rejected}; tổng đã có {len(ordered)}/{len(raw_by_id)}.")
    for sid, pbs in list(rejected_ids.items())[:40]:
        print(f"  ✗ {sid}: " + " | ".join(pbs[:3]))
    return 0 if rejected == 0 else 1


def check_file(path: Path = OUT_FILE) -> list[str]:
    """Quét file kết quả; trả danh sách lỗi (rỗng = sạch)."""
    errors: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        sid = row["source_id"]
        texts = [("tên", row["name"])]
        texts += [(f"bước {i + 1}", s) for i, s in enumerate(row["instructions"])]
        texts += [("nguyên liệu", i["name"]) for i in row["ingredients"]]
        texts += [("định lượng", i["measure"]) for i in row["ingredients"]]
        for field, text in texts:
            for pb in find_english(text):
                errors.append(f"{sid} {field}: {pb}")
    return errors


def cmd_check(args: argparse.Namespace) -> int:
    if not OUT_FILE.exists():
        print("Chưa có file kết quả.")
        return 1
    errors = check_file()
    total = len(load_pending())
    done = sum(1 for _ in OUT_FILE.read_text(encoding="utf-8").splitlines() if _.strip())
    print(f"Đã dịch {done}/{total} món; lỗi tiếng Anh: {len(errors)}")
    for e in errors[:40]:
        print("  ✗", e)
    return 0 if not errors and done == total else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("export").set_defaults(fn=cmd_export)
    sub.add_parser("merge").set_defaults(fn=cmd_merge)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
