"""Script tao va bien soan bo du lieu mon an gia dinh Viet Nam va mon quoc te dich chuan.

Tong hop:
- 105 mon an Viet Nam truyen thong & hien dai (45 mon man, 30 mon rau, 30 mon canh)
- 25 mon an quoc te pho bien nhat voi nguoi Viet (da dich ten & instructions, chuan hoa don vi)
Ghi ra:
- data/open/vietnamese_recipes.jsonl
- data/open/international_recipes_vi.jsonl
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "open"
DATA_DIR.mkdir(parents=True, exist_ok=True)

VN_OUT = DATA_DIR / "vietnamese_recipes.jsonl"
INTL_OUT = DATA_DIR / "international_recipes_vi.jsonl"


def normalize_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    without_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    cleaned = without_marks.replace("đ", "d").replace("Đ", "d")
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def make_ing(name: str, qty: float | int, unit: str, measure: str | None = None) -> dict[str, Any]:
    norm = normalize_text(name)
    m = measure or f"{qty}{unit}"
    return {
        "name": name,
        "normalized_name": norm,
        "measure": m,
        "quantity": str(qty),
        "unit": unit,
    }


def make_recipe(
    idx: str,
    name: str,
    cat: str,
    servings: int,
    instructions: list[str],
    ingredients: list[dict[str, Any]],
    aliases: list[str] | None = None,
    area: str = "Vietnamese",
    source: str = "vietnamese_family_standard",
    *,
    # Thời gian chuẩn bị / nấu, độ khó và mẹo bảo quản (E2-data / E3-data).
    # Các giá trị này để None khi chưa có nguồn xác minh riêng cho từng công thức.
    # KHÔNG bịa số liệu: nếu không có nguồn xác minh, để null và đánh dấu thiếu bằng chứng.
    prep_time_minutes: int | None = None,
    prep_time_source_url: str | None = None,
    prep_time_verified_at: str | None = None,
    cook_time_minutes: int | None = None,
    cook_time_source_url: str | None = None,
    cook_time_verified_at: str | None = None,
    difficulty: str | None = None,
    difficulty_source_url: str | None = None,
    difficulty_verified_at: str | None = None,
    storage_tips: list[str] | None = None,
    storage_source_url: str | None = None,
    storage_verified_at: str | None = None,
) -> dict[str, Any]:
    return {
        "source_id": idx,
        "name": name,
        "normalized_name": normalize_text(name),
        "aliases": aliases or [],
        "dish_category": cat,
        "servings": servings,
        "area": area,
        "instructions": instructions,
        "ingredients": ingredients,
        "language": "vi",
        "source": source,
        # E2-data: thời gian chuẩn bị, thời gian nấu, độ khó (+ nguồn và ngày xác minh)
        "prep_time_minutes": prep_time_minutes,
        "prep_time_source_url": prep_time_source_url,
        "prep_time_verified_at": prep_time_verified_at,
        "cook_time_minutes": cook_time_minutes,
        "cook_time_source_url": cook_time_source_url,
        "cook_time_verified_at": cook_time_verified_at,
        "difficulty": difficulty,
        "difficulty_source_url": difficulty_source_url,
        "difficulty_verified_at": difficulty_verified_at,
        # E3-data: mẹo bảo quản (+ nguồn và ngày xác minh)
        "storage_tips": storage_tips,
        "storage_source_url": storage_source_url,
        "storage_verified_at": storage_verified_at,
    }


def get_vietnamese_man() -> list[dict[str, Any]]:
    return [
        make_recipe(
            "vn_m_01", "Thịt kho tàu với trứng", "man", 4,
            [
                "Thịt ba chỉ cạo sạch lông, rửa sạch để ráo, cắt miếng vuông khoảng 3-4cm.",
                "Ướp thịt với hành tím băm, tỏi băm, 2 muỗng nước mắm, 1 muỗng đường, tiêu trong 30 phút.",
                "Luộc chín 4 quả trứng vịt, bóc sạch vỏ.",
                "Thắng nước màu đường caramen trên chảo, cho thịt vào đảo săn đều màu.",
                "Đổ nước dừa tươi vào ngập mặt thịt, đun sôi vớt bọt, hạ nhỏ lửa kho liu riu 30 phút.",
                "Cho trứng vào kho cùng thêm 20 phút đến khi thịt mềm rục, nước sánh vàng óng thì tắt bếp."
            ],
            [
                make_ing("Thịt ba chỉ", 500, "g"),
                make_ing("Trứng vịt", 4, "piece"),
                make_ing("Hành tím", 30, "g"),
                make_ing("Tỏi", 20, "g"),
                make_ing("Nước mắm", 40, "ml"),
                make_ing("Đường", 30, "g"),
                make_ing("Tiêu", 5, "g"),
            ],
            aliases=["Thịt kho hột vịt", "Thịt kho nước dừa"]
        ),
        make_recipe(
            "vn_m_02", "Sườn non rim mặn ngọt", "man", 4,
            [
                "Sườn non chặt khúc vừa ăn, chần qua nước sôi 2 phút rồi rửa sạch, để ráo.",
                "Ướp sườn với hành tỏi băm, 1 muỗng nước mắm, tiêu trong 15 phút.",
                "Chiên sườn trên chảo với ít dầu đến khi vàng xém các mặt.",
                "Pha nước sốt: 2 muỗng nước mắm, 1.5 muỗng đường, 1 muỗng giấm, 3 muỗng nước lọc.",
                "Đổ nước sốt vào chảo sườn, đậy nắp đun lửa nhỏ đến khi sốt keo lại bám đều quanh miếng sườn."
            ],
            [
                make_ing("Sườn non heo", 500, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Tỏi", 15, "g"),
                make_ing("Nước mắm", 35, "ml"),
                make_ing("Đường", 25, "g"),
                make_ing("Tiêu", 5, "g"),
            ],
            aliases=["Sườn rim mặn ngọt"]
        ),
        make_recipe(
            "vn_m_03", "Sườn xào chua ngọt", "man", 4,
            [
                "Sườn non rửa sạch, chặt miếng 3cm, chần sơ nước sôi rồi ướp.",
                "Chiên sườn vàng đều hai mặt rồi vớt ra đĩa.",
                "Cà chua bổ múi cau, ớt chuông và hành tây cắt miếng vuông.",
                "Pha sốt chua ngọt: nước mắm, đường, giấm táo, tương cà.",
                "Phi thơm tỏi, trút cà chua, hành tây vào xào, sau đó cho sườn và sốt chua ngọt đảo đều 5 phút."
            ],
            [
                make_ing("Sườn non heo", 500, "g"),
                make_ing("Cà chua", 100, "g"),
                make_ing("Hành tây", 60, "g"),
                make_ing("Ớt chuông", 80, "g"),
                make_ing("Tỏi", 15, "g"),
                make_ing("Nước mắm", 30, "ml"),
                make_ing("Đường", 25, "g"),
            ]
        ),
        make_recipe(
            "vn_m_04", "Thịt ba chỉ rang cháy cạnh", "man", 4,
            [
                "Thịt ba chỉ rửa sạch, thái lát mỏng vừa ăn.",
                "Hành lá rửa sạch cắt khúc, hành tím thái lát.",
                "Cho thịt vào chảo đảo đều tay trên lửa vừa đến khi thịt tiết bớt mỡ và xém cạnh vàng nâu.",
                "Chắt bớt mỡ thừa ra, cho hành tím vào phi thơm cùng thịt.",
                "Nêm nước mắm, đường, tiêu đảo nhanh tay đến khi sốt bám bóng miếng thịt, rắc hành lá rồi tắt bếp."
            ],
            [
                make_ing("Thịt ba chỉ", 400, "g"),
                make_ing("Hành tím", 25, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Nước mắm", 25, "ml"),
                make_ing("Đường", 15, "g"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
        make_recipe(
            "vn_m_05", "Thịt ba chỉ luộc chấm mắm tôm", "man", 4,
            [
                "Thịt ba chỉ rửa sạch với muối, cuộn tròn buộc chỉ nếu thích miếng thịt tròn đẹp.",
                "Đun sôi nồi nước với vài củ hành tím đập dập và nhánh gừng.",
                "Thả thịt vào luộc khoảng 20-25 phút với lửa vừa đến khi dùng đũa xiên qua không còn nước hồng.",
                "Vớt thịt ngâm ngay vào âu nước đá lạnh 5 phút để thịt giòn trắng không bị thâm.",
                "Thái thịt lát mỏng, dọn kèm dưa leo, rau sống và chén mắm tôm đánh sủi bọt với chanh ớt đường."
            ],
            [
                make_ing("Thịt ba chỉ", 500, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Gừng", 15, "g"),
                make_ing("Dưa leo", 150, "g"),
                make_ing("Ớt", 10, "g"),
                make_ing("Chanh", 1, "piece"),
            ]
        ),
        make_recipe(
            "vn_m_06", "Thịt heo kho tiêu", "man", 4,
            [
                "Thịt nạc dăm hoặc ba chỉ thái miếng vuông nhỏ vừa ăn.",
                "Ướp thịt với nước mắm ngon, đường, hành tỏi băm và thật nhiều tiêu xay trong 20 phút.",
                "Thắng nước màu đường trong nồi đất hoặc nồi dày, trút thịt vào xào săn trên lửa lớn.",
                "Hạ nhỏ lửa, đậy vung kho liu riu không thêm nước để thịt thấm gia vị và tiết nước sốt đậm đà.",
                "Kho khoảng 15 phút đến khi nước cạn sánh sệt, rắc thêm ớt và tiêu hạt rồi tắt bếp."
            ],
            [
                make_ing("Thịt heo nạc dăm", 400, "g"),
                make_ing("Hành tím", 25, "g"),
                make_ing("Tỏi", 15, "g"),
                make_ing("Nước mắm", 30, "ml"),
                make_ing("Đường", 20, "g"),
                make_ing("Tiêu", 10, "g"),
            ]
        ),
        make_recipe(
            "vn_m_07", "Thịt băm viên sốt cà chua", "man", 4,
            [
                "Thịt nạc vai xay nhuyễn trộn cùng hành tím băm, mộc nhĩ nấm mèo ngâm nở thái nhỏ, tiêu.",
                "Vo thịt thành các viên tròn đường kính 3cm.",
                "Chiên sơ các viên thịt trong chảo dầu nóng cho săn mặt ngoài.",
                "Cà chua băm nhuyễn xào nhừ với hành phi thành sốt sệt, nêm nước mắm và chút đường.",
                "Thả các viên thịt vào sốt cà chua, đậy nắp om nhỏ lửa 15 phút cho ngấm đều, rắc hành lá."
            ],
            [
                make_ing("Thịt heo nạc dăm", 350, "g"),
                make_ing("Cà chua", 200, "g"),
                make_ing("Nấm mèo", 20, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Hành lá", 15, "g"),
                make_ing("Nước mắm", 20, "ml"),
            ],
            aliases=["Xíu mại sốt cà"]
        ),
        make_recipe(
            "vn_m_08", "Thịt heo kho quẹt tóp mỡ", "man", 4,
            [
                "Mỡ phần heo cắt hạt lựu, thắng trên chảo nhỏ lửa lấy tóp mỡ giòn vàng, vớt ra để riêng.",
                "Tôm khô ngâm nước ấm 15 phút cho mềm, rửa sạch để ráo.",
                "Pha hỗn hợp: 5 muỗng nước mắm, 4 muỗng đường, 3 muỗng nước lọc, tiêu sọ đập dập.",
                "Phi thơm hành tỏi băm với 1 muỗng mỡ heo trong tộ đất, cho tôm khô vào xào săn.",
                "Đổ hỗn hợp nước mắm vào đun sôi, hạ lửa nhỏ đun liu riu đến khi keo lại sền sệt.",
                "Trút tóp mỡ, ớt hiểm, tiêu xanh vào đảo đều 2 phút rồi tắt bếp, dùng chấm rau củ luộc."
            ],
            [
                make_ing("Thịt ba chỉ", 200, "g"),
                make_ing("Tôm khô", 50, "g"),
                make_ing("Hành tím", 25, "g"),
                make_ing("Tỏi", 15, "g"),
                make_ing("Nước mắm", 50, "ml"),
                make_ing("Đường", 40, "g"),
                make_ing("Tiêu", 10, "g"),
                make_ing("Ớt", 10, "g"),
            ]
        ),
        make_recipe(
            "vn_m_09", "Chả lụa rim nước mắm tiêu", "man", 4,
            [
                "Chả lụa (giò lụa) cắt miếng tam giác hoặc vuông dày khoảng 1cm.",
                "Chiên sơ các mặt chả lụa trên chảo dầu nóng cho vàng nhẹ và phồng giòn.",
                "Pha sốt rim: 2 muỗng nước mắm, 1 muỗng đường, 1/2 muỗng tương ớt, 1 muỗng tiêu xay, 3 muỗng nước.",
                "Phi thơm tỏi băm và ớt cắt lát, trút nước sốt vào đun sôi.",
                "Cho chả lụa vào đảo đều tay trên lửa nhỏ đến khi sốt keo óng ả bám quanh miếng chả."
            ],
            [
                make_ing("Chả lụa", 300, "g"),
                make_ing("Tỏi", 15, "g"),
                make_ing("Hành lá", 15, "g"),
                make_ing("Nước mắm", 25, "ml"),
                make_ing("Đường", 15, "g"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
        make_recipe(
            "vn_m_10", "Thịt kho măng tươi", "man", 4,
            [
                "Măng tươi luộc 2-3 lần với chút muối mở nắp để khử hết độc và đắng, xé miếng vừa ăn.",
                "Thịt ba chỉ thái con chì, ướp hành tỏi băm, nước mắm, đường trong 20 phút.",
                "Xào săn thịt trên chảo, sau đó trút măng vào xào chung cho ngấm gia vị.",
                "Đổ thêm nước xâm xấp mặt thịt, kho lửa nhỏ khoảng 25 phút cho thịt mềm và măng giòn ngọt.",
                "Rắc hành lá, tiêu xay rồi múc ra đĩa dùng với cơm nóng."
            ],
            [
                make_ing("Thịt ba chỉ", 400, "g"),
                make_ing("Măng tươi", 300, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Nước mắm", 30, "ml"),
                make_ing("Đường", 15, "g"),
            ]
        ),
        make_recipe(
            "vn_m_11", "Bò xào cần tỏi", "man", 4,
            [
                "Thịt bò thăn thái lát mỏng ngang thớ, ướp tỏi băm, gừng, dầu hào, tiêu và chút dầu ăn.",
                "Cần tây nhặt sạch cắt khúc 4cm, hành tây bổ múi cau, tỏi tây cắt xéo, cà chua bổ múi cau.",
                "Làm nóng chảo với lửa lớn, phi thơm tỏi, cho thịt bò vào xào nhanh 1-2 phút vừa chín tới rồi trút ra đĩa.",
                "Tiếp tục cho cần tây, tỏi tây, hành tây, cà chua vào xào trên lửa lớn, nêm.",
                "Trút thịt bò trở lại đảo đều 30 giây, rắc tiêu thơm rồi tắt bếp."
            ],
            [
                make_ing("Thịt bò thăn", 300, "g"),
                make_ing("Cần tây", 150, "g"),
                make_ing("Hành tây", 80, "g"),
                make_ing("Cà chua", 80, "g"),
                make_ing("Tỏi", 20, "g"),
                make_ing("Dầu ăn", 20, "ml"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
        make_recipe(
            "vn_m_12", "Bò lúc lắc khoai tây", "man", 4,
            [
                "Thịt bò thăn cắt khối vuông quân cờ 2x2cm, ướp tỏi băm, dầu hào, nước tương, đường, tiêu và bơ.",
                "Khoai tây gọt vỏ, cắt thanh dài, chiên vàng giòn trong dầu nóng rồi vớt ra để ráo.",
                "Ớt chuông và hành tây cắt miếng vuông vừa ăn.",
                "Bắc chảo gang lên bếp lửa lớn thật nóng, cho chút dầu và bơ phi thơm tỏi.",
                "Cho thịt bò vào lắc đều tay trên lửa cực lớn khoảng 2 phút cho xém cạnh ngoài nhưng mềm ngọt bên trong.",
                "Cho ớt chuông, hành tây vào đảo nhanh 1 phút, trút ra đĩa ăn kèm khoai tây chiên."
            ],
            [
                make_ing("Thịt bò thăn", 400, "g"),
                make_ing("Khoai tây", 250, "g"),
                make_ing("Ớt chuông", 100, "g"),
                make_ing("Hành tây", 80, "g"),
                make_ing("Bơ", 20, "g"),
                make_ing("Tỏi", 20, "g"),
            ]
        ),
        make_recipe(
            "vn_m_13", "Bò kho sả gừng nước dừa", "man", 4,
            [
                "Nạm bò hoặc bắp bò cắt miếng vuông 3cm, chần qua nước gừng nóng khử mùi.",
                "Ướp bò với gói gia vị bò kho, sả băm, gừng, tỏi, nước mắm, đường trong 30 phút.",
                "Phi thơm hành tỏi và sả đập dập, trút thịt bò vào xào săn trên lửa lớn.",
                "Đổ nước dừa tươi ngập mặt thịt, đun sôi rồi hạ nhỏ lửa hầm liu riu 45 phút cho bò mềm.",
                "Cho cà rốt cắt khúc vào hầm thêm 15 phút, nước sốt sánh đậm đà, ăn cùng bánh mì hoặc cơm."
            ],
            [
                make_ing("Thịt bò thăn", 500, "g"),
                make_ing("Cà rốt", 200, "g"),
                make_ing("Sả", 50, "g"),
                make_ing("Gừng", 25, "g"),
                make_ing("Hành tím", 25, "g"),
                make_ing("Nước mắm", 30, "ml"),
            ]
        ),
        make_recipe(
            "vn_m_14", "Bò xào bông cải xanh", "man", 4,
            [
                "Thịt bò thái lát mỏng, ướp tỏi băm, dầu hào, nước tương và tiêu.",
                "Bông cải xanh (súp lơ) cắt miếng vừa ăn, ngâm rửa sạch rồi chần sơ nước sôi.",
                "Cà rốt tỉa hoa thái lát mỏng.",
                "Xào thịt bò trên lửa lớn vừa chín tới thì trút riêng ra đĩa.",
                "Xào bông cải và cà rốt với chút dầu ăn và cho chín giòn, trút thịt bò vào đảo đều 1 phút."
            ],
            [
                make_ing("Thịt bò thăn", 300, "g"),
                make_ing("Bông cải xanh", 300, "g"),
                make_ing("Cà rốt", 80, "g"),
                make_ing("Tỏi", 20, "g"),
                make_ing("Dầu ăn", 20, "ml"),
            ]
        ),
        make_recipe(
            "vn_m_15", "Bắp bò luộc gừng sả", "man", 4,
            [
                "Bắp bò hoa rửa sạch, dùng chỉ bọc tròn để khi thái lát có vân đẹp.",
                "Sả cây đập dập cắt khúc lót dưới đáy nồi, thêm vài lát gừng và củ hành tím.",
                "Cho bắp bò vào nồi cùng 2 muỗng nước mắm ngon, 1 muỗng đường, tiêu hạt.",
                "Đổ nước ngập ngang mặt thịt, đun sôi rồi hạ nhỏ lửa luộc trong 40 phút đến khi thịt chín mềm.",
                "Vớt bắp bò ra ngâm nước đá, để thật nguội rồi thái lát mỏng chấm mắm gừng hoặc tương gừng."
            ],
            [
                make_ing("Thịt bò thăn", 500, "g"),
                make_ing("Sả", 40, "g"),
                make_ing("Gừng", 30, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Nước mắm", 30, "ml"),
            ]
        ),
        make_recipe(
            "vn_m_16", "Gà kho gừng", "man", 4,
            [
                "Thịt gà ta chặt miếng vừa ăn, rửa thật sạch để ráo, để ráo.",
                "Gừng cạo vỏ, 1 nửa băm nhỏ ướp gà, 1 nửa thái sợi dài.",
                "Ướp gà với gừng băm, hành tím băm, 2 muỗng nước mắm, tiêu trong 20 phút.",
                "Thắng nước màu đường trong chảo, phi thơm gừng thái sợi rồi trút gà vào xào săn trên lửa lớn.",
                "Hạ nhỏ lửa, đậy vung kho khoảng 15 phút đến khi gà chín mềm, nước kho sánh thơm nức mùi gừng."
            ],
            [
                make_ing("Thịt gà", 600, "g"),
                make_ing("Gừng", 40, "g"),
                make_ing("Hành tím", 25, "g"),
                make_ing("Nước mắm", 35, "ml"),
                make_ing("Đường", 20, "g"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
        make_recipe(
            "vn_m_17", "Gà kho sả ớt cay nồng", "man", 4,
            [
                "Thịt gà chặt miếng vừa ăn, rửa sạch để ráo.",
                "Sả băm nhỏ, ớt hiểm băm nhuyễn, tỏi băm thơm.",
                "Ướp thịt gà với 1/2 lượng sả ớt, nước mắm, bột nghệ tạo màu trong 20 phút.",
                "Phi thơm lượng sả ớt còn lại trong chảo dầu nóng, trút gà vào xào săn vàng các mặt.",
                "Thêm 50ml nước lọc, đậy nắp kho lửa nhỏ 15 phút đến khi cạn nước, miếng gà thấm đẫm vị sả ớt cay thơm."
            ],
            [
                make_ing("Thịt gà", 600, "g"),
                make_ing("Sả", 50, "g"),
                make_ing("Ớt", 15, "g"),
                make_ing("Tỏi", 15, "g"),
                make_ing("Nước mắm", 35, "ml"),
                make_ing("Đường", 15, "g"),
            ]
        ),
        make_recipe(
            "vn_m_18", "Gà chiên nước mắm giòn da", "man", 4,
            [
                "Cánh gà hoặc đùi gà chặt miếng vừa ăn, khứa nhẹ mặt thịt, ướp và tỏi băm.",
                "Áo gà qua một lớp mỏng bột mì rồi chiên ngập dầu trên lửa vừa đến khi da gà vàng ươm giòn rụm.",
                "Pha sốt nước mắm: 2.5 muỗng nước mắm ngon, 2 muỗng đường, 1 muỗng tương ớt, 1 muỗng nước cốt chanh.",
                "Phi thơm tỏi băm trên chảo, đổ sốt nước mắm vào đun sôi sủi bọt keo lại.",
                "Trút gà chiên vào đảo thật nhanh tay 1 phút cho sốt bám đều quanh da gà rồi tắt bếp."
            ],
            [
                make_ing("Thịt gà", 600, "g"),
                make_ing("Tỏi", 25, "g"),
                make_ing("Nước mắm", 40, "ml"),
                make_ing("Đường", 30, "g"),
                make_ing("Ớt", 10, "g"),
                make_ing("Dầu ăn", 100, "ml"),
            ]
        ),
        make_recipe(
            "vn_m_19", "Gà hấp lá chanh", "man", 4,
            [
                "Gà ta làm sạch, xát muối và gừng khử mùi hôi, để ráo nước.",
                "Lá chanh rửa sạch, một nửa lót đáy xửng hấp, một nửa thái chỉ thật mỏng.",
                "Xát nhẹ chút muối và tiêu lên mình gà, đặt gà lên xửng hấp.",
                "Hấp gà trên lửa vừa trong 25-30 phút đến khi thịt gà chín tới, da căng bóng vàng óng.",
                "Chặt gà thành miếng vừa ăn, rải lá chanh thái chỉ lên trên, chấm muối tiêu chanh ớt."
            ],
            [
                make_ing("Thịt gà", 800, "g"),
                make_ing("Lá chanh", 20, "g"),
                make_ing("Chanh", 1, "piece"),
                make_ing("Ớt", 10, "g"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
        make_recipe(
            "vn_m_20", "Cánh gà sốt me chua ngọt", "man", 4,
            [
                "Cánh gà rửa sạch, chặt 3 khúc, ướp, tiêu và hành tỏi băm 15 phút.",
                "Chiên cánh gà ngập dầu đến khi vàng giòn hai mặt.",
                "Me chín ngâm nước ấm dầm nát, lọc lấy nước cốt me.",
                "Pha nước sốt me: nước cốt me, đường, nước mắm, tương ớt khuấy tan.",
                "Phi thơm tỏi ớt băm, đổ sốt me vào đun sôi lăn tăn, cho cánh gà chiên vào đảo đều đến khi sốt keo bóng."
            ],
            [
                make_ing("Thịt gà", 500, "g"),
                make_ing("Cốt me", 40, "g"),
                make_ing("Nước mắm", 30, "ml"),
                make_ing("Đường", 30, "g"),
                make_ing("Tỏi", 15, "g"),
                make_ing("Ớt", 10, "g"),
            ]
        ),
        make_recipe(
            "vn_m_21", "Vịt kho gừng", "man", 4,
            [
                "Thịt vịt rửa sạch với rượu trắng và gừng đập dập để khử sạch mùi hôi đặc trưng, chặt miếng vừa ăn.",
                "Gừng cạo vỏ, thái sợi hoặc thái lát dày đập dập.",
                "Ướp vịt với gừng, hành tím băm, nước mắm, đường, tiêu và nước màu đường trong 25 phút.",
                "Bắc nồi lên bếp, phi thơm chút hành tím rồi cho thịt vịt vào xào săn trên lửa lớn.",
                "Hạ nhỏ lửa đun liu riu khoảng 20 phút đến khi thịt vịt mềm rục, nước kho sánh thơm nức mũi."
            ],
            [
                make_ing("Thịt vịt", 600, "g"),
                make_ing("Gừng", 50, "g"),
                make_ing("Hành tím", 30, "g"),
                make_ing("Nước mắm", 35, "ml"),
                make_ing("Đường", 20, "g"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
        make_recipe(
            "vn_m_22", "Vịt om sấu chua thanh", "man", 4,
            [
                "Vịt làm sạch, chặt miếng vừa ăn, chần qua nước gừng nóng khử mùi.",
                "Sấu cạo vỏ rửa sạch, khía chữ thập quanh quả.",
                "Ướp vịt với hành, tỏi, sả băm, nước mắm trong 20 phút.",
                "Xào săn thịt vịt với sả hành, đổ nước dừa hoặc nước lọc ngập thịt và thả sấu vào nấu sôi.",
                "Hạ lửa om 25 phút cho vịt mềm, dầm sấu lấy vị chua thanh dịu, thả rau rút và mùi tàu cắt khúc rồi tắt bếp."
            ],
            [
                make_ing("Thịt vịt", 700, "g"),
                make_ing("Quả sấu", 6, "piece"),
                make_ing("Sả", 30, "g"),
                make_ing("Hành tím", 25, "g"),
                make_ing("Mùi tàu", 20, "g"),
                make_ing("Nước mắm", 30, "ml"),
            ]
        ),
        make_recipe(
            "vn_m_23", "Cá lóc kho tộ", "man", 4,
            [
                "Cá lóc làm sạch vảy, cắt khúc dày 2.5cm, rửa với muối và chanh cho hết nhớt.",
                "Ướp cá với hành tím, ớt đập dập, 3 muỗng nước mắm ngon, 1.5 muỗng đường, nước màu đường, tiêu 30 phút.",
                "Xếp thịt ba chỉ lát mỏng hoặc mỡ dưới đáy tộ đất, đặt các khúc cá lên trên.",
                "Bắc tộ lên bếp đun sôi trên lửa lớn cho cá săn chắc thịt.",
                "Đổ thêm 50ml nước nóng hoặc nước dừa, hạ lửa thật nhỏ kho liu riu 35 phút đến khi nước cạn sánh kẹo.",
                "Rắc hành lá, tiêu xay và vài lát ớt hiểm lên mặt trước khi bưng ra bàn ăn."
            ],
            [
                make_ing("Cá lóc", 500, "g"),
                make_ing("Thịt ba chỉ", 100, "g"),
                make_ing("Hành tím", 30, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Nước mắm", 45, "ml"),
                make_ing("Đường", 25, "g"),
                make_ing("Tiêu", 10, "g"),
                make_ing("Ớt", 10, "g"),
            ]
        ),
        make_recipe(
            "vn_m_24", "Cá bống kho tiêu", "man", 4,
            [
                "Cá bống làm sạch ruột, đánh sạch vảy, rửa thật sạch để ráo, để ráo nước.",
                "Ướp cá với nước mắm ngon, tiêu xay thật nhiều, đường, hành tỏi băm trong 30 phút.",
                "Thắng nước màu đường trong nồi đất cho vàng cánh gián, cho cá bống vào đun sôi lăn tăn.",
                "Không đảo cá để tránh vỡ nát, thỉnh thoảng lắc nhẹ nồi cho ngấm đều gia vị.",
                "Kho lửa nhỏ liu riu đến khi thịt cá săn đanh lại, nước kho cạn sánh bóng, rắc thêm ớt hiểm và tiêu sọ."
            ],
            [
                make_ing("Cá bống", 400, "g"),
                make_ing("Hành tím", 25, "g"),
                make_ing("Tỏi", 15, "g"),
                make_ing("Nước mắm", 35, "ml"),
                make_ing("Đường", 20, "g"),
                make_ing("Tiêu", 12, "g"),
                make_ing("Ớt", 10, "g"),
            ]
        ),
        make_recipe(
            "vn_m_25", "Cá thu sốt cà chua", "man", 4,
            [
                "Cá thu cắt khúc rửa sạch, thấm khô nước, ướp chút muối và tiêu 10 phút.",
                "Chiên cá thu trên chảo dầu nóng đến khi hai mặt vàng nhẹ thì gắp ra đĩa.",
                "Cà chua băm nhuyễn, phi thơm hành tím rồi trút cà chua vào xào nhuyễn thành sốt đỏ sệt.",
                "Nêm nước mắm, đường vừa vị mặn ngọt hài hòa.",
                "Thả cá thu vào chảo sốt cà, rưới sốt lên mặt cá, đun nhỏ lửa 10 phút cho cá ngấm đều, rắc hành ngò."
            ],
            [
                make_ing("Cá thu", 450, "g"),
                make_ing("Cà chua", 250, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Nước mắm", 25, "ml"),
                make_ing("Đường", 15, "g"),
            ]
        ),
        make_recipe(
            "vn_m_26", "Cá điêu hồng chiên giòn", "man", 4,
            [
                "Cá điêu hồng đánh sạch vảy, khía xéo vài đường trên mình cá, để thật ráo nước.",
                "Xát nhẹ một lớp muối mỏng quanh mình cá.",
                "Đun nóng chảo ngập dầu ăn, thả cá vào chiên trên lửa vừa đến khi một mặt vàng giòn rồi mới lật.",
                "Chiên vàng giòn đều cả hai mặt, vớt cá ra đĩa có lót giấy thấm dầu.",
                "Pha nước mắm tỏi ớt chanh chua ngọt đậm đà để chấm cùng, ăn kèm rau sống bánh tráng."
            ],
            [
                make_ing("Cá điêu hồng", 700, "g"),
                make_ing("Tỏi", 20, "g"),
                make_ing("Ớt", 10, "g"),
                make_ing("Chanh", 1, "piece"),
                make_ing("Nước mắm", 30, "ml"),
                make_ing("Dầu ăn", 150, "ml"),
            ]
        ),
        make_recipe(
            "vn_m_27", "Cá nục kho cà chua", "man", 4,
            [
                "Cá nục làm sạch ruột mang, cắt đôi nếu cá to, rửa sạch với nước muối loãng.",
                "Ướp cá với chút muối tiêu, chiên sơ hai mặt cho cá săn chắc không bị nát khi kho.",
                "Cà chua bổ múi cau, hành tím thái lát mỏng.",
                "Xếp một lớp cà chua dưới đáy nồi, đặt cá nục lên, phủ tiếp lớp cà chua bên trên.",
                "Nêm nước mắm, đường, đổ nước dừa hoặc nước sôi ngập cá, đun sôi rồi hạ nhỏ lửa kho 45 phút cho nhừ xương."
            ],
            [
                make_ing("Cá nục", 500, "g"),
                make_ing("Cà chua", 300, "g"),
                make_ing("Hành tím", 25, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Nước mắm", 35, "ml"),
                make_ing("Đường", 20, "g"),
            ]
        ),
        make_recipe(
            "vn_m_28", "Tôm rim mặn ngọt", "man", 4,
            [
                "Tôm sú hoặc tôm đất cắt bỏ đầu nhọn, râu và chân tôm, giữ lại vỏ để khi rim tôm giòn bóng.",
                "Rửa sạch tôm, để ráo, ướp với hành tím băm, tiêu trong 10 phút.",
                "Làm nóng chảo với dầu ăn, phi thơm hành tỏi băm rồi cho tôm vào đảo nhanh tay trên lửa lớn đến khi tôm đổi màu đỏ.",
                "Pha nước sốt: 2 muỗng nước mắm, 1.5 muỗng đường, 1/2 muỗng tiêu.",
                "Đổ sốt vào chảo tôm, đảo đều tay trên lửa vừa đến khi nước sốt keo lại bám óng ánh quanh thân tôm."
            ],
            [
                make_ing("Tôm sú", 400, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Tỏi", 15, "g"),
                make_ing("Nước mắm", 30, "ml"),
                make_ing("Đường", 25, "g"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
        make_recipe(
            "vn_m_29", "Tôm xào bông cải", "man", 4,
            [
                "Tôm sú bóc vỏ, bỏ chỉ đen trên lưng, rửa sạch thấm khô.",
                "Bông cải xanh và trắng cắt miếng vừa ăn, chần nhanh qua nước sôi có chút muối rồi ngâm nước lạnh.",
                "Cà rốt tỉa hoa thái lát.",
                "Phi thơm tỏi trên chảo lửa lớn, cho tôm vào xào săn chín tới rồi múc ra đĩa.",
                "Cho bông cải và cà rốt vào xào nhanh tay, nêm dầu hào, trút tôm vào đảo đều 1 phút rắc tiêu."
            ],
            [
                make_ing("Tôm sú", 300, "g"),
                make_ing("Bông cải xanh", 250, "g"),
                make_ing("Cà rốt", 80, "g"),
                make_ing("Tỏi", 15, "g"),
                make_ing("Dầu ăn", 20, "ml"),
            ]
        ),
        make_recipe(
            "vn_m_30", "Mực xào chua ngọt", "man", 4,
            [
                "Mực ống làm sạch, khía vảy rồng rồi cắt miếng vuông vừa ăn, chần sơ qua nước sôi với rượu gừng.",
                "Dưa leo, cà chua, dứa (thơm), hành tây, cần tây cắt miếng vừa ăn.",
                "Phi thơm tỏi trên chảo lửa lớn, xào mực nhanh tay 1 phút rồi trút ra đĩa.",
                "Cho dứa, cà chua, dưa leo, hành tây vào xào trên lửa lớn, nêm nước mắm, đường, giấm cho vừa vị chua ngọt.",
                "Trút mực và cần tây vào đảo đều nhanh 1 phút nữa, rắc tiêu rồi tắt bếp."
            ],
            [
                make_ing("Mực ống", 350, "g"),
                make_ing("Dứa", 120, "g"),
                make_ing("Cà chua", 100, "g"),
                make_ing("Dưa leo", 100, "g"),
                make_ing("Cần tây", 50, "g"),
                make_ing("Tỏi", 15, "g"),
                make_ing("Nước mắm", 20, "ml"),
            ]
        ),
        make_recipe(
            "vn_m_31", "Mực xào cần tỏi", "man", 4,
            [
                "Mực tươi làm sạch, thái khoanh hoặc khía hoa, ướp chút gừng băm và tiêu.",
                "Cần tây, tỏi tây cắt khúc, hành tây bổ múi cau.",
                "Bắc chảo lên bếp lửa lớn, phi thơm tỏi đập dập, trút mực vào đảo nhanh tay 1-2 phút cho mực săn giòn rồi vớt ra.",
                "Tiếp tục xào cần tây, tỏi tây, hành tây cho vừa chín tới.",
                "Đổ mực vào đảo lại cùng rau trong 30 giây, nêm dầu hào và tiêu thơm rồi tắt bếp."
            ],
            [
                make_ing("Mực ống", 350, "g"),
                make_ing("Cần tây", 150, "g"),
                make_ing("Hành tây", 80, "g"),
                make_ing("Tỏi", 20, "g"),
                make_ing("Dầu ăn", 20, "ml"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
        make_recipe(
            "vn_m_32", "Chả giò nem rán truyền thống", "man", 4,
            [
                "Thịt nạc vai băm nhỏ trộn tôm băm, mộc nhĩ, nấm hương ngâm nở thái chỉ, miến ngâm mềm cắt khúc.",
                "Cà rốt, củ đậu (hoặc su hào) bào sợi vắt bớt nước, hành lá thái nhỏ, đập 1 quả trứng vào trộn đều nhân.",
                "Trải bánh tráng ra mặt phẳng, múc lượng nhân vừa đủ cuộn tròn chặt tay vừa phải.",
                "Đun nóng dầu ăn ngập chảo, cho nem vào chiên lửa vừa đến khi chín đều rồi tăng lửa chiên vàng giòn rụm.",
                "Vớt nem ra đĩa có lót giấy thấm dầu, ăn kèm bún, rau sống và nước mắm chua ngọt tỏi ớt."
            ],
            [
                make_ing("Thịt heo nạc dăm", 300, "g"),
                make_ing("Tôm sú", 150, "g"),
                make_ing("Trứng gà", 1, "piece"),
                make_ing("Nấm mèo", 20, "g"),
                make_ing("Miến", 50, "g"),
                make_ing("Cà rốt", 80, "g"),
                make_ing("Bánh tráng", 20, "piece"),
                make_ing("Dầu ăn", 200, "ml"),
            ],
            aliases=["Nem rán", "Chả ram"]
        ),
        make_recipe(
            "vn_m_33", "Trứng chiên thịt băm", "man", 4,
            [
                "Thịt heo nạc vai băm nhỏ hoặc xay nhuyễn.",
                "Đập 4 quả trứng gà vào tô, thêm thịt băm, hành tím băm nhỏ, hành lá cắt nhỏ, 1 muỗng nước mắm, tiêu.",
                "Đánh tan đều trứng và thịt để gia vị hòa quyện.",
                "Làm nóng chảo với 2 muỗng dầu ăn, đổ hỗn hợp trứng thịt vào đậy vung hạ lửa nhỏ để thịt chín đều.",
                "Khi mặt dưới vàng đều, lật mặt trên chiên tiếp 2 phút đến khi hai mặt vàng thơm nở xốp."
            ],
            [
                make_ing("Trứng gà", 4, "piece"),
                make_ing("Thịt heo nạc dăm", 150, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Hành tím", 15, "g"),
                make_ing("Nước mắm", 15, "ml"),
                make_ing("Dầu ăn", 25, "ml"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
        make_recipe(
            "vn_m_34", "Đậu hũ nhồi thịt sốt cà chua", "man", 4,
            [
                "Đậu hũ trắng cắt miếng vuông 5cm, khoét nhẹ một phần ruột đậu ở giữa.",
                "Thịt nạc xay trộn đều cùng nấm mèo băm nhỏ, hành tím, chút ruột đậu, nước mắm, tiêu.",
                "Nhồi phần nhân thịt vào giữa từng miếng đậu hũ.",
                "Chiên sơ mặt nhồi thịt trên chảo dầu nóng cho thịt săn chắc và không bị rơi ra.",
                "Cà chua băm nhuyễn xào thành sốt, xếp đậu hũ vào om nhỏ lửa 15 phút cho ngấm sốt, rắc hành ngò."
            ],
            [
                make_ing("Đậu hũ trắng", 4, "piece"),
                make_ing("Thịt heo nạc dăm", 200, "g"),
                make_ing("Cà chua", 200, "g"),
                make_ing("Nấm mèo", 15, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Nước mắm", 20, "ml"),
            ]
        ),
        make_recipe(
            "vn_m_35", "Đậu hũ chiên sả ớt", "man", 4,
            [
                "Đậu hũ trắng rửa nhẹ, dùng khăn thấm khô, cắt miếng vuông vừa ăn.",
                "Chiên đậu hũ trong chảo dầu ngập lửa vừa đến khi bốn mặt vàng ươm giòn rụm rồi vớt ra.",
                "Sả băm nhỏ, ớt hiểm băm nhuyễn, tỏi băm thơm.",
                "Chắt bớt dầu trong chảo, cho sả tỏi ớt vào phi thật vàng thơm giòn.",
                "Nêm đường, o sả rồi trút đậu hũ chiên vào xóc đều tay 1 phút cho bám quanh miếng đậu."
            ],
            [
                make_ing("Đậu hũ trắng", 4, "piece"),
                make_ing("Sả", 50, "g"),
                make_ing("Ớt", 15, "g"),
                make_ing("Tỏi", 15, "g"),
                make_ing("Dầu ăn", 80, "ml"),
            ]
        ),
        make_recipe(
            "vn_m_36", "Trứng hấp thịt băm nấm mèo", "man", 4,
            [
                "Thịt nạc vai băm nhỏ, nấm mèo và miến ngâm nở thái nhuyễn, hành tím băm nhỏ.",
                "Đập 3 quả trứng vào tô thịt, chừa lại 1 lòng đỏ để quét mặt bánh.",
                "Nêm nước mắm, tiêu trộn đều các nguyên liệu cho sánh mịn.",
                "Đổ hỗn hợp vào khuôn hoặc tô sứ, cho vào xửng hấp lửa vừa trong 20 phút.",
                "Đánh tan lòng đỏ trứng còn lại với chút dầu màu điều, quét đều lên mặt trứng rồi hấp tiếp 5 phút không đậy nắp cho mặt vàng đẹp."
            ],
            [
                make_ing("Thịt heo nạc dăm", 200, "g"),
                make_ing("Trứng gà", 4, "piece"),
                make_ing("Nấm mèo", 20, "g"),
                make_ing("Miến", 30, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Tiêu", 5, "g"),
            ],
            aliases=["Chả trứng hấp"]
        ),
        make_recipe(
            "vn_m_37", "Lòng gà xào mướp hương", "man", 4,
            [
                "Lòng mề gà bóp muối và chanh thật kỹ khử mùi hôi, rửa sạch, thái miếng vừa ăn.",
                "Ướp lòng gà với hành tím băm, nước mắm và tiêu trong 15 phút.",
                "Mướp hương gọt vỏ, bổ đôi thái vát dày 1cm, hành lá cắt khúc.",
                "Phi thơm hành tím trên chảo dầu nóng, trút lòng gà vào xào chín săn trên lửa lớn rồi múc ra đĩa.",
                "Cho mướp vào xào nhanh trên lửa lớn vừa chín tới thì trút lòng gà vào đảo đều, rắc hành hoa tiêu xay."
            ],
            [
                make_ing("Lòng gà", 300, "g"),
                make_ing("Mướp hương", 400, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Nước mắm", 20, "ml"),
                make_ing("Dầu ăn", 20, "ml"),
            ]
        ),
        make_recipe(
            "vn_m_38", "Cá ba sa kho nghệ", "man", 4,
            [
                "Cá ba sa cắt khúc, chà muối gừng khử mùi tanh, để ráo nước.",
                "Củ nghệ tươi gọt vỏ giã nhuyễn lấy cả nước lẫn xác nghệ.",
                "Ướp cá với nghệ giã, hành tím băm, nước mắm, đường, ớt đập dập trong 25 phút.",
                "Bắc nồi lên bếp xào săn cá trên lửa lớn để cá thấm màu vàng tươi của nghệ.",
                "Thêm 80ml nước sôi, đậy vung hạ lửa nhỏ kho liu riu 25 phút cho cá ngấm vị đậm đà và nước sánh lại."
            ],
            [
                make_ing("Cá ba sa", 500, "g"),
                make_ing("Củ nghệ", 30, "g"),
                make_ing("Hành tím", 25, "g"),
                make_ing("Ớt", 10, "g"),
                make_ing("Nước mắm", 35, "ml"),
                make_ing("Đường", 20, "g"),
            ]
        ),
        make_recipe(
            "vn_m_39", "Ếch xào sả ớt", "man", 4,
            [
                "Thịt ếch làm sạch, lột da hoặc giữ da tùy thích, chặt miếng vừa ăn.",
                "Ướp ếch với hành tỏi băm, 1/2 lượng sả ớt, bột nghệ, nước mắm, tiêu trong 20 phút.",
                "Chiên sơ thịt ếch trên chảo dầu nóng cho thịt săn vàng giòn.",
                "Phi thơm lượng sả ớt còn lại với hành tỏi trên chảo, trút ếch vào đảo đều trên lửa lớn.",
                "Nêm nếm lại gia vị, thêm chút ớt chuông hoặc hành tây đảo đều 2 phút rồi tắt bếp."
            ],
            [
                make_ing("Thịt ếch", 450, "g"),
                make_ing("Sả", 50, "g"),
                make_ing("Ớt", 15, "g"),
                make_ing("Tỏi", 15, "g"),
                make_ing("Hành tím", 15, "g"),
                make_ing("Nước mắm", 25, "ml"),
            ]
        ),
        make_recipe(
            "vn_m_40", "Tôm rang thịt ba chỉ", "man", 4,
            [
                "Thịt ba chỉ thái miếng mỏng vừa ăn, tôm cắt râu rửa sạch để ráo.",
                "Cho thịt ba chỉ vào chảo đảo trên lửa vừa cho tiết bớt mỡ và xém cạnh vàng giòn.",
                "Gạt thịt sang một bên, trút hành tỏi băm vào phi thơm trên phần mỡ heo.",
                "Cho tôm vào đảo đều trên lửa lớn đến khi tôm cong lại đỏ au.",
                "Nêm nước mắm, đường, chút nước màu đảo đều tay đến khi nước cạn keo bám bóng tôm thịt, rắc hành lá tiêu xay."
            ],
            [
                make_ing("Thịt ba chỉ", 250, "g"),
                make_ing("Tôm sú", 250, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Tỏi", 15, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Nước mắm", 30, "ml"),
                make_ing("Đường", 25, "g"),
            ]
        ),
        make_recipe(
            "vn_m_41", "Chả cá thát lát chiên cốm", "man", 4,
            [
                "Cá thát lát nạo sẵn quết thật kỹ cùng hành tím băm, thì là băm nhuyễn, nước mắm, tiêu hạt cho dai dẻo.",
                "Thoa dầu ăn vào tay, nặn chả cá thành các viên tròn dẹt vừa ăn.",
                "Lăn từng miếng chả cá qua một lớp cốm dẹp xanh cho cốm bám đều quanh bề mặt.",
                "Đun nóng chảo dầu trên lửa vừa, thả chả cá vào chiên đến khi hạt cốm phồng giòn rụm và chả chín thơm.",
                "Vớt ra giấy thấm dầu, ăn nóng chấm tương ớt hoặc sốt mayonnaise."
            ],
            [
                make_ing("Cá thát lát", 350, "g"),
                make_ing("Cốm xanh", 100, "g"),
                make_ing("Thì là", 30, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Tiêu", 5, "g"),
                make_ing("Dầu ăn", 150, "ml"),
            ]
        ),
        make_recipe(
            "vn_m_42", "Cá rô phi nướng sả ớt", "man", 4,
            [
                "Cá rô phi đánh vảy làm sạch, khía xéo caro trên thân cá để ngấm gia vị.",
                "Giã nhuyễn hỗn hợp: sả băm, ớt hiểm, tỏi, gừng, nước mắm, dầu hào, đường.",
                "Xát đều hỗn hợp sả ớt vào bụng cá và các đường khía ngoài thân cá, ướp 30 phút.",
                "Nướng cá trên than hoa hoặc nồi chiên không dầu ở 180°C trong 20 phút, lật mặt nướng thêm 10 phút.",
                "Da cá vàng giòn thơm nức mùi sả ớt nướng, thịt bên trong trắng ngọt tự nhiên."
            ],
            [
                make_ing("Cá rô phi", 700, "g"),
                make_ing("Sả", 50, "g"),
                make_ing("Ớt", 15, "g"),
                make_ing("Tỏi", 20, "g"),
                make_ing("Gừng", 15, "g"),
                make_ing("Nước mắm", 30, "ml"),
            ]
        ),
        make_recipe(
            "vn_m_43", "Thịt bò né hoa thiên lý", "man", 4,
            [
                "Thịt bò thăn thái lát mỏng ngang thớ, ướp tỏi băm, dầu hào, tiêu và chút bơ thơm.",
                "Hoa thiên lý nhặt rửa sạch, ngâm rửa sạch 5 phút rồi để ráo.",
                "Làm nóng chảo gang với lửa lớn, cho 1 muỗng bơ lạt phi thơm tỏi băm.",
                "Cho thịt bò vào đảo nhanh tay 1 phút trên lửa lớn vừa chín tái thì cho hoa thiên lý vào đảo chung.",
                "Đảo đều trong 1 phút đến khi hoa thiên lý vừa chín tới giữ độ giòn ngọt, rắc tiêu rồi dọn ăn ngay trên chảo gang."
            ],
            [
                make_ing("Thịt bò thăn", 350, "g"),
                make_ing("Hoa thiên lý", 250, "g"),
                make_ing("Bơ", 25, "g"),
                make_ing("Tỏi", 20, "g"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
        make_recipe(
            "vn_m_45", "Tép đồng rang khế chua", "man", 4,
            [
                "Tép đồng hoặc tôm nhỏ nhặt sạch rác, rửa nước muối để ráo.",
                "Khế chua gọt rìa múi, thái lát mỏng hình ngôi sao.",
                "Cho tép vào chảo không dầu rang cho ráo nước và chuyển màu hồng cam.",
                "Thêm 1 muỗng mỡ heo (hoặc dầu ăn), hành tím phi thơm đảo đều cùng tép.",
                "Cho khế chua vào đảo chung, nêm nước mắm và đường cho vị mặn ngọt chua cân bằng, rắc lá chanh thái chỉ."
            ],
            [
                make_ing("Tôm sú", 300, "g"),
                make_ing("Khế chua", 100, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Nước mắm", 25, "ml"),
                make_ing("Đường", 20, "g"),
                make_ing("Lá chanh", 10, "g"),
            ]
        ),
    ]


def get_vietnamese_rau() -> list[dict[str, Any]]:
    return [
        make_recipe(
            "vn_r_01", "Rau muống xào tỏi", "rau", 4,
            [
                "Rau muống nhặt khúc non, bỏ bớt lá già, rửa sạch để ráo.",
                "Đun sôi nồi nước có chần nhanh rau muống 30 giây rồi vớt ra xả nước lạnh giữ màu xanh giòn.",
                "Tỏi bóc vỏ đập dập, chia làm hai phần.",
                "Làm nóng chảo với dầu ăn trên lửa lớn, phi thơm một nửa tỏi.",
                "Trút rau muống vào đảo nhanh tay, nêm nước mắm, cho nốt phần tỏi còn lại vào đảo đều 1 phút rồi tắt bếp."
            ],
            [
                make_ing("Rau muống", 500, "g"),
                make_ing("Tỏi", 40, "g"),
                make_ing("Dầu ăn", 30, "ml"),
                make_ing("Nước mắm", 15, "ml"),
            ]
        ),
        make_recipe(
            "vn_r_02", "Cải ngọt xào tỏi", "rau", 4,
            [
                "Cải ngọt cắt gốc, rửa sạch từng bẹ lá, cắt khúc dài 4-5cm.",
                "Tỏi bóc vỏ đập dập thơm.",
                "Làm nóng chảo với dầu ăn, phi thơm tỏi vàng óng trên lửa lớn.",
                "Trút phần cọng cải vào xào trước 1 phút, sau đó cho phần lá vào xào chung.",
                "Nêm dầu hào vừa ăn, đảo nhanh tay thêm 1 phút cho rau chín giòn rồi trút ra đĩa."
            ],
            [
                make_ing("Cải ngọt", 450, "g"),
                make_ing("Tỏi", 30, "g"),
                make_ing("Dầu ăn", 25, "ml"),
            ]
        ),
        make_recipe(
            "vn_r_03", "Bắp cải xào cà chua", "rau", 4,
            [
                "Bắp cải rửa sạch, thái sợi dày khoảng 1cm.",
                "Cà chua rửa sạch bổ múi cau, hành lá cắt khúc.",
                "Phi thơm hành tím băm trên chảo dầu nóng, cho cà chua vào đảo nhuyễn tạo màu.",
                "Trút bắp cải vào xào trên lửa lớn, nêm chút nước mắm và .",
                "Xào đến khi bắp cải chín mềm ngọt nhưng vẫn giữ được độ tươi giòn, rắc hành lá tiêu xay."
            ],
            [
                make_ing("Bắp cải", 400, "g"),
                make_ing("Cà chua", 150, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Nước mắm", 15, "ml"),
                make_ing("Dầu ăn", 20, "ml"),
            ]
        ),
        make_recipe(
            "vn_r_04", "Su su xào trứng", "rau", 4,
            [
                "Su su gọt vỏ dưới vòi nước chảy để không dính mủ, bổ đôi bỏ hạt rồi thái sợi mỏng.",
                "Phi thơm hành tím băm với dầu ăn trên chảo nóng.",
                "Trút su su vào xào trên lửa lớn, nêm cho vừa miệng.",
                "Khi su su vừa chín tới, đập 2 quả trứng gà vào chảo, đảo nhanh tay cho trứng bám đều quanh sợi su su.",
                "Rắc hành lá cắt nhỏ và tiêu xay thơm nồng rồi tắt bếp."
            ],
            [
                make_ing("Su su", 400, "g"),
                make_ing("Trứng gà", 2, "piece"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Dầu ăn", 25, "ml"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
        make_recipe(
            "vn_r_05", "Đậu cô ve xào thịt băm", "rau", 4,
            [
                "Đậu cô ve tước xơ hai bên mép, rửa sạch, cắt khúc xéo vừa ăn.",
                "Thịt nạc băm ướp và tiêu.",
                "Phi thơm tỏi trên chảo, cho thịt băm vào xào săn chín tới rồi múc riêng ra đĩa.",
                "Tiếp tục cho đậu cô ve vào chảo xào với lửa lớn, thêm chút nước lọc để đậu nhanh chín mềm ngọt.",
                "Trút thịt băm trở lại chảo đảo đều cùng đậu cô ve trong 1 phút, rắc tiêu thơm."
            ],
            [
                make_ing("Đậu cô ve", 350, "g"),
                make_ing("Thịt heo nạc dăm", 150, "g"),
                make_ing("Tỏi", 20, "g"),
                make_ing("Dầu ăn", 25, "ml"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
        make_recipe(
            "vn_r_06", "Bông cải trắng xào tỏi", "rau", 4,
            [
                "Bông cải trắng cắt thành các nhánh nhỏ vừa ăn, ngâm rửa sạch 5 phút rồi rửa sạch.",
                "Chần nhanh qua nước sôi 1 phút rồi vớt ra để ráo.",
                "Làm nóng chảo với dầu ăn, phi thơm tỏi đập dập.",
                "Cho bông cải vào xào nhanh tay trên lửa lớn, nêm dầu hào.",
                "Rắc hành lá thái nhỏ và tiêu xay thơm rồi trút ra đĩa dùng nóng."
            ],
            [
                make_ing("Bông cải trắng", 450, "g"),
                make_ing("Tỏi", 30, "g"),
                make_ing("Dầu ăn", 25, "ml"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
        make_recipe(
            "vn_r_07", "Măng tây xào tỏi bơ", "rau", 4,
            [
                "Măng tây cắt bỏ phần gốc già cứng, rửa sạch, cắt khúc dài 5cm.",
                "Chần măng tây qua nước sôi có chút muối 30 giây rồi ngâm nước đá lạnh cho giòn xanh.",
                "Làm nóng chảo, cho 1 muỗng dầu ăn và 1 muỗng bơ lạt vào đun chảy.",
                "Phi thơm tỏi băm trên lửa vừa đến khi dậy mùi thơm nức.",
                "Trút măng tây vào xào nhanh trên lửa lớn 2 phút, nêm chút muối tiêu rồi tắt bếp."
            ],
            [
                make_ing("Măng tây", 350, "g"),
                make_ing("Tỏi", 25, "g"),
                make_ing("Bơ", 20, "g"),
                make_ing("Dầu ăn", 15, "ml"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
        make_recipe(
            "vn_r_08", "Nấm đùi gà xào xì dầu", "rau", 4,
            [
                "Nấm đùi gà cắt gốc, rửa sạch, thái lát dày 0.5cm hoặc cắt quân cờ.",
                "Pha sốt xì dầu: 2 muỗng nước tương ngon, 1 muỗng dầu hào, 1/2 muỗng đường, tiêu.",
                "Phi thơm tỏi băm với dầu ăn trên chảo nóng.",
                "Cho nấm đùi gà vào xào trên lửa lớn cho nấm săn lại và tiết nước ngọt.",
                "Đổ sốt xì dầu vào đảo đều 3 phút cho nấm ngấm vị đậm đà nâu bóng, rắc hành lá cắt khúc."
            ],
            [
                make_ing("Nấm đùi gà", 400, "g"),
                make_ing("Tỏi", 20, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Nước tương", 30, "ml"),
                make_ing("Dầu ăn", 20, "ml"),
            ]
        ),
        make_recipe(
            "vn_r_09", "Ngọn bí xào tỏi", "rau", 4,
            [
                "Ngọn bí nhặt tước sạch xơ bên ngoài cọng và cuống lá, rửa sạch nhiều lần với nước.",
                "Chần cọng bí qua nước sôi 1 phút rồi thả lá bí vào đảo nhanh vớt ra ngay.",
                "Làm nóng chảo với nhiều dầu ăn, phi thơm thật nhiều tỏi đập dập.",
                "Trút ngọn bí vào xào nhanh tay trên lửa thật lớn để rau xanh giòn.",
                "Nêm nước mắm ngon và, đảo đều 1 phút cho ngấm tỏi rồi trút ra đĩa."
            ],
            [
                make_ing("Rau bí", 500, "g"),
                make_ing("Tỏi", 45, "g"),
                make_ing("Dầu ăn", 35, "ml"),
                make_ing("Nước mắm", 20, "ml"),
            ]
        ),
        make_recipe(
            "vn_r_10", "Giá đỗ xào huyết heo", "rau", 4,
            [
                "Giá đỗ nhặt bỏ rễ sâu, rửa sạch để ráo nước.",
                "Huyết heo luộc chín, cắt khối vuông quân cờ vừa ăn.",
                "Hẹ hoặc hành lá rửa sạch cắt khúc dài 4cm.",
                "Phi thơm hành tỏi băm trên chảo dầu nóng, cho huyết heo vào đảo nhẹ tay tránh vỡ.",
                "Trút giá đỗ và hẹ vào đảo nhanh trên lửa lớn 1 phút, nêm nước mắm tiêu rồi tắt bếp ngay giữ độ giòn."
            ],
            [
                make_ing("Giá đỗ", 300, "g"),
                make_ing("Huyết heo", 250, "g"),
                make_ing("Hành lá", 50, "g"),
                make_ing("Tỏi", 15, "g"),
                make_ing("Nước mắm", 15, "ml"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
        make_recipe(
            "vn_r_11", "Cải thìa sốt dầu hào", "rau", 4,
            [
                "Cải thìa cắt đôi dọc theo thân, rửa sạch bùn đất trong các bẹ lá.",
                "Chần cải thìa trong nước sôi có chút muối và vài giọt dầu ăn 1 phút để cải bóng xanh giòn.",
                "Vớt cải xếp ngay ngắn ra đĩa tròn.",
                "Pha nước sốt: 2 muỗng dầu hào, 1 muỗng nước tương, 1 muỗng đường, 3 muỗng nước lọc, chút bột mì.",
                "Phi thơm tỏi băm, đổ sốt vào đun sôi sánh lại rồi rưới đều lên đĩa cải thìa luộc."
            ],
            [
                make_ing("Cải thìa", 450, "g"),
                make_ing("Tỏi", 25, "g"),
                make_ing("Dầu hào", 30, "ml"),
                make_ing("Nước tương", 15, "ml"),
                make_ing("Dầu ăn", 15, "ml"),
            ]
        ),
        make_recipe(
            "vn_r_12", "Cà tím nướng mỡ hành", "rau", 4,
            [
                "Cà tím dài để nguyên cuống, rửa sạch, dùng tăm xiên nhẹ vài lỗ quanh thân cà.",
                "Nướng cà tím trên than hoa hoặc nồi chiên không dầu 200°C trong 15 phút cho da cháy xém mềm nhũn.",
                "Lột bỏ lớp vỏ cháy bên ngoài, tách thịt cà tím xếp ra đĩa phẳng.",
                "Hành lá thái nhỏ cho vào chén cùng chút muối đường, đun sôi 3 muỗng dầu ăn rồi đổ vào chén hành làm mỡ hành thơm.",
                "Rưới mỡ hành, nước mắm tỏi ớt chua ngọt và rắc đậu phộng rang giã dập lên đĩa cà tím."
            ],
            [
                make_ing("Cà tím", 450, "g"),
                make_ing("Hành lá", 50, "g"),
                make_ing("Đậu phộng", 30, "g"),
                make_ing("Ớt", 10, "g"),
                make_ing("Tỏi", 10, "g"),
                make_ing("Nước mắm", 25, "ml"),
                make_ing("Dầu ăn", 30, "ml"),
            ]
        ),
        make_recipe(
            "vn_r_13", "Đậu hũ sốt cà chua", "rau", 4,
            [
                "Đậu hũ trắng cắt miếng vuông 3cm, chiên vàng đều các mặt trên chảo dầu nóng.",
                "Cà chua rửa sạch, băm nhuyễn hoặc thái múi cau.",
                "Phi thơm hành tím băm, trút cà chua vào xào nhừ thành nước sốt sệt đỏ au.",
                "Nêm nước mắm, đường cho vừa miệng.",
                "Cho đậu hũ chiên vào sốt cà chua, đun nhỏ lửa 5-7 phút cho ngấm gia vị, rắc hành lá cắt nhỏ."
            ],
            [
                make_ing("Đậu hũ trắng", 4, "piece"),
                make_ing("Cà chua", 250, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Nước mắm", 20, "ml"),
                make_ing("Dầu ăn", 30, "ml"),
            ]
        ),
        make_recipe(
            "vn_r_14", "Dưa leo dầm tỏi ớt chua ngọt", "rau", 4,
            [
                "Dưa leo rửa sạch ngâm muối loãng, bỏ bớt ruột, đập dập rồi cắt khúc 3cm.",
                "Tỏi bóc vỏ đập dập băm nhỏ, ớt hiểm thái lát mỏng.",
                "Pha nước trộn: 2 muỗng nước mắm, 2 muỗng đường, 2 muỗng giấm táo (hoặc chanh).",
                "Cho dưa leo vào âu lớn, đổ hỗn hợp nước mắm tỏi ớt vào xóc đều tay.",
                "Để trong ngăn mát tủ lạnh 15-20 phút cho dưa ngấm giòn lạnh chua ngọt khai vị rất ngon."
            ],
            [
                make_ing("Dưa leo", 400, "g"),
                make_ing("Tỏi", 20, "g"),
                make_ing("Ớt", 10, "g"),
                make_ing("Nước mắm", 25, "ml"),
                make_ing("Đường", 25, "g"),
                make_ing("Giấm", 25, "ml"),
            ]
        ),
        make_recipe(
            "vn_r_15", "Bắp cải luộc dầm trứng nước mắm", "rau", 4,
            [
                "Bắp cải rửa sạch, cắt miếng tam giác to bản vừa ăn.",
                "Đun sôi nồi nước với một nhánh gừng đập dập.",
                "Thả bắp cải vào luộc trên lửa lớn khoảng 4-5 phút đến khi bắp cải chín trong mềm ngọt.",
                "Vớt bắp cải ra đĩa sâu lòng, giữ lại nước luộc làm canh thanh mát.",
                "Luộc chín lòng đào 2 quả trứng vịt (hoặc trứng gà), dầm nát vào chén nước mắm nhĩ ngon nhiều ớt để chấm rau."
            ],
            [
                make_ing("Bắp cải", 500, "g"),
                make_ing("Trứng vịt", 2, "piece"),
                make_ing("Gừng", 15, "g"),
                make_ing("Nước mắm", 30, "ml"),
                make_ing("Ớt", 10, "g"),
            ]
        ),
        make_recipe(
            "vn_r_16", "Rau muống luộc chấm tương bần", "rau", 4,
            [
                "Rau muống nhặt khúc non, rửa sạch ngâm rửa sạch.",
                "Đun nồi nước thật sôi trên lửa lớn, thả rau muống vào dìm ngập nước.",
                "Luộc khoảng 3 phút cho cọng rau vừa chín tới nhưng vẫn giữ độ xanh giòn.",
                "Vớt rau ra đĩa, vắt chút chanh hoặc thả vài quả sấu vào nồi nước luộc làm canh.",
                "Chấm rau cùng chén tương bần pha chút đường, ớt và vài lát gừng cay nồng."
            ],
            [
                make_ing("Rau muống", 500, "g"),
                make_ing("Tương bần", 40, "g"),
                make_ing("Chanh", 1, "piece"),
                make_ing("Ớt", 10, "g"),
            ]
        ),
        make_recipe(
            "vn_r_17", "Bầu luộc chấm kho quẹt", "rau", 4,
            [
                "Trái bầu non gọt vỏ, rửa sạch, cắt khúc dài 4cm hoặc thái lát dày 1cm.",
                "Đun sôi nồi nước có chút muối hạt.",
                "Thả bầu vào luộc lửa vừa khoảng 3 phút đến khi miếng bầu trong lại là chín ngọt.",
                "Vớt bầu ra đĩa tròn, dùng nóng chấm cùng tộ thịt kho quẹt đậm đà béo ngậy tóp mỡ."
            ],
            [
                make_ing("Bầu", 500, "g"),
                make_ing("Hành lá", 15, "g"),
            ]
        ),
        make_recipe(
            "vn_r_18", "Đậu bắp luộc chấm chao", "rau", 4,
            [
                "Đậu bắp rửa sạch, cắt bỏ phần cuống trên đầu nhưng không cắt sát vào trong ruột.",
                "Đun sôi nồi nước với chút muối hạt.",
                "Thả đậu bắp vào luộc khoảng 3-4 phút đến khi đậu chuyển màu xanh thẫm chín mềm.",
                "Vớt đậu bắp ra ngâm nhanh nước đá 1 phút cho giòn rồi xếp ra đĩa.",
                "Dầm 2 viên chao béo ngậy với chút đường, sa tế ớt để làm nước chấm thơm ngon độc đáo."
            ],
            [
                make_ing("Đậu bắp", 400, "g"),
                make_ing("Chao", 30, "g"),
                make_ing("Đường", 10, "g"),
                make_ing("Ớt", 10, "g"),
            ]
        ),
        make_recipe(
            "vn_r_19", "Củ quả luộc thập cẩm", "rau", 4,
            [
                "Cà rốt, su su, bông cải xanh, đậu bắp, bắp non gọt vỏ rửa sạch, cắt miếng con chì đều nhau.",
                "Đun sôi nồi nước lớn với 1/2 muỗng muối hạt.",
                "Cho cà rốt và su su vào luộc trước 3 phút, sau đó cho bông cải, đậu bắp và bắp non vào luộc tiếp 2 phút.",
                "Vớt toàn bộ củ quả ra đĩa lớn trình bày nhiều màu sắc rực rỡ bắt mắt.",
                "Chấm kèm kho quẹt tôm thịt hoặc trứng dầm nước mắm ngon."
            ],
            [
                make_ing("Cà rốt", 150, "g"),
                make_ing("Su su", 150, "g"),
                make_ing("Bông cải xanh", 150, "g"),
                make_ing("Đậu bắp", 100, "g"),
            ]
        ),
        make_recipe(
            "vn_r_20", "Gỏi ngó sen tôm thịt", "rau", 4,
            [
                "Ngó sen chẻ đôi cắt khúc, ngâm nước đá có pha giấm đường để ngó sen trắng giòn.",
                "Thịt ba chỉ luộc chín thái mỏng, tôm luộc chín bóc vỏ chẻ đôi sống lưng.",
                "Cà rốt bào sợi, dưa leo bỏ ruột thái lát, rau răm thái nhỏ, đậu phộng rang giã dập.",
                "Pha nước mắm gỏi: 3 muỗng nước mắm, 3 muỗng đường, 2.5 muỗng nước cốt chanh, tỏi ớt băm nhuyễn.",
                "Vắt ráo ngó sen cà rốt, trộn đều cùng tôm thịt, rau răm và nước mắm chua ngọt, rắc đậu phộng lên trên."
            ],
            [
                make_ing("Ngó sen", 300, "g"),
                make_ing("Tôm sú", 200, "g"),
                make_ing("Thịt ba chỉ", 150, "g"),
                make_ing("Cà rốt", 80, "g"),
                make_ing("Rau răm", 20, "g"),
                make_ing("Đậu phộng", 30, "g"),
                make_ing("Nước mắm", 30, "ml"),
                make_ing("Chanh", 2, "piece"),
            ]
        ),
        make_recipe(
            "vn_r_21", "Nộm hoa chuối tai heo", "rau", 4,
            [
                "Tai heo bóp muối chanh luộc chín giòn, ngâm nước đá rồi thái lát thật mỏng.",
                "Hoa chuối thái mỏng ngâm ngay vào âu nước có pha nước cốt chanh và muối để không bị thâm đen.",
                "Cà rốt bào sợi, giá đỗ rửa sạch, rau rau thơm húng quế thái nhỏ.",
                "Pha nước mắm chua ngọt tỏi ớt đậm đà.",
                "Vắt ráo hoa chuối, trộn đều cùng tai heo giòn sần sật, các loại rau thơm và nước sốt nộm, rắc lạc rang."
            ],
            [
                make_ing("Hoa chuối", 350, "g"),
                make_ing("Tai heo", 200, "g"),
                make_ing("Cà rốt", 80, "g"),
                make_ing("Đậu phộng", 30, "g"),
                make_ing("Rau thơm", 30, "g"),
                make_ing("Chanh", 2, "piece"),
                make_ing("Nước mắm", 30, "ml"),
            ]
        ),
        make_recipe(
            "vn_r_22", "Gỏi gà xé phay bắp cải", "rau", 4,
            [
                "Thịt ức hoặc đùi gà luộc chín tới, xé sợi vừa ăn.",
                "Bắp cải bào sợi mỏng rửa sạch ngâm nước đá cho giòn ráo.",
                "Hành tây thái mỏng ngâm giấm đường khử hăng, rau răm thái nhỏ.",
                "Pha nước sốt trộn: nước cốt chanh, đường, nước mắm, tỏi ớt băm nhuyễn và tiêu xay.",
                "Trộn đều bắp cải, thịt gà xé, hành tây với nước sốt, rắc đậu phộng rang và hành phi giòn."
            ],
            [
                make_ing("Thịt gà", 300, "g"),
                make_ing("Bắp cải", 300, "g"),
                make_ing("Hành tây", 80, "g"),
                make_ing("Rau răm", 25, "g"),
                make_ing("Đậu phộng", 30, "g"),
                make_ing("Chanh", 2, "piece"),
                make_ing("Nước mắm", 25, "ml"),
            ]
        ),
        make_recipe(
            "vn_r_23", "Nộm dưa leo thịt bò", "rau", 4,
            [
                "Thịt bò thăn thái lát mỏng, xào nhanh trên lửa lớn vừa chín tới với chút tỏi.",
                "Dưa chuột rửa sạch bỏ bớt ruột, thái lát xéo ngâm chút muối đường 10 phút rồi vắt nhẹ ráo nước.",
                "Cà rốt bào sợi, rau rau thơm mùi tàu thái khúc nhỏ.",
                "Trộn dưa leo, cà rốt với thịt bò xào, rưới nước mắm chua ngọt tỏi ớt trộn đều.",
                "Rắc đậu phộng rang giã dập lên trên đĩa nộm giòn mát."
            ],
            [
                make_ing("Dưa leo", 350, "g"),
                make_ing("Thịt bò thăn", 150, "g"),
                make_ing("Cà rốt", 80, "g"),
                make_ing("Đậu phộng", 30, "g"),
                make_ing("Nước mắm", 20, "ml"),
                make_ing("Chanh", 1, "piece"),
            ]
        ),
        make_recipe(
            "vn_r_24", "Rau lang xào tỏi", "rau", 4,
            [
                "Rau khoai lang nhặt đọt non, tước bớt phần xơ cuống lá, rửa sạch nhiều lần.",
                "Chần nhanh rau lang qua nước sôi 30 giây để giữ màu xanh mướt.",
                "Tỏi bóc vỏ đập dập thơm.",
                "Làm nóng chảo với nhiều dầu ăn, phi thơm tỏi trên lửa lớn.",
                "Cho rau lang vào đảo nhanh tay, nêm và nước mắm ngon, xào 2 phút rau vừa chín tới rồi trút ra đĩa."
            ],
            [
                make_ing("Rau khoai lang", 450, "g"),
                make_ing("Tỏi", 40, "g"),
                make_ing("Dầu ăn", 30, "ml"),
                make_ing("Nước mắm", 15, "ml"),
            ]
        ),
        make_recipe(
            "vn_r_25", "Bông bí xào tỏi", "rau", 4,
            [
                "Bông bí tước sạch phần xơ ở cuống, ngắt bỏ nhụy đắng bên trong hoa, rửa nhẹ nhàng để không dập nát.",
                "Phi thơm thật nhiều tỏi đập dập với dầu ăn trên chảo lửa lớn.",
                "Trút bông bí vào đảo nhanh tay trên lửa lớn 2 phút.",
                "Nêm nước mắm vừa ăn, khi cánh hoa vừa mềm chín giòn ngọt thì tắt bếp dọn ra đĩa."
            ],
            [
                make_ing("Bông bí", 350, "g"),
                make_ing("Tỏi", 35, "g"),
                make_ing("Dầu ăn", 25, "ml"),
                make_ing("Nước mắm", 15, "ml"),
            ]
        ),
        make_recipe(
            "vn_r_26", "Khổ qua xào trứng", "rau", 4,
            [
                "Khổ qua (mướp đắng) rửa sạch, bổ đôi nạo sạch ruột trắng, thái lát mỏng xéo.",
                "Ngâm khổ qua vào âu nước đá lạnh 10 phút để giảm vị đắng và tăng độ giòn.",
                "Đập 3 quả trứng gà vào chén, nêm tiêu đánh tan.",
                "Phi thơm hành tím trên chảo dầu nóng, cho khổ qua vào xào trên lửa lớn 2 phút vừa chín tới.",
                "Rưới trứng vào chảo, đảo đều tay nhẹ nhàng đến khi trứng chín bám quanh miếng khổ qua rồi tắt bếp."
            ],
            [
                make_ing("Khổ qua", 350, "g"),
                make_ing("Trứng gà", 3, "piece"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Dầu ăn", 25, "ml"),
                make_ing("Tiêu", 5, "g"),
            ],
            aliases=["Mướp đắng xào trứng"]
        ),
        make_recipe(
            "vn_r_27", "Măng xào tỏi ớt", "rau", 4,
            [
                "Măng củ tươi thái con chì hoặc xé sợi, luộc 2 lần nước sôi mở nắp để thải hết độc đắng, rửa sạch để ráo.",
                "Tỏi bóc vỏ băm nhỏ, ớt hiểm thái lát mỏng, hành lá cắt khúc.",
                "Phi thơm tỏi ớt trên chảo dầu nóng dậy mùi thơm cay nồng.",
                "Trút măng vào xào đều trên lửa lớn, nêm nước mắm và chút tiêu.",
                "Đảo đều khoảng 4-5 phút cho măng ngấm đượm gia vị vàng giòn, rắc hành lá rồi tắt bếp."
            ],
            [
                make_ing("Măng tươi", 400, "g"),
                make_ing("Tỏi", 25, "g"),
                make_ing("Ớt", 15, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Nước mắm", 20, "ml"),
                make_ing("Dầu ăn", 25, "ml"),
            ]
        ),
        make_recipe(
            "vn_r_28", "Rau dền luộc chấm nước mắm", "rau", 4,
            [
                "Rau dền đỏ và dền cơm nhặt lấy đọt non, rửa sạch ngâm rửa sạch 5 phút.",
                "Đun sôi nồi nước lớn với 1/2 muỗng muối hạt trên lửa lớn.",
                "Thả rau dền vào dìm ngập nước, luộc khoảng 3 phút cho rau mềm ngọt vừa tới.",
                "Vớt rau ra đĩa sâu lòng, phần nước luộc màu hồng tím ngọt mát để riêng làm canh.",
                "Chấm rau dền cùng chén nước mắm ngon dầm trứng luộc hoặc nước mắm cá cơm tỏi ớt."
            ],
            [
                make_ing("Rau dền", 450, "g"),
                make_ing("Nước mắm", 25, "ml"),
                make_ing("Ớt", 10, "g"),
            ]
        ),
        make_recipe(
            "vn_r_29", "Nộm su hào cà rốt chua ngọt", "rau", 4,
            [
                "Su hào và cà rốt gọt vỏ, bào sợi mỏng dài.",
                "Trộn sợi su hào cà rốt với 1 muỗng muối hạt trong 10 phút, sau đó vắt nhẹ bỏ bớt nước để giữ độ giòn.",
                "Rau mùi, rau thơm rửa sạch thái nhỏ.",
                "Pha nước trộn: 2 muỗng giấm, 2 muỗng đường, 1.5 muỗng nước mắm ngon, tỏi ớt băm nhuyễn.",
                "Trộn đều su hào cà rốt với nước sốt chua ngọt và rau thơm, rắc đậu phộng rang giã dập lên trên."
            ],
            [
                make_ing("Su hào", 300, "g"),
                make_ing("Cà rốt", 150, "g"),
                make_ing("Đậu phộng", 30, "g"),
                make_ing("Rau mùi", 20, "g"),
                make_ing("Giấm", 25, "ml"),
                make_ing("Đường", 25, "g"),
                make_ing("Nước mắm", 20, "ml"),
            ]
        ),
        make_recipe(
            "vn_r_30", "Bí đao xào tỏi", "rau", 4,
            [
                "Bí đao gọt vỏ, bổ đôi bỏ phần ruột xốp bên trong, thái lát mỏng vừa ăn.",
                "Tỏi bóc vỏ đập dập thơm.",
                "Làm nóng chảo với dầu ăn, phi thơm tỏi đập dập trên lửa vừa.",
                "Cho bí đao vào xào trên lửa lớn, nêm nước mắm đảo đều tay.",
                "Xào khoảng 3 phút đến khi miếng bí vừa trong chín giòn ngọt thanh, rắc hành lá tiêu xay rồi tắt bếp."
            ],
            [
                make_ing("Bí đao", 450, "g"),
                make_ing("Tỏi", 25, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Nước mắm", 15, "ml"),
                make_ing("Dầu ăn", 20, "ml"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
    ]


def get_vietnamese_canh() -> list[dict[str, Any]]:
    return [
        make_recipe(
            "vn_c_01", "Canh chua cá lóc miền Tây", "canh", 4,
            [
                "Cá lóc cắt khúc rửa sạch với chanh khử nhớt, để ráo.",
                "Cà chua bổ múi cau, thơm (dứa) thái lát, đậu bắp cắt xéo, dọc mùng tước vỏ bóp muối rửa sạch, giá đỗ rửa sạch.",
                "Me chín dầm với nước ấm lọc lấy nước cốt me chua thanh.",
                "Phi thơm tỏi băm trên nồi, cho cà chua và dứa vào xào thơm lấy màu đỏ cam đẹp.",
                "Đổ 1.2 lít nước vào đun sôi, thả cá lóc vào nấu chín trong 10 phút rồi nêm nước mắm, đường, cốt me.",
                "Thả đậu bắp, dọc mùng, giá đỗ vào đun sôi bùng lại rồi tắt bếp, rắc ngò gai rau om và tỏi phi thơm nức."
            ],
            [
                make_ing("Cá lóc", 450, "g"),
                make_ing("Cà chua", 150, "g"),
                make_ing("Dứa", 120, "g"),
                make_ing("Đậu bắp", 100, "g"),
                make_ing("Giá đỗ", 100, "g"),
                make_ing("Cốt me", 40, "g"),
                make_ing("Ngò gai", 20, "g"),
                make_ing("Nước mắm", 35, "ml"),
                make_ing("Đường", 30, "g"),
            ]
        ),
        make_recipe(
            "vn_c_02", "Canh chua tôm đậu bắp", "canh", 4,
            [
                "Tôm sú lột vỏ chừa đuôi, rút chỉ đen trên lưng, rửa sạch để ráo.",
                "Đậu bắp cắt xéo, cà chua bổ múi cau, giá đỗ rửa sạch, me ngâm nước nóng lọc nước cốt.",
                "Phi thơm hành tỏi băm trong nồi, xào cà chua cho mềm đỏ.",
                "Đổ 1 lít nước lọc và nước cốt me vào đun sôi, thả tôm vào nấu khoảng 3 phút cho tôm chuyển màu đỏ au.",
                "Cho đậu bắp và giá đỗ vào đun sôi thêm 2 phút, nêm nước mắm đường vừa vị chua ngọt đậm đà, rắc rau ngò."
            ],
            [
                make_ing("Tôm sú", 300, "g"),
                make_ing("Đậu bắp", 150, "g"),
                make_ing("Cà chua", 150, "g"),
                make_ing("Giá đỗ", 80, "g"),
                make_ing("Cốt me", 35, "g"),
                make_ing("Rau ngò", 20, "g"),
                make_ing("Nước mắm", 30, "ml"),
                make_ing("Đường", 25, "g"),
            ]
        ),
        make_recipe(
            "vn_c_03", "Canh sườn nấu sấu", "canh", 4,
            [
                "Sườn non chặt khúc 3cm, chần qua nước sôi rửa sạch bọt bẩn.",
                "Sấu cạo vỏ rửa sạch, khía vài đường quanh quả.",
                "Cà chua bổ múi cau, hành lá và rau mùi tàu thái nhỏ.",
                "Cho sườn vào nồi cùng 1.2 lít nước, đun sôi rồi vớt bọt, hầm lửa nhỏ 25 phút cho sườn mềm ngọt nước.",
                "Thả sấu và cà chua vào nấu thêm 10 phút, dầm sấu lấy vị chua thanh mát dịu, nêm nước mắm rắc hành mùi tàu."
            ],
            [
                make_ing("Sườn non heo", 450, "g"),
                make_ing("Quả sấu", 6, "piece"),
                make_ing("Cà chua", 150, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Mùi tàu", 20, "g"),
                make_ing("Nước mắm", 30, "ml"),
            ]
        ),
        make_recipe(
            "vn_c_04", "Canh sườn nấu chua dứa cà chua", "canh", 4,
            [
                "Sườn non chặt miếng vừa ăn, chần nước sôi rửa sạch.",
                "Dứa (thơm) gọt vỏ bỏ mắt, thái lát mỏng hình tam giác, cà chua bổ múi cau.",
                "Hầm sườn với 1 lít nước trên lửa vừa trong 25 phút cho thịt mềm ngọt nước.",
                "Phi thơm hành tím trên chảo xào cà chua và dứa lấy màu đẹp rồi trút vào nồi sườn.",
                "Nêm nước mắm, đường vừa vị chua ngọt thanh mát, đun sôi 3 phút rắc hành lá thì là."
            ],
            [
                make_ing("Sườn non heo", 400, "g"),
                make_ing("Dứa", 150, "g"),
                make_ing("Cà chua", 150, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Nước mắm", 25, "ml"),
            ]
        ),
        make_recipe(
            "vn_c_05", "Canh ngao nấu chua thì là", "canh", 4,
            [
                "Ngao (nghêu) ngâm nước có cắt vài lát ớt 1 tiếng cho nhả hết cát, rửa sạch vỏ ngoài.",
                "Cho ngao vào nồi với 1 lít nước đun sôi cho ngao mở miệng, vớt ngao ra nhặt lấy ruột thịt, gạn nước luộc trong.",
                "Cà chua bổ múi cau, dứa thái lát, khế chua thái lát mỏng, hành lá và thì là cắt khúc.",
                "Phi thơm hành tím, xào cà chua rồi đổ nước luộc ngao vào đun sôi cùng dứa và khế.",
                "Thả ruột ngao vào đun sôi lại, nêm nước mắm vừa ăn, tắt bếp rắc hành lá thì là thơm ngát."
            ],
            [
                make_ing("Ngao", 800, "g"),
                make_ing("Cà chua", 150, "g"),
                make_ing("Dứa", 100, "g"),
                make_ing("Thì là", 30, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Nước mắm", 20, "ml"),
            ],
            aliases=["Canh nghêu nấu chua"]
        ),
        make_recipe(
            "vn_c_06", "Canh cua rau đay mồng tơi mướp", "canh", 4,
            [
                "Cua đồng giã nhuyễn lọc lấy nước thịt cua, khêu gạch cua trong mai để riêng.",
                "Rau đay, mồng tơi nhặt lá non rửa sạch thái nhỏ, mướp gọt vỏ bổ đôi thái vát chéo.",
                "Cho nước cua vào nồi cùng 1 thìa muối nhỏ, khuấy đều rồi bắc lên bếp đun lửa vừa không đậy vung.",
                "Khi thịt cua nổi thành từng mảng gạch dày kết tủa trên mặt, nhẹ nhàng gạt thịt cua sang bên hoặc vớt riêng ra bát.",
                "Thả mướp và rau đay mồng tơi vào nồi nước sôi đun 3 phút cho rau chín xanh, nêm nước mắm vừa ăn.",
                "Trút thịt cua và gạch cua chưng thơm vào nồi canh, ăn cùng cà pháo giòn tan."
            ],
            [
                make_ing("Cua đồng", 400, "g"),
                make_ing("Rau đay", 200, "g"),
                make_ing("Rau mồng tơi", 200, "g"),
                make_ing("Mướp hương", 200, "g"),
                make_ing("Nước mắm", 25, "ml"),
            ]
        ),
        make_recipe(
            "vn_c_07", "Canh bí đỏ thịt băm", "canh", 4,
            [
                "Bí đỏ gọt vỏ, nạo bỏ ruột hạt, rửa sạch, cắt miếng vuông quân cờ vừa ăn.",
                "Thịt nạc băm ướp, tiêu và hành tím băm nhỏ 10 phút.",
                "Phi thơm hành tím trong nồi với chút dầu ăn, trút thịt băm vào xào săn chín tới.",
                "Đổ 1 lít nước vào đun sôi, thả bí đỏ vào nấu trên lửa vừa khoảng 12 phút cho bí chín mềm bùi.",
                "Nêm nước mắm vừa vị ngọt dịu, rắc rau ngò ôm (rau ngổ) và mùi tàu thái nhỏ rồi tắt bếp."
            ],
            [
                make_ing("Bí đỏ", 400, "g"),
                make_ing("Thịt heo nạc dăm", 150, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Ngò gai", 20, "g"),
                make_ing("Nước mắm", 20, "ml"),
            ]
        ),
        make_recipe(
            "vn_c_08", "Canh mướp đắng nhồi thịt", "canh", 4,
            [
                "Mướp đắng cắt khúc 4cm, dùng thìa móc sạch ruột hạt trắng bên trong, chần sơ nước sôi cho bớt đắng.",
                "Thịt nạc vai băm trộn đều với nấm mèo băm nhỏ, hành tím, chút miến cắt nhỏ, nước mắm và tiêu.",
                "Nhồi phần thịt băm vào giữa từng khúc mướp đắng, miết phẳng hai đầu.",
                "Đun sôi 1.2 lít nước hầm xương hoặc nước lọc có nêm chút muối hạt.",
                "Thả từng khúc mướp đắng nhồi thịt vào nấu nhỏ lửa mở nắp trong 20 phút cho mướp đắng chín mềm trong và nước canh ngọt thanh.",
                "Nêm nước mắm vừa ăn, rắc hành lá mùi tàu thái nhỏ."
            ],
            [
                make_ing("Khổ qua", 500, "g"),
                make_ing("Thịt heo nạc dăm", 250, "g"),
                make_ing("Nấm mèo", 20, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Nước mắm", 25, "ml"),
            ],
            aliases=["Canh khổ qua nhồi thịt"]
        ),
        make_recipe(
            "vn_c_09", "Canh bắp cải cuộn thịt", "canh", 4,
            [
                "Bắp cải tách từng lá to nguyên vẹn, chần qua nước sôi 1 phút cho lá mềm dai dễ cuộn.",
                "Thịt nạc vai xay nhuyễn trộn cùng nấm mèo, cà rốt băm nhỏ, hành tím, nước mắm, tiêu.",
                "Trải lá bắp cải ra, cho nhân thịt vào giữa rồi cuộn tròn lại như cuốn nem, buộc bằng cọng hành lá chần mềm.",
                "Đun sôi 1 lít nước dùng trên nồi, thả từng cuộn bắp cải vào nấu lửa vừa trong 15 phút.",
                "Nước canh ngọt thanh từ bắp cải và thịt băm, nêm nước mắm vừa miệng, rắc tiêu hành hoa."
            ],
            [
                make_ing("Bắp cải", 400, "g"),
                make_ing("Thịt heo nạc dăm", 250, "g"),
                make_ing("Nấm mèo", 20, "g"),
                make_ing("Cà rốt", 50, "g"),
                make_ing("Hành lá", 30, "g"),
                make_ing("Nước mắm", 20, "ml"),
            ]
        ),
        make_recipe(
            "vn_c_10", "Canh đu đủ hầm sườn non", "canh", 4,
            [
                "Đu đủ mỏ vịt (vừa hườm hoặc xanh) gọt vỏ rửa sạch mủ, cắt miếng vuông dày 3cm.",
                "Sườn non chặt khúc chần nước sôi rửa sạch bọt bẩn.",
                "Cho sườn vào nồi cùng 1.2 lít nước đun sôi vớt sạch bọt, hầm nhỏ lửa 20 phút cho ra nước ngọt.",
                "Thả đu đủ vào hầm chung thêm 15 phút đến khi đu đủ chín mềm bùi ngọt lịm.",
                "Nêm nước mắm vừa ăn, rắc hành ngò thái nhỏ và chút tiêu xay."
            ],
            [
                make_ing("Đu đủ", 450, "g"),
                make_ing("Sườn non heo", 400, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Rau ngò", 20, "g"),
                make_ing("Nước mắm", 25, "ml"),
            ]
        ),
        make_recipe(
            "vn_c_11", "Canh khoai mỡ nấu tôm thịt", "canh", 4,
            [
                "Khoai mỡ gọt vỏ, dùng dao nạo hoặc muỗng cạo nhuyễn thành bột mịn màu tím đặc trưng.",
                "Tôm bóc vỏ băm nhuyễn, thịt nạc băm nhỏ ướp chút hành tím, nước mắm, tiêu.",
                "Phi thơm hành tím băm trên nồi dầu nóng, xào săn tôm thịt băm.",
                "Đổ 1 lít nước vào đun sôi, từ từ cho khoai mỡ nạo vào khuấy đều tay theo một chiều để khoai tan mịn không vón cục.",
                "Đun sôi nhỏ lửa khoảng 8-10 phút đến khi canh khoai mỡ sánh mịn dẻo quánh, nêm nước mắm vừa ăn.",
                "Tắt bếp rắc nhiều ngò gai và rau om thái nhỏ tạo mùi thơm nức mũi."
            ],
            [
                make_ing("Khoai mỡ", 400, "g"),
                make_ing("Tôm sú", 150, "g"),
                make_ing("Thịt heo nạc dăm", 100, "g"),
                make_ing("Ngò gai", 20, "g"),
                make_ing("Rau om", 15, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Nước mắm", 25, "ml"),
            ]
        ),
        make_recipe(
            "vn_c_12", "Canh rau ngót nấu thịt băm", "canh", 4,
            [
                "Rau ngót tuốt lá, rửa sạch ngâm rửa sạch, dùng tay vò hơi dập lá để rau mềm ngọt nước khi nấu.",
                "Thịt nạc vai băm nhỏ ướp và hành tím băm.",
                "Phi thơm hành tím với 1 muỗng dầu ăn, cho thịt băm vào xào săn chín.",
                "Cho rau ngót vào xào cùng thịt khoảng 1-2 phút cho ngấm gia vị.",
                "Đổ 1 lít nước lọc vào đun sôi bùng lên trong 3-4 phút cho rau ngót chín mềm nước ngọt lịm, nêm nước mắm vừa ăn rồi tắt bếp."
            ],
            [
                make_ing("Rau ngót", 300, "g"),
                make_ing("Thịt heo nạc dăm", 150, "g"),
                make_ing("Hành tím", 15, "g"),
                make_ing("Nước mắm", 20, "ml"),
                make_ing("Dầu ăn", 15, "ml"),
            ]
        ),
        make_recipe(
            "vn_c_13", "Canh cải cúc nấu thịt băm", "canh", 4,
            [
                "Rau cải cúc (tần ô) nhặt gốc rửa sạch, cắt đôi hoặc để nguyên ngọn.",
                "Thịt nạc băm ướp và hành tím băm nhỏ.",
                "Phi thơm hành tím, xào săn thịt băm rồi đổ 1 lít nước vào đun sôi bùng.",
                "Thả rau cải cúc vào dìm ngập nước sôi, nấu nhanh trong 1-2 phút vì cải cúc rất nhanh chín.",
                "Nêm nước mắm ngon và tiêu thơm rồi tắt bếp ngay để cải cúc giữ vị ngăm ngọt thơm nồng."
            ],
            [
                make_ing("Rau cải cúc", 350, "g"),
                make_ing("Thịt heo nạc dăm", 150, "g"),
                make_ing("Hành tím", 15, "g"),
                make_ing("Nước mắm", 20, "ml"),
                make_ing("Tiêu", 5, "g"),
            ],
            aliases=["Canh tần ô thịt băm"]
        ),
        make_recipe(
            "vn_c_14", "Canh rong biển đậu hũ thịt băm", "canh", 4,
            [
                "Rong biển khô ngâm nước lạnh 10 phút cho nở to, rửa sạch bóp nhẹ ráo nước, cắt khúc vừa ăn.",
                "Đậu hũ non cắt khối vuông nhỏ 2cm.",
                "Thịt băm xào săn với chút dầu ăn và gừng băm khử mùi tanh.",
                "Đổ 1 lít nước vào đun sôi, thả đậu hũ trắng và rong biển vào nấu sôi lăn tăn trong 5 phút.",
                "Nêm nước tương ngon vừa ăn, rắc hành hoa và vài giọt dầu mè thơm ngát."
            ],
            [
                make_ing("Rong biển", 30, "g"),
                make_ing("Đậu hũ trắng", 2, "piece"),
                make_ing("Thịt heo nạc dăm", 120, "g"),
                make_ing("Gừng", 15, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Nước mắm", 15, "ml"),
            ]
        ),
        make_recipe(
            "vn_c_15", "Canh hoa thiên lý thịt bò", "canh", 4,
            [
                "Hoa thiên lý nhặt cuống sâu úa, ngâm rửa sạch 5 phút rồi rửa sạch để ráo.",
                "Thịt bò thăn thái lát mỏng ướp tỏi băm, tiêu và chút dầu ăn.",
                "Phi thơm tỏi trong nồi, xào thịt bò trên lửa lớn vừa chín tái thì trút riêng ra đĩa.",
                "Đổ 1 lít nước vào nồi đun sôi bùng, nêm nước mắm vừa ăn.",
                "Thả hoa thiên lý vào nấu sôi 1 phút cho vừa chín tới giữ độ giòn ngọt, trút thịt bò vào đảo đều rồi tắt bếp ngay."
            ],
            [
                make_ing("Hoa thiên lý", 300, "g"),
                make_ing("Thịt bò thăn", 150, "g"),
                make_ing("Tỏi", 20, "g"),
                make_ing("Nước mắm", 20, "ml"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
        make_recipe(
            "vn_c_16", "Canh kim chi đậu hũ thịt ba chỉ", "canh", 4,
            [
                "Thịt ba chỉ thái miếng mỏng vừa ăn.",
                "Kim chi cải thảo cắt khúc 3cm, giữ lại cả nước muối kim chi chua cay.",
                "Đậu hũ trắng cắt miếng vuông dày 1.5cm.",
                "Xào thịt ba chỉ trên nồi cho xém cạnh tiết bớt mỡ, cho tỏi băm và kim chi vào đảo đều 3 phút.",
                "Đổ 900ml nước lọc và nước kim chi vào đun sôi, hạ nhỏ lửa đun 10 phút cho vị chua cay ngấm đều.",
                "Thả đậu hũ trắng vào nấu sôi thêm 3 phút, nêm đường, rắc hành lá cắt khúc."
            ],
            [
                make_ing("Kim chi", 300, "g"),
                make_ing("Thịt ba chỉ", 200, "g"),
                make_ing("Đậu hũ trắng", 2, "piece"),
                make_ing("Tỏi", 15, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Đường", 10, "g"),
            ]
        ),
        make_recipe(
            "vn_c_17", "Canh sườn hầm khoai tây cà rốt", "canh", 4,
            [
                "Sườn heo chặt khúc 3cm chần nước sôi rửa sạch.",
                "Khoai tây, cà rốt gọt vỏ cắt khối vuông quân cờ vừa ăn.",
                "Cho sườn vào nồi hầm với 1.2 lít nước trên lửa vừa trong 25 phút vớt sạch bọt cho nước trong.",
                "Cho cà rốt và khoai tây vào hầm thêm 15 phút đến khi củ quả chín mềm bở bùi ngọt lịm.",
                "Nêm nước mắm vừa miệng, rắc hành lá mùi tàu thái nhỏ và tiêu xay thơm nồng."
            ],
            [
                make_ing("Sườn non heo", 450, "g"),
                make_ing("Khoai tây", 300, "g"),
                make_ing("Cà rốt", 200, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Mùi tàu", 20, "g"),
                make_ing("Nước mắm", 25, "ml"),
            ],
            aliases=["Canh súp thập cẩm"]
        ),
        make_recipe(
            "vn_c_18", "Canh hến nấu rau muống", "canh", 4,
            [
                "Hến tươi ngâm nước vo gạo 1 tiếng nhả cát, luộc sôi với nước và chút muối đến khi mở miệng.",
                "Đãi lấy phần ruột hến, gạn lấy nước luộc hến trong không cặn cát.",
                "Rau muống nhặt khúc non rửa sạch để ráo.",
                "Phi thơm hành tím, xào săn ruột hến với nước mắm tiêu rồi trút nước luộc hến vào đun sôi.",
                "Thả rau muống vào nấu sôi trên lửa lớn 2-3 phút cho rau chín giòn xanh, rắc chút gừng đập dập thơm ấm."
            ],
            [
                make_ing("Hến", 600, "g"),
                make_ing("Rau muống", 350, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Gừng", 15, "g"),
                make_ing("Nước mắm", 20, "ml"),
            ]
        ),
        make_recipe(
            "vn_c_19", "Canh cá thác lác nấu khổ qua", "canh", 4,
            [
                "Cá thác lác nạo quết thật dai dẻo với hành tím băm, tiêu xay, chút muối và thì là.",
                "Khổ qua rửa sạch bỏ ruột bào lát mỏng xéo.",
                "Đun sôi 1 lít nước lọc hoặc nước hầm xương với .",
                "Dùng thìa múc từng viên chả cá thả vào nồi nước sôi đun 5 phút cho chả cá chín nổi lên mặt.",
                "Thả khổ qua vào nấu sôi lại trong 1 phút để khổ qua chín tới giòn ngọt không đắng, nêm nước mắm rắc hành thì là."
            ],
            [
                make_ing("Cá thát lát", 250, "g"),
                make_ing("Khổ qua", 350, "g"),
                make_ing("Thì là", 20, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Nước mắm", 20, "ml"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
        make_recipe(
            "vn_c_20", "Canh chua đầu cá hồi măng chua", "canh", 4,
            [
                "Đầu cá hồi chặt miếng vừa ăn, rửa sạch bóp rượu gừng khử tanh, chiên sơ cho săn thịt.",
                "Măng chua tước sợi luộc qua một lần nước sôi rửa sạch.",
                "Cà chua bổ múi cau, dứa thái lát, me lọc lấy nước cốt.",
                "Phi thơm hành tỏi xào cà chua dứa măng chua cho ngấm vị.",
                "Đổ nước sôi vào nấu cùng đầu cá hồi trong 12 phút, nêm nước mắm đường cốt me chua cay đậm đà, rắc thì là hành lá."
            ],
            [
                make_ing("Đầu cá hồi", 500, "g"),
                make_ing("Măng chua", 200, "g"),
                make_ing("Cà chua", 150, "g"),
                make_ing("Dứa", 100, "g"),
                make_ing("Thì là", 25, "g"),
                make_ing("Nước mắm", 30, "ml"),
            ]
        ),
        make_recipe(
            "vn_c_21", "Canh bầu nấu tôm tươi", "canh", 4,
            [
                "Quả bầu non gọt vỏ, băm hoặc thái sợi mỏng dài.",
                "Tôm đồng hoặc tôm sú bóc vỏ băm nhỏ, ướp chút hành tím nước mắm tiêu.",
                "Phi thơm hành tím trên nồi dầu nóng, xào săn tôm thơm lừng.",
                "Đổ 1 lít nước vào đun sôi, thả bầu băm vào đun lửa lớn khoảng 2 phút đến khi miếng bầu trong suốt.",
                "Nêm nước mắm vừa miệng, rắc nhiều hành hoa và hành lá thơm nức mũi."
            ],
            [
                make_ing("Bầu", 500, "g"),
                make_ing("Tôm sú", 200, "g"),
                make_ing("Hành tím", 15, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Nước mắm", 20, "ml"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
        make_recipe(
            "vn_c_22", "Canh mướp hương nấu tôm khô", "canh", 4,
            [
                "Tôm khô ngâm nước ấm 15 phút cho mềm, giã hơi dập.",
                "Mướp hương gọt vỏ, bổ đôi thái vát xéo dày 1.5cm.",
                "Phi thơm hành tím, cho tôm khô vào đảo săn dậy mùi thơm đậm đà.",
                "Đổ 1 lít nước vào đun sôi 5 phút cho tôm tiết nước ngọt lịm.",
                "Thả mướp hương vào đun sôi bùng trong 2 phút đến khi mướp vừa chín tới thơm lừng, nêm nước mắm rắc hành ngò."
            ],
            [
                make_ing("Mướp hương", 450, "g"),
                make_ing("Tôm khô", 50, "g"),
                make_ing("Hành tím", 15, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Nước mắm", 20, "ml"),
            ]
        ),
        make_recipe(
            "vn_c_23", "Canh rau má nấu thịt nạc", "canh", 4,
            [
                "Rau má nhặt bỏ lá vàng rễ sâu, rửa sạch nhiều lần, ngâm rửa sạch rồi để ráo.",
                "Thịt heo nạc băm nhỏ ướp chút hành tím, nước mắm, tiêu.",
                "Phi thơm hành tím trong nồi xào chín săn thịt băm.",
                "Đổ 1 lít nước vào đun sôi bùng, thả rau má vào dìm ngập nước nấu trong 2 phút.",
                "Nêm nước mắm vừa vị thanh mát giải nhiệt, tắt bếp dọn ăn nóng hoặc nguội."
            ],
            [
                make_ing("Rau má", 350, "g"),
                make_ing("Thịt heo nạc dăm", 150, "g"),
                make_ing("Hành tím", 15, "g"),
                make_ing("Nước mắm", 20, "ml"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
        make_recipe(
            "vn_c_24", "Canh cải bẹ xanh nấu gừng cá rô", "canh", 4,
            [
                "Cá rô đồng làm sạch luộc chín với gừng, gỡ lấy thịt ướp nước mắm tiêu, phần xương giã lọc lấy nước ngọt.",
                "Cải bẹ xanh rửa sạch cắt khúc 3cm, gừng cạo vỏ thái sợi mỏng.",
                "Phi thơm hành tím xào sơ thịt cá rô cho săn thơm.",
                "Đổ nước hầm xương cá vào đun sôi cùng gừng thái sợi ấm bụng.",
                "Thả cải bẹ xanh vào nấu sôi 2 phút cho cải chín mềm vị cay thanh mát, nêm nước mắm vừa ăn."
            ],
            [
                make_ing("Cải bẹ xanh", 400, "g"),
                make_ing("Cá rô đồng", 350, "g"),
                make_ing("Gừng", 30, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Nước mắm", 25, "ml"),
            ]
        ),
        make_recipe(
            "vn_c_25", "Canh tôm nấu rau dền đỏ", "canh", 4,
            [
                "Rau dền đỏ nhặt lá non, rửa sạch để ráo nước.",
                "Tôm sú bóc vỏ băm nhỏ ướp chút muối tiêu hành tím.",
                "Xào săn tôm trên nồi với 1 muỗng dầu ăn.",
                "Đổ 1 lít nước vào đun sôi bùng, thả rau dền vào nấu lửa vừa khoảng 3 phút đến khi rau mềm chín nước có màu tím đỏ tuyệt đẹp.",
                "Nêm nước mắm ngọt lành thanh nhiệt ngày hè."
            ],
            [
                make_ing("Rau dền", 400, "g"),
                make_ing("Tôm sú", 150, "g"),
                make_ing("Hành tím", 15, "g"),
                make_ing("Nước mắm", 20, "ml"),
            ]
        ),
        make_recipe(
            "vn_c_26", "Canh cà chua trứng đậu hũ trắng", "canh", 4,
            [
                "Cà chua bổ múi cau, đậu hũ trắng cắt khối vuông nhỏ.",
                "Đập 2 quả trứng gà ra bát đánh tan đều.",
                "Phi thơm hành tím xào cà chua cho mềm nhừ đỏ au.",
                "Đổ 900ml nước lọc vào đun sôi, thả đậu hũ trắng vào nấu sôi lăn tăn 3 phút.",
                "Hạ nhỏ lửa, từ từ rưới trứng vào nồi đồng thời khuấy nhẹ theo một chiều tạo vân mây trứng bồng bềnh, rắc hành lá mùi tàu."
            ],
            [
                make_ing("Cà chua", 250, "g"),
                make_ing("Trứng gà", 2, "piece"),
                make_ing("Đậu hũ trắng", 2, "piece"),
                make_ing("Hành tím", 15, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Nước mắm", 15, "ml"),
            ]
        ),
        make_recipe(
            "vn_c_27", "Canh nấm hạt sen sườn non", "canh", 4,
            [
                "Sườn non chặt khúc chần nước sôi rửa sạch bọt bẩn.",
                "Hạt sen tươi thông tâm rửa sạch, nấm hương nấm rơm ngâm rửa sạch cắt đôi.",
                "Hầm sườn non với 1.2 lít nước trên lửa vừa trong 25 phút.",
                "Thả hạt sen và nấm vào hầm chung thêm 15 phút đến khi hạt sen bở mềm bùi ngọt nước.",
                "Nêm nước mắm vừa ăn, rắc hành ngò tiêu xay bổ dưỡng thơm dịu."
            ],
            [
                make_ing("Sườn non heo", 400, "g"),
                make_ing("Hạt sen", 150, "g"),
                make_ing("Nấm rơm", 150, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Nước mắm", 20, "ml"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
        make_recipe(
            "vn_c_28", "Canh nghêu nấu hoa thiên lý", "canh", 4,
            [
                "Nghêu ngâm ớt rửa sạch, luộc sôi với nước cho mở miệng, tách lấy ruột và gạn nước luộc trong.",
                "Hoa thiên lý nhặt rửa sạch ngâm rửa sạch để ráo.",
                "Phi thơm hành tím xào sơ ruột nghêu với nước mắm tiêu.",
                "Đổ nước luộc nghêu vào đun sôi bùng, thả hoa thiên lý vào nấu trong 1-2 phút cho vừa chín tới giữ độ giòn thơm ngọt mát.",
                "Tắt bếp nêm nếm lại rồi múc ra tô lớn thưởng thức."
            ],
            [
                make_ing("Ngao", 700, "g"),
                make_ing("Hoa thiên lý", 250, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Nước mắm", 20, "ml"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
        make_recipe(
            "vn_c_29", "Canh xà lách xoong nấu thịt bò", "canh", 4,
            [
                "Rau xà lách xoong nhặt ngọn non rửa sạch nhiều lần để ráo.",
                "Thịt bò thăn thái lát mỏng ướp tỏi băm, tiêu, chút dầu ăn.",
                "Phi thơm tỏi xào nhanh thịt bò vừa chín tái rồi múc riêng ra đĩa.",
                "Đổ 1 lít nước vào nồi đun sôi bùng nêm nước mắm vừa ăn.",
                "Thả xà lách xoong vào nấu sôi trong 1 phút, trút thịt bò vào đảo đều rồi tắt bếp ngay tránh rau nát."
            ],
            [
                make_ing("Xà lách xoong", 350, "g"),
                make_ing("Thịt bò thăn", 150, "g"),
                make_ing("Tỏi", 20, "g"),
                make_ing("Nước mắm", 20, "ml"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
        make_recipe(
            "vn_c_30", "Canh bầu nấu cá lóc", "canh", 4,
            [
                "Cá lóc làm sạch cắt khúc, ướp chút hành tím, nước mắm, tiêu trong 15 phút.",
                "Bầu non gọt vỏ thái sợi hoặc thái lát mỏng.",
                "Phi thơm hành tím xào săn cá lóc trên lửa lớn cho cá chắc thịt.",
                "Đổ 1.1 lít nước sôi vào đun nhỏ lửa 10 phút cho cá chín ngọt nước.",
                "Thả bầu vào nấu sôi bùng thêm 2 phút đến khi bầu vừa trong mềm, rắc hành ngò tiêu xay thơm nức."
            ],
            [
                make_ing("Cá lóc", 400, "g"),
                make_ing("Bầu", 450, "g"),
                make_ing("Hành tím", 20, "g"),
                make_ing("Hành lá", 20, "g"),
                make_ing("Nước mắm", 25, "ml"),
                make_ing("Tiêu", 5, "g"),
            ]
        ),
    ]


def get_international_recipes() -> list[dict[str, Any]]:
    return [
        make_recipe(
            "intl_01", "Mì Ý sốt thịt bò băm (Spaghetti Bolognese)", "man", 4,
            [
                "Luộc mì Spaghetti trong nước sôi có muối 8-10 phút cho chín tới (al dente), vớt ra xóc chút dầu oliu.",
                "Hành tây, cà rốt, cần tây băm nhỏ hạt lựu, tỏi băm nhuyễn.",
                "Phi thơm tỏi và hành tây với dầu oliu, cho thịt bò băm vào xào săn trên lửa lớn.",
                "Đổ cà chua xay nhuyễn, lá oregano và húng quế khô vào nồi sốt, nêm muối tiêu và đun nhỏ lửa om 20 phút cho sốt sánh đậm đà.",
                "Bày mì Ý ra đĩa, chan sốt bò băm nóng hổi lên trên, rắc phô mai Parmesan bào vụn."
            ],
            [
                make_ing("Mì Ý spaghetti", 350, "g"),
                make_ing("Thịt bò thăn", 350, "g"),
                make_ing("Cà chua", 300, "g"),
                make_ing("Hành tây", 100, "g"),
                make_ing("Cà rốt", 60, "g"),
                make_ing("Tỏi", 20, "g"),
                make_ing("Dầu oliu", 30, "ml"),
                make_ing("Phô mai", 30, "g"),
            ],
            area="Italian", source="international_curated_vi"
        ),
        make_recipe(
            "intl_02", "Bò bít tết sốt tiêu đen (Beef Steak)", "man", 4,
            [
                "Thịt thăn bò dày 2.5cm thấm khô nước, ướp muối biển, tiêu đen đập dập và dầu oliu 15 phút.",
                "Đun nóng chảo gang trên lửa lớn thật nóng, cho bít tết vào áp chảo 2-3 phút mỗi mặt.",
                "Cho bơ lạt, tỏi đập dập và nhánh hương thảo vào chảo, rưới bơ nóng liên tục lên miếng thịt để tạo lớp vỏ nâu giòn mọng nước.",
                "Gắp thịt ra đĩa để nghỉ 5 phút giữ trọn độ ngọt mọng bên trong.",
                "Pha sốt tiêu đen từ bơ, tiêu đen sọ giã dập, dầu hào, nước tương đun sôi sánh, rưới lên bít tết dùng kèm khoai tây chiên."
            ],
            [
                make_ing("Thịt bò thăn", 600, "g"),
                make_ing("Bơ", 40, "g"),
                make_ing("Tỏi", 25, "g"),
                make_ing("Tiêu", 15, "g"),
                make_ing("Khoai tây", 300, "g"),
                make_ing("Dầu oliu", 30, "ml"),
            ],
            area="Western", source="international_curated_vi"
        ),
        make_recipe(
            "intl_03", "Cá hồi áp chảo sốt bơ chanh tỏi", "man", 4,
            [
                "Phi lê cá hồi rửa sạch thấm khô nước, ướp muối, tiêu và chút dầu oliu 10 phút.",
                "Làm nóng chảo với chút dầu oliu, đặt mặt da cá xuống áp chảo lửa vừa 4 phút cho da vàng giòn rụm.",
                "Lật mặt thịt cá áp chảo thêm 2 phút cho cá chín tới mọng nước rồi gắp ra đĩa.",
                "Hạ nhỏ lửa, cho bơ lạt vào chảo phi thơm tỏi băm, vắt nước cốt chanh vàng và chút hành lá thái nhỏ khuấy đều.",
                "Rưới sốt bơ chanh tỏi thơm béo ngậy lên miếng cá hồi, ăn kèm măng tây hoặc khoai tây nghiền."
            ],
            [
                make_ing("Cá hồi", 500, "g"),
                make_ing("Bơ", 35, "g"),
                make_ing("Chanh", 1, "piece"),
                make_ing("Tỏi", 20, "g"),
                make_ing("Măng tây", 200, "g"),
                make_ing("Dầu oliu", 20, "ml"),
            ],
            area="Western", source="international_curated_vi"
        ),
        make_recipe(
            "intl_04", "Bò cuộn nấm kim châm áp chảo", "man", 4,
            [
                "Thịt bò ba chỉ thái dải dài mỏng chuyên dùng cuộn nấm.",
                "Nấm kim châm cắt gốc, rửa sạch chia thành các phần nhỏ.",
                "Trải dải thịt bò ra, đặt nấm kim châm vào giữa rồi cuộn tròn chặt tay.",
                "Pha nước sốt: 2 muỗng nước tương, 1 muỗng dầu hào, 1 muỗng đường, 1/2 muỗng tiêu, 3 muỗng nước.",
                "Áp chảo các cuộn thịt bò trên chảo nóng cho vàng xém các mặt, đổ nước sốt vào đảo đều 2 phút cho bóng đẹp rồi tắt bếp."
            ],
            [
                make_ing("Thịt bò thăn", 400, "g"),
                make_ing("Nấm kim châm", 300, "g"),
                make_ing("Nước tương", 30, "ml"),
                make_ing("Dầu hào", 20, "ml"),
                make_ing("Đường", 15, "g"),
            ],
            area="Japanese", source="international_curated_vi"
        ),
        make_recipe(
            "intl_05", "Cơm chiên kim chi phô mai Hàn Quốc", "man", 4,
            [
                "Kim chi cải thảo thái nhỏ, thịt ba chỉ hoặc xúc xích thái hạt lựu.",
                "Xào săn thịt ba chỉ trên chảo lửa lớn cho xém cạnh, trút kim chi và 1 muỗng tương ớt Hàn Quốc (Gochujang) vào xào thơm.",
                "Cho cơm nguội vào chảo dằm tơi hạt cơm, đảo đều tay trên lửa lớn cho hạt cơm săn bóng ngấm vị chua cay.",
                "Tạo khoảng trống ở giữa chảo, cho phô mai Mozzarella bào sợi vào đậy vung hạ nhỏ lửa 2 phút cho phô mai tan chảy kéo sợi.",
                "Rắc rong biển vụn và mè rang thơm lừng lên trên chảo cơm chiên nóng hổi."
            ],
            [
                make_ing("Cơm nguội", 500, "g"),
                make_ing("Kim chi", 250, "g"),
                make_ing("Thịt ba chỉ", 150, "g"),
                make_ing("Phô mai", 80, "g"),
                make_ing("Rong biển", 15, "g"),
                make_ing("Dầu ăn", 25, "ml"),
            ],
            area="Korean", source="international_curated_vi"
        ),
        make_recipe(
            "intl_06", "Cơm chiên Dương Châu lạp xưởng tôm", "man", 4,
            [
                "Lạp xưởng luộc sơ thái hạt lựu, tôm sú bóc vỏ thái hạt lựu.",
                "Cà rốt, đậu cô ve chần sơ nước sôi thái hạt lựu, trứng gà đánh tan chiên mỏng thái sợi.",
                "Trộn cơm nguội với 1 lòng đỏ trứng gà và chút dầu ăn để hạt cơm áo màu vàng óng.",
                "Phi thơm hành tỏi trên chảo lớn lửa to, xào tôm lạp xưởng cho săn thơm rồi trút rau củ vào đảo đều.",
                "Cho cơm vào đảo nhanh tay trên lửa lớn đến khi hạt cơm săn giòn tách rời, nêm nước tương tiêu rắc hành hoa."
            ],
            [
                make_ing("Cơm nguội", 500, "g"),
                make_ing("Tôm sú", 150, "g"),
                make_ing("Lạp xưởng", 100, "g"),
                make_ing("Trứng gà", 2, "piece"),
                make_ing("Cà rốt", 80, "g"),
                make_ing("Đậu cô ve", 80, "g"),
                make_ing("Hành lá", 20, "g"),
            ],
            area="Chinese", source="international_curated_vi"
        ),
        make_recipe(
            "intl_07", "Cà ri gà kiểu Nhật Bản", "man", 4,
            [
                "Thịt đùi gà rút xương cắt miếng vuông 3cm, khoai tây và cà rốt gọt vỏ cắt khối vừa ăn, hành tây thái múi cau.",
                "Xào thịt gà trên nồi lớn với chút dầu ăn cho săn vàng mặt ngoài.",
                "Cho hành tây, khoai tây và cà rốt vào xào chung trong 3 phút.",
                "Đổ 800ml nước vào đun sôi vớt bọt, hạ nhỏ lửa hầm 15 phút cho củ quả chín mềm.",
                "Thả viên sốt cà ri Nhật (hoặc bột cà ri) vào khuấy tan hoàn toàn, đun liu riu thêm 5 phút đến khi sốt cà ri sánh mịn thơm nức."
            ],
            [
                make_ing("Thịt gà", 500, "g"),
                make_ing("Khoai tây", 250, "g"),
                make_ing("Cà rốt", 180, "g"),
                make_ing("Hành tây", 150, "g"),
                make_ing("Bột cà ri", 60, "g"),
                make_ing("Dầu ăn", 20, "ml"),
            ],
            area="Japanese", source="international_curated_vi"
        ),
        make_recipe(
            "intl_08", "Gà sốt cay ngọt Hàn Quốc (Dakgangjeong)", "man", 4,
            [
                "Thịt đùi hoặc cánh gà chặt miếng vừa ăn, ướp muối tiêu gừng băm trong 15 phút.",
                "Lăn thịt gà qua lớp bột mì rồi chiên ngập dầu lần 1 trên lửa vừa đến khi chín vàng nhạt.",
                "Vớt gà ra để nghỉ 5 phút rồi chiên lại lần 2 trên lửa lớn trong 2 phút để lớp vỏ giòn tan không ngấy mỡ.",
                "Pha sốt: tương ớt Gochujang, tương cà, mật ong, nước tương, tỏi băm đun sôi sủi bọt trong chảo lớn.",
                "Trút gà chiên giòn vào chảo sốt đảo thật nhanh tay cho sốt bám đều óng ánh, rắc mè rang thơm."
            ],
            [
                make_ing("Thịt gà", 600, "g"),
                make_ing("Tỏi", 25, "g"),
                make_ing("Mật ong", 40, "g"),
                make_ing("Tương cà", 30, "g"),
                make_ing("Tương ớt", 30, "g"),
                make_ing("Mè rang", 15, "g"),
                make_ing("Dầu ăn", 150, "ml"),
            ],
            area="Korean", source="international_curated_vi"
        ),
        make_recipe(
            "intl_09", "Thịt heo chiên xù kiểu Nhật (Tonkatsu)", "man", 4,
            [
                "Thịt thăn heo dày 1.5cm, dùng búa dần thịt đập nhẹ hai mặt cho mềm thớ, ướp muối tiêu.",
                "Chuẩn bị 3 đĩa: bột mì, trứng gà đánh tan, bột chiên xù (panko).",
                "Lăn miếng thịt lần lượt qua bột mì, nhúng ngập trứng rồi áo đều lớp bột chiên xù bên ngoài.",
                "Thả thịt vào chảo dầu nóng 170°C chiên ngập dầu khoảng 5-6 phút đến khi vỏ ngoài vàng ruộm giòn tan.",
                "Gắp thịt ra để ráo dầu, cắt thành từng thanh dài, dọn kèm bắp cải thái sợi mỏng và sốt Tonkatsu mè rang."
            ],
            [
                make_ing("Thịt heo nạc dăm", 500, "g"),
                make_ing("Trứng gà", 2, "piece"),
                make_ing("Bột chiên xù", 120, "g"),
                make_ing("Bắp cải", 200, "g"),
                make_ing("Dầu ăn", 200, "ml"),
            ],
            area="Japanese", source="international_curated_vi"
        ),
        make_recipe(
            "intl_10", "Salad cá ngừ trứng luộc sốt Mayonnaise", "rau", 4,
            [
                "Xà lách rửa sạch ngâm nước đá cho giòn ráo, xé miếng vừa ăn.",
                "Cà chua bi bổ đôi, dưa leo thái lát tròn, hành tây thái mỏng ngâm giấm đường khử hăng.",
                "Trứng gà luộc chín tới, bóc vỏ bổ múi cau.",
                "Cá ngừ ngâm dầu đóng hộp chắt bớt dầu, dằm nhẹ thành miếng nhỏ.",
                "Xếp xà lách, cà chua, dưa leo ra đĩa lớn, cho cá ngừ và trứng luộc lên trên, rưới sốt Mayonnaise pha chút cốt chanh và tiêu xay."
            ],
            [
                make_ing("Xà lách", 250, "g"),
                make_ing("Cá ngừ đóng hộp", 180, "g"),
                make_ing("Trứng gà", 3, "piece"),
                make_ing("Cà chua bi", 100, "g"),
                make_ing("Dưa leo", 120, "g"),
                make_ing("Sốt mayonnaise", 50, "g"),
            ],
            area="Western", source="international_curated_vi"
        ),
        make_recipe(
            "intl_11", "Salad Caesar ức gà nướng", "rau", 4,
            [
                "Ức gà ướp tiêu, dầu oliu và tỏi băm, áp chảo chín vàng hai mặt rồi thái lát xéo.",
                "Rau xà lách Romaine rửa sạch ngắt khúc 4cm để ráo nước thật giòn.",
                "Bánh mì sandwich cắt hạt lựu nướng vàng giòn với chút bơ tỏi.",
                "Pha sốt Caesar: sốt mayonnaise, phô mai Parmesan bào, tỏi băm, nước cốt chanh vàng, tiêu đen.",
                "Trộn đều xà lách với sốt Caesar, xếp ức gà nướng và bánh mì giòn lên trên, rắc thêm phô mai Parmesan bào nhuyễn."
            ],
            [
                make_ing("Ức gà", 300, "g"),
                make_ing("Xà lách", 250, "g"),
                make_ing("Bánh mì", 100, "g"),
                make_ing("Phô mai", 40, "g"),
                make_ing("Sốt mayonnaise", 40, "g"),
                make_ing("Chanh", 1, "piece"),
            ],
            area="Western", source="international_curated_vi"
        ),
        make_recipe(
            "intl_12", "Salad Nga thập cẩm khoai tây jambon", "rau", 4,
            [
                "Khoai tây, cà rốt gọt vỏ cắt hạt lựu, luộc chín mềm vừa tới rồi vớt ra ngâm nước lạnh cho ráo.",
                "Đậu Hà Lan và bắp ngọt chần sơ nước sôi.",
                "Thịt nguội jambon thái hạt lựu, dưa leo muối thái hạt lựu.",
                "Trứng gà luộc chín bóc vỏ cắt hạt lựu.",
                "Cho toàn bộ các nguyên liệu vào âu lớn, thêm sốt Mayonnaise, chút muối tiêu trộn nhẹ tay cho sốt bao đều rồi để ngăn mát 30 phút."
            ],
            [
                make_ing("Khoai tây", 250, "g"),
                make_ing("Cà rốt", 150, "g"),
                make_ing("Thịt nguội", 150, "g"),
                make_ing("Trứng gà", 2, "piece"),
                make_ing("Đậu Hà Lan", 80, "g"),
                make_ing("Sốt mayonnaise", 70, "g"),
            ],
            area="Russian", source="international_curated_vi"
        ),
        make_recipe(
            "intl_13", "Súp gà kem bắp non kiểu Âu", "canh", 4,
            [
                "Ức gà luộc chín xé sợi mỏng, giữ lại nước luộc gà ngọt thanh.",
                "Bắp ngọt tách hạt luộc chín, nấm hương ngâm nở thái sợi mỏng.",
                "Đun sôi nước luộc gà, cho bắp non, nấm hương và gà xé vào nấu trên lửa vừa 10 phút.",
                "Hòa tan bột mì với nước lọc, từ từ đổ vào nồi súp khuấy đều tay đến khi súp sánh mịn.",
                "Đánh tan lòng trắng trứng, rưới từ từ qua rây vào nồi súp khuấy nhẹ tạo vân sợi trắng đẹp mắt, thêm chút kem sữa tươi rắc tiêu ngò."
            ],
            [
                make_ing("Ức gà", 250, "g"),
                make_ing("Bắp ngọt", 200, "g"),
                make_ing("Trứng gà", 2, "piece"),
                make_ing("Nấm hương", 40, "g"),
                make_ing("Kem tươi", 50, "ml"),
                make_ing("Hành lá", 15, "g"),
                make_ing("Tiêu", 5, "g"),
            ],
            area="Western", source="international_curated_vi"
        ),
        make_recipe(
            "intl_14", "Súp bí đỏ kem sữa tươi kiểu Pháp", "canh", 4,
            [
                "Bí đỏ gọt vỏ bỏ hạt cắt miếng nhỏ, hành tây thái hạt lựu.",
                "Làm nóng nồi với 20g bơ lạt, phi thơm hành tây cho mềm thơm.",
                "Cho bí đỏ vào xào cùng hành tây 3 phút, đổ 600ml nước hầm xương vào đun sôi hầm 15 phút cho bí chín mềm nhừ.",
                "Dùng máy xay cầm tay xay nhuyễn mịn trực tiếp trong nồi.",
                "Đổ sữa tươi không đường và kem sữa đặc vào khuấy đều trên lửa nhỏ, nêm chút muối tiêu vừa vị béo ngậy mịn màng."
            ],
            [
                make_ing("Bí đỏ", 500, "g"),
                make_ing("Hành tây", 80, "g"),
                make_ing("Bơ", 30, "g"),
                make_ing("Sữa tươi", 150, "ml"),
                make_ing("Kem tươi", 60, "ml"),
            ],
            area="French", source="international_curated_vi"
        ),
        make_recipe(
            "intl_15", "Mì Udon xào thịt bò và rau cải", "man", 4,
            [
                "Mì Udon chần qua nước sôi 1 phút cho sợi mì tơi mềm, xả nước lạnh để ráo.",
                "Thịt bò thái lát mỏng ướp nước tương, dầu hào và tiêu.",
                "Bắp cải, cà rốt thái sợi, hành tây bổ múi cau.",
                "Xào thịt bò trên lửa lớn vừa chín tái thì gắp riêng ra đĩa.",
                "Xào rau củ chín giòn, cho mì Udon và thịt bò vào cùng sốt xào Nhật Bản đảo đều tay trên lửa lớn 2 phút rồi rắc mè rang."
            ],
            [
                make_ing("Mì udon", 400, "g"),
                make_ing("Thịt bò thăn", 250, "g"),
                make_ing("Bắp cải", 150, "g"),
                make_ing("Cà rốt", 80, "g"),
                make_ing("Hành tây", 60, "g"),
                make_ing("Nước tương", 30, "ml"),
            ],
            area="Japanese", source="international_curated_vi"
        ),
        make_recipe(
            "intl_16", "Canh rong biển truyền thống Hàn Quốc (Miyeokguk)", "canh", 4,
            [
                "Rong biển khô ngâm nước lạnh 15 phút cho nở to, vắt ráo cắt khúc 4cm.",
                "Thịt bò thái mỏng ướp tỏi băm, nước tương và 1 muỗng dầu mè thơm.",
                "Xào thịt bò với dầu mè trong nồi đến khi săn chín.",
                "Cho rong biển vào xào chung cùng thịt bò 2 phút cho rong biển ngấm đượm dầu mè.",
                "Đổ 1 lít nước lọc vào đun sôi, hạ nhỏ lửa đun liu riu 20 phút cho nước canh ngọt thanh đậm đà, nêm nước tương Hàn Quốc."
            ],
            [
                make_ing("Rong biển", 35, "g"),
                make_ing("Thịt bò thăn", 150, "g"),
                make_ing("Tỏi", 20, "g"),
                make_ing("Dầu mè", 20, "ml"),
                make_ing("Nước tương", 25, "ml"),
            ],
            area="Korean", source="international_curated_vi"
        ),
        make_recipe(
            "intl_17", "Cánh gà nướng sốt BBQ mật ong", "man", 4,
            [
                "Cánh gà rửa sạch khía vài đường trên mình thịt cho ngấm gia vị.",
                "Pha sốt ướp: sốt BBQ, mật ong, nước tương, dầu hào, tỏi băm, tiêu xay.",
                "Ướp cánh gà với sốt BBQ trong ít nhất 30 phút (hoặc để ngăn mát qua đêm).",
                "Xếp gà vào khay nướng ở 190°C trong 20 phút, lật mặt quét thêm lớp sốt mật ong.",
                "Nướng tiếp 10 phút đến khi da gà cánh gián nâu bóng vàng giòn thơm nức mũi."
            ],
            [
                make_ing("Thịt gà", 650, "g"),
                make_ing("Sốt BBQ", 50, "g"),
                make_ing("Mật ong", 30, "g"),
                make_ing("Tỏi", 20, "g"),
                make_ing("Nước tương", 20, "ml"),
            ],
            area="Western", source="international_curated_vi"
        ),
        make_recipe(
            "intl_18", "Cơm gà Teriyaki kiểu Nhật", "man", 4,
            [
                "Thịt má đùi gà rút xương khía nhẹ mặt thịt, ướp chút muối tiêu.",
                "Pha sốt Teriyaki: 3 muỗng nước tương Nhật, 2 muỗng rượu Mirin (hoặc giấm táo), 2 muỗng đường, 1 muỗng gừng băm.",
                "Áp chảo thịt gà với mặt da xuống trước trên lửa vừa đến khi da vàng giòn, lật mặt thịt áp chảo thêm 3 phút.",
                "Đổ sốt Teriyaki vào chảo đun sôi liu riu, lật đều hai mặt miếng gà đến khi sốt keo sánh bám óng ánh quanh miếng thịt.",
                "Cắt gà thành từng dải dày xếp lên tô cơm nóng, rưới sốt Teriyaki và rắc mè trắng rang."
            ],
            [
                make_ing("Thịt gà", 500, "g"),
                make_ing("Nước tương", 40, "ml"),
                make_ing("Đường", 25, "g"),
                make_ing("Gừng", 15, "g"),
                make_ing("Mè rang", 10, "g"),
                make_ing("Cơm nóng", 500, "g"),
            ],
            area="Japanese", source="international_curated_vi"
        ),
        make_recipe(
            "intl_19", "Bò hầm rượu vang kiểu Pháp (Boeuf Bourguignon)", "man", 4,
            [
                "Nạm bò hoặc bắp bò cắt khối vuông 3.5cm, ướp muối tiêu và chút rượu vang 20 phút.",
                "Áp chảo thịt bò trên nồi gang lửa lớn cho xém vàng các mặt rồi gắp ra.",
                "Xào hành tây, cà rốt, nấm hương và tỏi băm thơm nức.",
                "Trút thịt bò trở lại nồi, đổ 200ml rượu vang đỏ và 500ml nước hầm xương ngập mặt thịt.",
                "Hầm lửa nhỏ liu riu trong 50 phút đến khi thịt bò mềm tan trong miệng, nước sốt rượu vang nâu sánh đậm đà."
            ],
            [
                make_ing("Thịt bò thăn", 600, "g"),
                make_ing("Cà rốt", 200, "g"),
                make_ing("Khoai tây", 200, "g"),
                make_ing("Hành tây", 100, "g"),
                make_ing("Nấm hương", 60, "g"),
                make_ing("Bơ", 30, "g"),
            ],
            area="French", source="international_curated_vi"
        ),
        make_recipe(
            "intl_20", "Bánh kếp kim chi hải sản Hàn Quốc (Haemul Kimchijeon)", "man", 4,
            [
                "Mực và tôm bóc vỏ cắt miếng nhỏ, kim chi cải thảo thái nhỏ vắt nhẹ ráo nước.",
                "Hành lá rửa sạch cắt khúc dài 6cm.",
                "Pha bột bánh: bột mì, bột mì, 1 quả trứng gà, nước kim chi khuấy tan thành hỗn hợp sánh sệt vừa phải.",
                "Trộn hải sản, kim chi và hành lá vào tô bột.",
                "Đun nóng chảo dầu, múc bột trải đều thành lớp bánh mỏng, chiên lửa vừa đến khi hai mặt vàng ruộm giòn tan chấm nước tương ớt."
            ],
            [
                make_ing("Tôm sú", 150, "g"),
                make_ing("Mực ống", 150, "g"),
                make_ing("Kim chi", 150, "g"),
                make_ing("Hành lá", 60, "g"),
                make_ing("Trứng gà", 1, "piece"),
                make_ing("Bột mì", 120, "g"),
                make_ing("Dầu ăn", 50, "ml"),
            ],
            area="Korean", source="international_curated_vi"
        ),
        make_recipe(
            "intl_21", "Súp kem nấm gà kiểu Âu", "canh", 4,
            [
                "Nấm rơm hoặc nấm mỡ rửa sạch thái lát mỏng, thịt ức gà thái hạt lựu nhỏ.",
                "Làm nóng chảo với bơ lạt, phi thơm hành tây băm nhỏ.",
                "Cho nấm và ức gà vào xào săn trên lửa vừa trong 4 phút.",
                "Đổ 600ml nước luộc gà vào đun sôi hầm 10 phút.",
                "Thêm sữa tươi và kem tươi khuấy đều, hòa tan chút bột mì tạo độ sánh mịn như nhung, rắc tiêu đen thơm ngát."
            ],
            [
                make_ing("Nấm rơm", 250, "g"),
                make_ing("Ức gà", 200, "g"),
                make_ing("Hành tây", 80, "g"),
                make_ing("Bơ", 30, "g"),
                make_ing("Sữa tươi", 150, "ml"),
                make_ing("Kem tươi", 60, "ml"),
                make_ing("Tiêu", 5, "g"),
            ],
            area="Western", source="international_curated_vi"
        ),
        make_recipe(
            "intl_22", "Trứng ốp la xúc xích đậu hầm sốt cà (English Breakfast)", "man", 4,
            [
                "Xúc xích khía nhẹ thân, áp chảo vàng đều các mặt trên chảo bơ.",
                "Thịt xông khói áp chảo giòn thơm.",
                "Cà chua bổ đôi áp chảo xém cạnh ngọt thơm.",
                "Ốp la 4 quả trứng gà giữ lòng đào béo ngậy.",
                "Hâm nóng đậu trắng hầm sốt cà chua, bày toàn bộ ra đĩa lớn ăn kèm bánh mì nướng giòn."
            ],
            [
                make_ing("Trứng gà", 4, "piece"),
                make_ing("Xúc xích", 200, "g"),
                make_ing("Thịt xông khói", 120, "g"),
                make_ing("Cà chua", 150, "g"),
                make_ing("Bánh mì", 150, "g"),
                make_ing("Bơ", 25, "g"),
            ],
            area="British", source="international_curated_vi"
        ),
        make_recipe(
            "intl_23", "Cá hồi đút lò phô mai", "man", 4,
            [
                "Cá hồi phi lê rửa sạch thấm khô, ướp chút muối tiêu và dầu oliu.",
                "Pha hỗn hợp phủ mặt cá: phô mai bào, tỏi băm, rau mùi tây băm nhuyễn và chút sốt mayonnaise.",
                "Phết đều lớp sốt phô mai lên trên từng miếng cá hồi.",
                "Cho vào lò nướng hoặc nồi chiên không dầu ở 180°C trong 12-14 phút.",
                "Lớp phô mai chảy vàng óng xém mặt thơm béo ngậy quyện cùng thịt cá hồi ngọt mềm mọng nước."
            ],
            [
                make_ing("Cá hồi", 500, "g"),
                make_ing("Phô mai", 80, "g"),
                make_ing("Sốt mayonnaise", 30, "g"),
                make_ing("Tỏi", 15, "g"),
                make_ing("Dầu oliu", 15, "ml"),
            ],
            area="Western", source="international_curated_vi"
        ),
        make_recipe(
            "intl_24", "Thịt heo xào kim chi cay Hàn Quốc", "man", 4,
            [
                "Thịt ba chỉ thái lát mỏng vừa ăn.",
                "Kim chi cải thảo chua cay cắt khúc ngắn 3cm.",
                "Hành tây thái múi cau, hành boa-rô cắt xéo.",
                "Xào thịt ba chỉ trên chảo lửa lớn cho xém cạnh tiết bớt mỡ, cho tỏi băm và kim chi vào đảo đều 4 phút.",
                "Nêm 1 muỗng tương ớt Gochujang, 1 muỗng nước tương, 1 muỗng đường đảo đều tay, rắc hành boa-rô và mè rang."
            ],
            [
                make_ing("Thịt ba chỉ", 350, "g"),
                make_ing("Kim chi", 250, "g"),
                make_ing("Hành tây", 80, "g"),
                make_ing("Tỏi", 20, "g"),
                make_ing("Mè rang", 10, "g"),
            ],
            area="Korean", source="international_curated_vi"
        ),
        make_recipe(
            "intl_25", "Mì xào hải sản kiểu Singapore", "man", 4,
            [
                "Mì trứng chần nước sôi xả nước lạnh cho sợi mì tơi giòn.",
                "Tôm bóc vỏ, mực khía hoa cắt miếng vừa ăn xào chín tới rồi múc ra đĩa.",
                "Cải ngọt, cà rốt thái sợi, giá đỗ rửa sạch.",
                "Phi thơm tỏi ớt xào rau củ chín giòn, cho mì trứng và hải sản vào đảo nhanh tay trên lửa lớn.",
                "Rưới sốt xào hải sản dầu hào nước tương tiêu vào đảo đều trong 2 phút rồi rắc hành ngò tiêu xay."
            ],
            [
                make_ing("Mì trứng", 300, "g"),
                make_ing("Tôm sú", 150, "g"),
                make_ing("Mực ống", 150, "g"),
                make_ing("Cải ngọt", 150, "g"),
                make_ing("Giá đỗ", 100, "g"),
                make_ing("Dầu hào", 25, "ml"),
            ],
            area="Asian", source="international_curated_vi"
        ),
    ]


def main() -> None:
    vn_recipes = get_vietnamese_man() + get_vietnamese_rau() + get_vietnamese_canh()
    intl_recipes = get_international_recipes()

    print(f"-> Ghi {len(vn_recipes)} mon an Viet Nam vao {VN_OUT}...")
    with VN_OUT.open("w", encoding="utf-8") as f:
        for r in vn_recipes:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"-> Ghi {len(intl_recipes)} mon an quoc te da dich vao {INTL_OUT}...")
    with INTL_OUT.open("w", encoding="utf-8") as f:
        for r in intl_recipes:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("HOAN TAT! Bo du lieu am thuc Viet & Quoc te dich chuan da duoc bien soan.")


if __name__ == "__main__":
    main()
