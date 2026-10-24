"""Upload 551 cong thuc TheMealDB da dich tieng Viet len Supabase (chay local).

Chay MAC DEFaut o che do dry-run (chi bao cao, khong ghi DB).
Chi ghi DB khi co --apply VA SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY.
"""

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

VI_FILE = ROOT / "data" / "open" / "themealdb_recipes_vi.jsonl"
NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
VALID_UNITS = {"g", "kg", "ml", "l", "piece"}
VALID_CATEGORIES = {"man", "rau", "canh"}


def norm(text: str) -> str:
    if not text:
        return ""
    text = text.strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def gen_uuid(seed: str) -> str:
    return str(uuid.uuid5(NAMESPACE, seed))


def build_client(apply: bool) -> Any:
    if not apply:
        return None
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key or url.startswith("https://your-project"):
        print(
            "Loi: can SUPABASE_URL va SUPABASE_SERVICE_ROLE_KEY de --apply.",
            file=sys.stderr,
        )
        sys.exit(2)
    from supabase import create_client

    return create_client(url, key)


def upload_themealdb_vi(apply: bool = False) -> dict[str, Any]:
    client = build_client(apply)

    # Thu tap nguyen lieu
    ingredient_map: dict[str, dict[str, Any]] = {}
    with VI_FILE.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            for ing in rec.get("ingredients", []):
                ing_norm = (ing.get("normalized_name") or "").strip() or norm(ing.get("name", ""))
                ing_name = ing.get("name", "").strip() or ing_norm
                if ing_norm and ing_norm not in ingredient_map:
                    ingredient_map[ing_norm] = {"name": ing_name, "normalized_name": ing_norm}

    ingredient_uuids = {k: gen_uuid(f"ingredient:{k}") for k in sorted(ingredient_map)}

    if apply:
        print(f"--> Nhap {len(ingredient_map)} nguyen lieu...")
        for ing_norm in sorted(ingredient_map):
            ing = ingredient_map[ing_norm]
            payload = {
                "id": ingredient_uuids[ing_norm],
                "name": ing["name"],
                "normalized_name": ing_norm,
                "category": None,
            }
            client.table("ingredients").upsert(payload, on_conflict="normalized_name").execute()

    print("--> Nhap 551 cong thuc + recipe_ingredients...")
    inserted_recipes = 0
    inserted_links = 0
    skipped_links = 0
    reports: list[str] = []

    with VI_FILE.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            sid = rec.get("source_id", "")
            rid = gen_uuid(f"recipe:{sid}")
            cat = rec.get("dish_category", "man")
            if cat not in VALID_CATEGORIES:
                cat = "man"
            name = rec.get("name", "")
            instructions = rec.get("instructions") or []
            servings = int(rec.get("servings") or 4)

            payload = {
                "id": rid,
                "name": name,
                "category": cat,
                "instructions": instructions,
                "servings": servings,
            }
            if apply:
                try:
                    client.table("recipes").upsert(payload, on_conflict="id").execute()
                except Exception as exc:  # noqa: BLE001
                    reports.append(f"LOI insert recipe '{name}': {exc}")
                    continue
            inserted_recipes += 1

            for ing in rec.get("ingredients", []):
                ing_norm = (ing.get("normalized_name") or "").strip() or norm(ing.get("name", ""))
                iid = ingredient_uuids.get(ing_norm)
                if not iid:
                    reports.append(f"KHONG KHOP nguyen lieu '{ing.get('name')}' cho '{name}'")
                    skipped_links += 1
                    continue
                try:
                    qty = float(ing.get("quantity")) if ing.get("quantity") is not None else 0
                except Exception:
                    qty = 0
                unit = (ing.get("unit") or "").strip()
                if qty <= 0 or unit not in VALID_UNITS:
                    skipped_links += 1
                    continue
                ri_payload = {
                    "recipe_id": rid,
                    "ingredient_id": iid,
                    "quantity": qty,
                    "unit": unit,
                }
                if apply:
                    try:
                        client.table("recipe_ingredients").upsert(
                            ri_payload, on_conflict="recipe_id,ingredient_id"
                        ).execute()
                    except Exception as exc:  # noqa: BLE001
                        reports.append(f"LOI insert recipe_ingredient '{ing.get('name')}': {exc}")
                        continue
                inserted_links += 1

    if apply:
        # Kiem tra dem (chi doc)
        res_ing = client.table("ingredients").select("id", count="exact").execute()
        res_rec = client.table("recipes").select("id", count="exact").execute()
        res_ri = client.table("recipe_ingredients").select("id", count="exact").execute()
        print("\n== KET QUA TRONG SUPABASE ==")
        print(f"  ingredients : {res_ing.count or len(res_ing.data)}")
        print(f"  recipes     : {res_rec.count or len(res_rec.data)}")
        print(f"  recipe_ingredients : {res_ri.count or len(res_ri.data)}")

    return {
        "ingredients": len(ingredient_map),
        "recipes": inserted_recipes,
        "recipe_links": inserted_links,
        "skipped_links": skipped_links,
        "reports": reports[:20],
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Upload 551 cong thuc TheMealDB tieng Viet len Supabase."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Ghi thanh vao Supabase (can SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY).",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("EasyMeals — Upload TheMealDB tieng Viet len Supabase")
    print("=" * 60)
    print(f"Che do: {'APPLY (ghi DB)' if args.apply else 'DRY-RUN (chi bao cao)'}")
    res = upload_themealdb_vi(apply=args.apply)
    print("\n== BAO CAO ==")
    print(f"  Nguyen lieu: {res['ingredients']}")
    print(f"  Cong thuc: {res['recipes']}")
    print(f"  Recipe_ingredients: {res['recipe_links']}")
    print(f"  Bo qua lien ket: {res['skipped_links']}")
    if res["reports"]:
        print("\n-- Chi tiet loi (20 dau) --")
        for r in res["reports"]:
            print(f"  - {r}")
    if not args.apply:
        hint = (
            "\n--> De ghi thanh vao DB, chay: "
            "python scripts/upload_themealdb_vi_to_supabase.py --apply"
        )
        print(hint)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
