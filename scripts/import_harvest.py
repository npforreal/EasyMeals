"""Import du lieu danh muc mo rong (tieng Viet) vao Supabase.

Chay MAC DINH o che do dry-run (chi bao cao, khong ghi DB). Chi ghi DB khi
duoc truyen --apply VA duoc nguoi dung cap phep (khong cham du lieu
production voi phep).

Dau vao: data/open/ingredients_vi.jsonl, vietnamese_recipes.jsonl,
         va international_recipes_vi.jsonl.

Dau ra: insert/update vao Supabase bang ingredients, ingredient_aliases,
        recipes, recipe_ingredients.
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from supabase import create_client

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DATA_DIR = ROOT / "data" / "open"
INGREDIENTS_FILE = DATA_DIR / "ingredients_vi.jsonl"
RECIPES_FILES = [
    DATA_DIR / "vietnamese_recipes.jsonl",
    DATA_DIR / "international_recipes_vi.jsonl",
]

NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # DNS namespace UUID

VALID_UNITS = {"g", "kg", "ml", "l", "piece"}
VALID_CATEGORIES = {"man", "rau", "canh"}

# Anh -> Viet (canh chinh, khop voi catalogue VN co san trong migration seed).
# Item khong co trong dict giu ten tieng Anh va danh dau can dich.
MAP_INGREDIENT: dict[str, str] = {
    "chicken": "Thịt gà",
    "pork": "Thịt heo",
    "beef": "Thịt bò",
    "salmon": "Cá hồi",
    "garlic": "Tỏi",
    "onion": "Hành tây",
    "red onion": "Hành tím",
    "ginger": "Gừng",
    "lime": "Chanh",
    "lemon": "Chanh",
    "egg": "Trứng gà",
    "eggs": "Trứng gà",
    "tomato": "Cà chua",
    "tomatoes": "Cà chua",
    "potato": "Khoai tây",
    "potatoes": "Khoai tây",
    "carrot": "Cà rốt",
    "carrots": "Cà rốt",
    "cabbage": "Bắp cải",
    "broccoli": "Cải xanh",
    "spinach": "Rau cải",
    "mushroom": "Nấm",
    "mushrooms": "Nấm",
    "scallions": "Hành lá",
    "green onion": "Hành lá",
    "cilantro": "Ngò rí",
    "coriander": "Ngò rí",
    "parsley": "Ngùi",
    "basil": "Húng quế",
    "mint": "Bạc hà",
    "salt": "Muối",
    "pepper": "Tiêu",
    "black pepper": "Tiêu đen",
    "sugar": "Đường",
    "oil": "Dầu ăn",
    "olive oil": "Dầu oliu",
    "vegetable oil": "Dầu thực vật",
    "butter": "Bơ",
    "milk": "Sữa",
    "rice": "Gạo",
    "noodle": "Mì",
    "fish sauce": "Nước mắm",
    "soy sauce": "Nước tương",
    "vinegar": "Giấm",
    "rice vinegar": "Giấm gạo",
    "coconut milk": "Nước cốt dừa",
    "curry paste": "Hộp cà ri",
    "fish fillet": "Filé cá",
    "shrimp": "Tôm",
    "prawn": "Tôm",
    "tofu": "Đậu hũ",
    "black beans": "Đậu đen",
    "chickpeas": "Đậu giữa",
    "lentils": "Đậu lente",
    "corn": "Ngô",
    "peanut": "Đậu phộng",
    "peanut butter": "Bơ đậu phộng",
    "almond": "Hạt điều",
    "walnut": "Hạt óc chó",
    "sesame": "Hạt sesame",
    "banana": "Chuối",
    "apple": "Táo",
    "orange": "Cam",
    "pineapple": "Dứa",
    "mango": "Xoài",
    "papaya": "Đủ",
    "avocado": "Bơ",
    "cucumber": "Dưa leo",
    "bell pepper": "Ớt chuông",
    "chilli": "Ớt",
    "chili": "Ớt",
    "green chilli": "Ớt xanh",
    "red chilli": "Ớt đỏ",
}


def normalize(text: str | None) -> str:
    """Chuoi tieng Anh khong dau, viet thuong, bo dau cai tien de khop ten."""
    if not text:
        return ""
    text = text.strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    # bo dau phu, ghep khoang trang
    import re

    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def gen_uuid(source_id: str | None, fallback_name: str | None = None) -> str:
    """Sinh UUID5 deterministic tu source_id (idempotent neu chay lai)."""
    seed = (source_id or fallback_name or "").strip()
    if not seed:
        seed = "empty"
    return str(uuid.uuid5(NAMESPACE, seed))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


TRANSLATIONS_FILE = ROOT / "data" / "ingredient_translations.json"


def load_translations() -> dict[str, str]:
    mapping: dict[str, str] = dict(MAP_INGREDIENT)
    if TRANSLATIONS_FILE.exists():
        try:
            with TRANSLATIONS_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    mapping[normalize(k)] = v
        except Exception:
            pass
    return mapping


ACTIVE_TRANSLATIONS = load_translations()


def translate_ingredient(name: str, normalized_name: str) -> tuple[str, bool]:
    """Tra ve (ten_viet, can_dich)."""
    # Neu da la tieng Viet (co dau hoac chu đ/Đ) thi khong can dich nua
    vn_chars = "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđĐ"
    if any(c in vn_chars for c in name):
        return name.strip(), False

    key = normalize(name) or normalize(normalized_name)
    vi = ACTIVE_TRANSLATIONS.get(key)
    if vi:
        return vi.strip(), False
    return name, True


def parse_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        return None


def build_client(apply: bool) -> Any:
    if not apply:
        return None
    import os

    from dotenv import dotenv_values

    env_vars = {**dotenv_values(".env"), **os.environ}
    url = env_vars.get("SUPABASE_URL")
    key = (
        env_vars.get("SUPABASE_SERVICE_ROLE_KEY")
        or env_vars.get("SUPABASE_ANON_KEY")
        or env_vars.get("SUPABASE_KEY")
    )
    if not url or not key or url.startswith("https://your-project"):
        print(
            "Loi: can SUPABASE_URL va SUPABASE_SERVICE_ROLE_KEY/ANON_KEY de --apply.",
            file=sys.stderr,
        )
        sys.exit(2)
    return create_client(url, key)


def import_ingredients(client: Any | None, apply: bool) -> dict[str, Any]:
    """Nhap danh sach nguyen lieu. Tra ve bao cao."""
    rows = load_jsonl(INGREDIENTS_FILE)
    inserted = 0
    skipped = 0
    need_translate = 0
    reports: list[str] = []
    index: dict[str, dict[str, Any]] = {}  # normalized_name -> row

    for row in rows:
        name = row.get("name") or ""
        normalized = row.get("normalized_name") or normalize(name)
        source_id = row.get("source_id")
        vi_name, need = translate_ingredient(name, normalized)
        if need:
            need_translate += 1
            reports.append(f"CAN DICH: '{name}' (source_id={source_id})")

        vi_normalized = normalize(vi_name) or normalized
        uid = gen_uuid(source_id, vi_normalized)
        # Luu y: bang ingredients khong co cot source_id (xem full_schema.sql);
        # source_id chi duoc giu trong data/open/*.jsonl de truy nguon goc.
        payload = {
            "id": uid,
            "name": vi_name,
            "normalized_name": vi_normalized,
            "category": row.get("category"),
        }
        # Only carry editorial allergen facts when the source explicitly provides evidence.
        if row.get("allergen_verification_status") in {"incomplete", "verified"}:
            payload.update(
                allergens=row.get("allergens") or [],
                allergen_verification_status=row["allergen_verification_status"],
                allergen_source_url=row.get("allergen_source_url"),
                allergen_verified_at=row.get("allergen_verified_at"),
            )
        index[normalized] = {"id": uid, "name": vi_name, "source_id": source_id}
        index[vi_normalized] = {"id": uid, "name": vi_name, "source_id": source_id}
        if apply:
            assert client is not None
            try:
                client.table("ingredients").upsert(payload, on_conflict="normalized_name").execute()
                # Dong thoi luu ten tieng Anh vao ingredient_aliases de tim kiem da ngon ngu
                if name.strip().lower() != vi_name.strip().lower():
                    alias_payload = {
                        "ingredient_id": uid,
                        "alias": name.strip(),
                        "normalized_alias": normalize(name),
                    }
                    try:
                        client.table("ingredient_aliases").upsert(
                            alias_payload, on_conflict="normalized_alias"
                        ).execute()
                    except Exception:
                        pass
                inserted += 1
            except Exception as exc:  # noqa: BLE001 - bao cao loi va tiep tuc
                skipped += 1
                reports.append(f"LOI insert ingredient '{name}': {exc}")
        else:
            inserted += 1

    return {
        "total": len(rows),
        "inserted": inserted,
        "skipped": skipped,
        "need_translate": need_translate,
        "index": index,
        "reports": reports,
    }


def import_recipes(client: Any | None, apply: bool, ing_index: dict[str, Any]) -> dict[str, Any]:
    """Nhap cong thuc co dish_category hop le. Tra ve bao cao."""
    rows = []
    for rf in RECIPES_FILES:
        if rf.exists():
            rows.extend(load_jsonl(rf))
    inserted = 0
    skipped_no_cat = 0
    skipped_no_ing = 0
    reports: list[str] = []

    for row in rows:
        category = row.get("dish_category")
        if category not in VALID_CATEGORIES:
            skipped_no_cat += 1
            continue

        name = row.get("name") or ""
        source_id = row.get("source_id")
        instructions = row.get("instructions") or []
        servings = row.get("servings") or 4
        try:
            servings = int(servings)
        except (ValueError, TypeError):
            servings = 4

        # Nguyen lieu cua cong thuc
        ings = row.get("ingredients") or []
        valid_ings = []
        for ing in ings:
            ing_name = ing.get("name") or ""
            ing_norm = normalize(ing_name) or normalize(ing.get("normalized_name") or "")
            match = ing_index.get(ing_norm)
            if not match:
                reports.append(f"KHONG KHOP nguyen lieu '{ing_name}' cho recipe '{name}'")
                continue
            qty = parse_decimal(ing.get("quantity"))
            unit = (ing.get("unit") or "").strip()
            if qty is None or unit not in VALID_UNITS:
                # bo qua dong nguyen lieu khong hop tro, bao cao
                reports.append(
                    f"BO qua nguyen lieu '{ing_name}' (qty={qty}, unit={unit}) cho '{name}'"
                )
                continue
            valid_ings.append((ing, match, qty, unit))

        # Mon khong co nguyen lieu hop le -> khong nap (yeu cau §2.2)
        if not valid_ings:
            skipped_no_ing += 1
            continue

        uid = gen_uuid(source_id, name)
        payload = {
            "id": uid,
            "name": name,
            "category": category,
            "instructions": instructions,
            "servings": servings,
        }
        # Preserve only explicitly sourced editorial labels; never infer from names/ingredients.
        for field in (
            "dietary_status",
            "dietary_source_url",
            "dietary_verified_at",
            "spice_level",
            "spice_source_url",
            "spice_verified_at",
        ):
            if field in row:
                payload[field] = row[field]
        if apply:
            assert client is not None
            try:
                client.table("recipes").upsert(payload, on_conflict="id").execute()
            except Exception as exc:  # noqa: BLE001
                reports.append(f"LOI insert recipe '{name}': {exc}")
                continue
        inserted += 1

        # Insert recipe_ingredients
        for ing, match, qty, unit in valid_ings:
            ing_name = ing.get("name") or ""
            ri_payload = {
                "recipe_id": uid,
                "ingredient_id": match["id"],
                "quantity": float(qty),
                "unit": unit,
            }
            if apply:
                assert client is not None
                try:
                    client.table("recipe_ingredients").upsert(
                        ri_payload, on_conflict="recipe_id,ingredient_id"
                    ).execute()
                except Exception as exc:  # noqa: BLE001
                    reports.append(f"LOI insert recipe_ingredient '{ing_name}': {exc}")

    return {
        "total": len(rows),
        "inserted": inserted,
        "skipped_no_cat": skipped_no_cat,
        "skipped_no_ing": skipped_no_ing,
        "reports": reports,
    }


def print_report(label: str, report: dict[str, Any]) -> None:
    print(f"\n== {label} ==")
    for key in (
        "total",
        "inserted",
        "skipped",
        "need_translate",
        "skipped_no_cat",
        "skipped_no_ing",
    ):
        if key in report:
            print(f"  {key}: {report[key]}")
    rpts = report.get("reports", [])
    if rpts:
        print(f"  chi tiet ({len(rpts)}):")
        for item in rpts[:40]:
            print(f"    - {item}")
        if len(rpts) > 40:
            print(f"    ... (+{len(rpts) - 40} dong khac)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import du lieu harvest vao Supabase (dry-run mac dinh)."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Ghi vao Supabase (can bien moi truong + phep nguoi dung).",
    )
    args = parser.parse_args()

    client = build_client(args.apply)

    ing_report = import_ingredients(client, args.apply)
    recipe_report = import_recipes(client, args.apply, ing_report["index"])

    print_report("NGUYEN LIEU", ing_report)
    print_report("CONG THUC", recipe_report)

    if args.apply:
        print("\nDA GHI VAO SUPABASE (theo --apply).")
    else:
        print("\nDRY-RUN: chua ghi gi vao DB. Chay --apply de ghi (can phep nguoi dung).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
