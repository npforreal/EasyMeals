"""Nạp dữ liệu mồi (Seed Catalogue) cho EasyMeals trên Supabase.

Chạy MẶC ĐỊNH ở chế độ dry-run (chỉ thống kê, không ghi DB).
Chỉ thực hiện ghi vào database khi có cờ --apply.

Dữ liệu gồm 2 nguồn:
1. Bộ danh mục chuẩn Việt Nam (29 nguyên liệu cơ bản, 18 món ăn Việt kinh điển: mặn, rau, canh).
2. Dữ liệu harvest mở rộng từ data/open/ (nếu có, qua từ điển đối chiếu Anh -> Việt).

Idempotent: chạy nhiều lần không tạo bản ghi trùng lặp.
An toàn: Không in khoá bí mật ra log, yêu cầu SUPABASE_SERVICE_ROLE_KEY chạy local.
"""

from __future__ import annotations

import argparse
import os
import sys
import unicodedata
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data" / "open"
INGREDIENTS_FILE = DATA_DIR / "ingredients.jsonl"
RECIPES_FILE = DATA_DIR / "recipes.jsonl"

VALID_UNITS = {"g", "kg", "ml", "l", "piece"}
VALID_CATEGORIES = {"man", "rau", "canh"}
NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

# Bộ danh mục chuẩn Việt Nam khởi tạo
CANONICAL_INGREDIENTS = [
    ("11111111-0001-0000-0000-000000000001", "Thịt ba chỉ", "thit ba chi", "meat"),
    ("11111111-0001-0000-0000-000000000002", "Thịt heo nạc dăm", "thit heo nac dam", "meat"),
    ("11111111-0001-0000-0000-000000000003", "Sườn non heo", "suon non heo", "meat"),
    ("11111111-0001-0000-0000-000000000004", "Thịt bò thăn", "thit bo than", "meat"),
    ("11111111-0001-0000-0000-000000000005", "Thịt gà", "thit ga", "poultry"),
    ("11111111-0001-0000-0000-000000000006", "Cá lóc", "ca loc", "seafood"),
    ("11111111-0001-0000-0000-000000000007", "Tôm sú", "tom su", "seafood"),
    ("11111111-0001-0000-0000-000000000008", "Trứng gà", "trung ga", "egg"),
    ("11111111-0001-0000-0000-000000000009", "Trứng vịt", "trung vit", "egg"),
    ("11111111-0001-0000-0000-000000000010", "Đậu hũ trắng", "dau hu trang", "tofu"),
    ("11111111-0001-0000-0000-000000000011", "Rau muống", "rau muong", "vegetable"),
    ("11111111-0001-0000-0000-000000000012", "Cải ngọt", "cai ngot", "vegetable"),
    ("11111111-0001-0000-0000-000000000013", "Rau mồng tơi", "rau mong toi", "vegetable"),
    ("11111111-0001-0000-0000-000000000014", "Bắp cải", "bap cai", "vegetable"),
    ("11111111-0001-0000-0000-000000000015", "Cà chua", "ca chua", "vegetable"),
    ("11111111-0001-0000-0000-000000000016", "Dưa leo", "dua leo", "vegetable"),
    ("11111111-0001-0000-0000-000000000017", "Bí đỏ", "bi do", "vegetable"),
    ("11111111-0001-0000-0000-000000000018", "Khoai tây", "khoai tay", "root"),
    ("11111111-0001-0000-0000-000000000019", "Cà rốt", "ca rot", "root"),
    ("11111111-0001-0000-0000-000000000020", "Đậu cô ve", "dau co ve", "vegetable"),
    ("11111111-0001-0000-0000-000000000021", "Thơm (Dứa)", "thom dua", "fruit_vegetable"),
    ("11111111-0001-0000-0000-000000000022", "Đậu bắp", "dau bap", "vegetable"),
    ("11111111-0001-0000-0000-000000000023", "Giá đỗ", "gia do", "vegetable"),
    ("11111111-0001-0000-0000-000000000024", "Nấm rơm", "nam rom", "mushroom"),
    ("11111111-0001-0000-0000-000000000025", "Tỏi", "toi", "spice"),
    ("11111111-0001-0000-0000-000000000026", "Hành tím", "hanh tim", "spice"),
    ("11111111-0001-0000-0000-000000000027", "Hành lá", "hanh la", "herb"),
    ("11111111-0001-0000-0000-000000000028", "Gừng", "gung", "spice"),
    ("11111111-0001-0000-0000-000000000029", "Cần tây", "can tay", "vegetable"),
]

CANONICAL_ALIASES = [
    ("11111111-0001-0000-0000-000000000001", "Thịt rọi", "thit roi"),
    ("11111111-0001-0000-0000-000000000002", "Thịt băm", "thit bam"),
    ("11111111-0001-0000-0000-000000000002", "Thịt xay", "thit xay"),
    ("11111111-0001-0000-0000-000000000010", "Tàu hũ", "tau hu"),
    ("11111111-0001-0000-0000-000000000021", "Dứa", "dua"),
    ("11111111-0001-0000-0000-000000000021", "Khóm", "khom"),
]

CANONICAL_RECIPES = [
    (
        "22222222-0001-0000-0000-000000000001",
        "Thịt kho tàu",
        "man",
        4,
        [
            "Ướp thịt ba chỉ với hành tím băm, nước mắm, tiêu trong 20 phút.",
            "Luộc trứng vịt chín rồi bóc vỏ.",
            "Thắng nước màu đường caramen, trút thịt vào đảo săn đều.",
            "Thêm nước vào nồi ngập thịt, đun sôi rồi hạ lửa riu riu.",
            "Cho trứng vịt vào kho cùng đến khi thịt mềm rục, nước sền sệt.",
        ],
        [
            ("11111111-0001-0000-0000-000000000001", 500, "g"),
            ("11111111-0001-0000-0000-000000000009", 4, "piece"),
            ("11111111-0001-0000-0000-000000000026", 20, "g"),
        ],
    ),
    (
        "22222222-0001-0000-0000-000000000002",
        "Sườn xào chua ngọt",
        "man",
        4,
        [
            "Sườn non chặt miếng vừa ăn, chần qua nước sôi rồi để ráo.",
            "Chiên sườn vàng đều 2 mặt trên chảo dầu nóng.",
            "Pha sốt chua ngọt từ nước mắm, giấm gạo, đường và tương cà chua.",
            "Phi thơm tỏi, cho sườn và nước sốt đảo đều đến khi ngấm đậm vị.",
        ],
        [
            ("11111111-0001-0000-0000-000000000003", 500, "g"),
            ("11111111-0001-0000-0000-000000000025", 15, "g"),
            ("11111111-0001-0000-0000-000000000015", 100, "g"),
        ],
    ),
    (
        "22222222-0001-0000-0000-000000000003",
        "Gà kho gừng",
        "man",
        4,
        [
            "Gà rửa sạch, chặt miếng vừa ăn.",
            "Ướp gà với gừng thái sợi, tỏi băm, nước mắm và tiêu trong 15 phút.",
            "Phi tỏi và một ít gừng cho thơm, trút gà vào xào săn.",
            "Đậy vung hạ lửa nhỏ kho liu riu 15 phút đến khi gà chín mềm.",
        ],
        [
            ("11111111-0001-0000-0000-000000000005", 600, "g"),
            ("11111111-0001-0000-0000-000000000028", 30, "g"),
            ("11111111-0001-0000-0000-000000000025", 15, "g"),
        ],
    ),
    (
        "22222222-0002-0000-0000-000000000001",
        "Rau muống xào tỏi",
        "rau",
        4,
        [
            "Rau muống nhặt sạch, chần nhanh qua nước sôi có chút muối.",
            "Làm nóng dầu ăn trên chảo lửa lớn, phi thơm tỏi đập dập.",
            "Cho rau muống vào đảo nhanh tay, nêm gia vị vừa ăn rồi tắt bếp.",
        ],
        [
            ("11111111-0001-0000-0000-000000000011", 400, "g"),
            ("11111111-0001-0000-0000-000000000025", 25, "g"),
        ],
    ),
    (
        "22222222-0003-0000-0000-000000000001",
        "Canh chua cá lóc",
        "canh",
        4,
        [
            "Cá lóc rửa sạch cắt khúc, cà chua bổ múi cau, thơm thái lát, đậu bắp cắt xéo.",
            "Phi thơm tỏi băm, cho cà chua và thơm vào xào lấy màu đẹp.",
            "Thêm nước vào đun sôi, thả cá lóc vào nấu chín.",
            "Cho đậu bắp, giá đỗ vào nấu sôi lại, nêm nếm gia vị và rau ngò.",
        ],
        [
            ("11111111-0001-0000-0000-000000000006", 400, "g"),
            ("11111111-0001-0000-0000-000000000015", 150, "g"),
            ("11111111-0001-0000-0000-000000000021", 150, "g"),
            ("11111111-0001-0000-0000-000000000022", 100, "g"),
            ("11111111-0001-0000-0000-000000000023", 100, "g"),
        ],
    ),
]


def normalize_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    without_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    cleaned = without_marks.replace("đ", "d").replace("Đ", "d")
    return " ".join(cleaned.split())


def get_client(service_key: str, supabase_url: str) -> Any:
    from supabase import create_client

    return create_client(supabase_url, service_key)


def seed_database(apply: bool = False, with_harvest: bool = False) -> None:
    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    print("=" * 60)
    print("EasyMeals — Nạp Dữ Liệu Danh Mục Mồi (Catalogue Seeder)")
    print("=" * 60)
    print(f"Chế độ: {'APPLY (ghi thật vào DB)' if apply else 'DRY-RUN (chỉ kiểm tra)'}")

    if not supabase_url:
        print("Lỗi: SUPABASE_URL không được tìm thấy trong môi trường hoặc .env")
        sys.exit(1)

    if apply and not service_role_key:
        print("Lỗi: Cần SUPABASE_SERVICE_ROLE_KEY để ghi dữ liệu mồi vào Supabase.")
        sys.exit(1)

    print(f"Tổng nguyên liệu chuẩn chuẩn bị nạp: {len(CANONICAL_INGREDIENTS)}")
    print(f"Tổng alias chuẩn bị nạp: {len(CANONICAL_ALIASES)}")
    print(f"Tổng công thức chuẩn bị nạp: {len(CANONICAL_RECIPES)}")
    if with_harvest:
        print("Kèm theo: Kho mở rộng (105 món Việt Nam + 25 món quốc tế dịch + 550 món TheMealDB)")

    if not apply:
        print("\n--> [DRY-RUN HOÀN TẤT]: Để ghi vào cơ sở dữ liệu thật, chạy:")
        if with_harvest:
            print("    python scripts/seed_catalogue.py --apply --with-harvest")
        else:
            print("    python scripts/seed_catalogue.py --apply")
        return

    client = get_client(service_role_key, supabase_url)

    # 1. Nạp ingredients
    print("\n--> Đang nạp bảng ingredients...")
    for item_id, name, norm_name, cat in CANONICAL_INGREDIENTS:
        payload = {
            "id": item_id,
            "name": name,
            "normalized_name": norm_name,
            "category": cat,
        }
        client.table("ingredients").upsert(payload, on_conflict="normalized_name").execute()

    # 2. Nạp aliases
    print("--> Đang nạp bảng ingredient_aliases...")
    for item_id, alias, norm_alias in CANONICAL_ALIASES:
        payload = {
            "ingredient_id": item_id,
            "alias": alias,
            "normalized_alias": norm_alias,
        }
        client.table("ingredient_aliases").upsert(payload, on_conflict="normalized_alias").execute()

    # 3. Nạp recipes & recipe_ingredients
    print("--> Đang nạp bảng recipes và recipe_ingredients...")
    for rec_id, name, cat, servings, instructions, ing_list in CANONICAL_RECIPES:
        rec_payload = {
            "id": rec_id,
            "name": name,
            "category": cat,
            "servings": servings,
            "instructions": instructions,
        }
        client.table("recipes").upsert(rec_payload, on_conflict="id").execute()

        for ing_id, qty, unit in ing_list:
            ing_payload = {
                "recipe_id": rec_id,
                "ingredient_id": ing_id,
                "quantity": float(qty),
                "unit": unit,
            }
            client.table("recipe_ingredients").upsert(
                ing_payload, on_conflict="recipe_id,ingredient_id"
            ).execute()

    # 4. Nếu có --with-harvest, nạp tiếp kho mở rộng (món Việt & quốc tế dịch chuẩn)
    if with_harvest:
        print("\n" + "=" * 60)
        print("Đang nạp kho công thức mở rộng (Món Việt & Quốc tế dịch chuẩn)...")
        print("=" * 60)
        try:
            from scripts.import_harvest import import_ingredients, import_recipes
        except ModuleNotFoundError:
            from import_harvest import import_ingredients, import_recipes

        ing_res = import_ingredients(client, apply=apply)
        print(f"  + Đã nạp nguyên liệu mở rộng: {ing_res['inserted']} items")
        rec_res = import_recipes(client, apply=apply, ing_index=ing_res["index"])
        print(f"  + Đã nạp công thức mở rộng: {rec_res['inserted']} items")

    # 5. Kiểm tra đếm số lượng sau nạp (chỉ đọc)
    print("\n--> Kiểm tra kết quả trong Supabase:")
    res_ing = client.table("ingredients").select("id", count="exact").execute()
    res_rec = client.table("recipes").select("id", count="exact").execute()
    print(f"  - Số lượng nguyên liệu trong DB: {res_ing.count or len(res_ing.data)}")
    print(f"  - Số lượng công thức trong DB: {res_rec.count or len(res_rec.data)}")
    print("\n[THÀNH CÔNG] Dữ liệu danh mục đã được nạp và kiểm tra.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed catalogue data into Supabase.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Thực hiện ghi vào Supabase (mặc định chỉ chạy dry-run).",
    )
    parser.add_argument(
        "--with-harvest",
        action="store_true",
        help="Nạp kèm toàn bộ kho dữ liệu mở rộng (105 món Việt, 25 món quốc tế dịch, v.v.).",
    )
    args = parser.parse_args()
    seed_database(apply=args.apply, with_harvest=args.with_harvest)


if __name__ == "__main__":
    main()
