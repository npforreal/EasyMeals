"""Module và CLI dịch tên nguyên liệu (Anh -> Việt) dùng cho EasyMeals.

Script này được thiết kế để tái sử dụng trong tương lai cho bất kỳ nguồn dữ liệu
nguyên liệu nào (TheMealDB, OpenFoodFacts, USDA, công thức cào mới...).

Tính năng:
- Lưu trữ từ điển bản dịch độc lập tại `data/ingredient_translations.json`.
- Bảo toàn bản dịch thủ công đã có (không ghi đè trừ khi có cờ --force).
- Quy tắc tách từ và dịch ghép ẩm thực thông minh (modifiers: dried, ground, smoked, fresh...
  và suffixes: powder, sauce, oil, seeds, leaves...).
- CLI báo cáo tỷ lệ bao phủ, danh sách cần dịch thêm hoặc xuất JSON chuẩn.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from translate_recipes import VN_CHARS

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = ROOT / "data" / "open" / "ingredients.jsonl"
DEFAULT_DICT = ROOT / "data" / "ingredient_translations.json"

# Tiền tố / Tính từ mô tả cách sơ chế, chế biến ẩm thực
MODIFIERS: dict[str, str] = {
    "ground": "xay",
    "minced": "băm",
    "chopped": "thái nhỏ",
    "diced": "cắt hạt lựu",
    "sliced": "thái lát",
    "shredded": "bào sợi",
    "grated": "bào vụn",
    "crushed": "nghiền",
    "mashed": "nghiền",
    "dried": "khô",
    "dry": "khô",
    "fresh": "tươi",
    "frozen": "đông lạnh",
    "roasted": "rang",
    "toasted": "nướng",
    "smoked": "hun khói",
    "cooked": "chín",
    "boiled": "luộc",
    "steamed": "hấp",
    "fried": "chiên",
    "raw": "sống",
    "boneless": "rút xương",
    "skinless": "bỏ da",
    "canned": "đóng hộp",
    "tinned": "đóng hộp",
    "pickled": "muối chua",
    "salted": "muối",
    "fermented": "lên men",
    "sweet": "ngọt",
    "sour": "chua",
    "spicy": "cay",
    "hot": "cay",
    "lean": "nạc",
    "whole": "nguyên hạt",
    "organic": "hữu cơ",
    "white": "trắng",
    "black": "đen",
    "red": "đỏ",
    "green": "xanh",
    "yellow": "vàng",
    "brown": "nâu",
    "baby": "baby",
    "extra virgin": "nguyên chất",
}

# Hậu tố / Danh từ dạng chế phẩm ẩm thực
SUFFIXES: dict[str, str] = {
    "powder": "bột",
    "flour": "bột mì",
    "paste": "sốt đặc",
    "puree": "nhuyễn",
    "sauce": "sốt",
    "dip": "sốt chấm",
    "oil": "dầu",
    "vinegar": "giấm",
    "syrup": "siro",
    "juice": "nước ép",
    "water": "nước",
    "milk": "sữa",
    "cream": "kem",
    "butter": "bơ",
    "extract": "chiết xuất",
    "broth": "nước dùng",
    "stock": "nước hầm",
    "seeds": "hạt",
    "seed": "hạt",
    "leaves": "lá",
    "leaf": "lá",
    "roots": "rễ",
    "root": "củ",
    "fillet": "phi lê",
    "fillets": "phi lê",
    "steak": "bít tết",
    "cutlets": "cốt lết",
    "chop": "sườn",
    "chops": "sườn",
    "ribs": "sườn",
    "flakes": "vụn",
    "cubes": "viên",
    "pieces": "miếng",
    "slices": "lát",
}

# Từ điển ẩm thực cơ sở phong phú (Anh -> Việt)
BASE_LEXICON: dict[str, str] = {
    # Thịt & Gia cầm
    "chicken": "Thịt gà",
    "chicken breast": "Ức gà",
    "chicken breasts": "Ức gà",
    "chicken thigh": "Đùi gà",
    "chicken thighs": "Đùi gà",
    "chicken leg": "Má đùi gà",
    "chicken legs": "Má đùi gà",
    "chicken wing": "Cánh gà",
    "chicken wings": "Cánh gà",
    "chicken drumsticks": "Tỏi gà",
    "chicken drumstick": "Tỏi gà",
    "chicken liver": "Gan gà",
    "chicken stock": "Nước dùng gà",
    "chicken broth": "Nước dùng gà",
    "pork": "Thịt heo",
    "pork belly": "Thịt ba chỉ heo",
    "pork chops": "Sườn cốt lết heo",
    "pork loin": "Thịt thăn heo",
    "pork shoulder": "Thịt vai heo",
    "pork mince": "Thịt heo xay",
    "ground pork": "Thịt heo xay",
    "bacon": "Thịt xông khói",
    "ham": "Giăm bông",
    "sausage": "Xúc xích",
    "sausages": "Xúc xích",
    "chorizo": "Xúc xích Chorizo",
    "prosciutto": "Thịt muối Prosciutto",
    "pancetta": "Thịt ba chỉ muối Pancetta",
    "beef": "Thịt bò",
    "ground beef": "Thịt bò xay",
    "beef mince": "Thịt bò xay",
    "beef brisket": "Gầu bò",
    "beef fillet": "Thăn bò",
    "beef sirloin": "Thăn ngoại bò",
    "beef steak": "Bít tết bò",
    "beef stock": "Nước dùng bò",
    "beef broth": "Nước hầm bò",
    "beef gravy": "Sốt thịt bò",
    "veal": "Thịt bê",
    "lamb": "Thịt cừu",
    "ground lamb": "Thịt cừu xay",
    "lamb chops": "Sườn cừu",
    "lamb shoulder": "Thịt vai cừu",
    "lamb leg": "Đùi cừu",
    "mutton": "Thịt cừu già",
    "duck": "Thịt vịt",
    "duck breast": "Ức vịt",
    "duck legs": "Đùi vịt",
    "turkey": "Thịt gà tây",
    "ground turkey": "Thịt gà tây xay",
    "turkey breast": "Ức gà tây",
    "quail": "Chim cút",
    "rabbit": "Thịt thỏ",
    "venison": "Thịt nai",
    # Cá & Hải sản
    "fish": "Cá",
    "salmon": "Cá hồi",
    "salmon fillet": "Phi lê cá hồi",
    "smoked salmon": "Cá hồi hun khói",
    "tuna": "Cá ngừ",
    "tuna steak": "Bít tết cá ngừ",
    "canned tuna": "Cá ngừ đóng hộp",
    "cod": "Cá tuyết",
    "haddock": "Cá tuyết chấm đen",
    "halibut": "Cá bơn Halibut",
    "sea bass": "Cá chẽm",
    "trout": "Cá hồi chấm",
    "mackerel": "Cá thu",
    "sardines": "Cá mòi",
    "anchovy": "Cá cơm",
    "anchovies": "Cá cơm",
    "shrimp": "Tôm",
    "prawn": "Tôm sú",
    "prawns": "Tôm sú",
    "king prawns": "Tôm càng",
    "crab": "Cua",
    "crab meat": "Thịt cua",
    "lobster": "Tôm hùm",
    "squid": "Mực",
    "calamari": "Mực nang",
    "octopus": "Bạch tuộc",
    "clam": "Nghêu",
    "clams": "Nghêu",
    "mussel": "Vẹm",
    "mussels": "Vẹm",
    "oyster": "Hàu",
    "oysters": "Hàu",
    "scallop": "Sò điệp",
    "scallops": "Sò điệp",
    # Trứng, Sữa & Phô mai
    "egg": "Trứng gà",
    "eggs": "Trứng gà",
    "egg yolk": "Lòng đỏ trứng",
    "egg yolks": "Lòng đỏ trứng",
    "egg white": "Lòng trắng trứng",
    "egg whites": "Lòng trắng trứng",
    "milk": "Sữa tươi",
    "whole milk": "Sữa tươi nguyên kem",
    "skimmed milk": "Sữa tách béo",
    "buttermilk": "Sữa bơ (Buttermilk)",
    "condensed milk": "Sữa đặc",
    "evaporated milk": "Sữa bốc hơi",
    "heavy cream": "Kem béo Heavy Cream",
    "double cream": "kem đặc",
    "single cream": "kem sữa",
    "sour cream": "Kem chua",
    "whipping cream": "Kem tươi đánh bông",
    "creme fraiche": "Kem tươi Crème Fraîche",
    "cream cheese": "Phô mai kem",
    "butter": "Bơ",
    "unsalted butter": "Bơ lạt",
    "salted butter": "Bơ mặn",
    "ghee": "Bơ tinh chế Ghee",
    "cheese": "Phô mai",
    "cheddar cheese": "Phô mai Cheddar",
    "parmesan": "Phô mai Parmesan",
    "parmesan cheese": "Phô mai Parmesan",
    "mozzarella": "Phô mai Mozzarella",
    "feta": "Phô mai Feta",
    "feta cheese": "Phô mai Feta",
    "ricotta": "Phô mai Ricotta",
    "brie": "Phô mai Brie",
    "gouda": "Phô mai Gouda",
    "gruyere": "Phô mai Gruyère",
    "blue cheese": "Phô mai xanh",
    "goat cheese": "Phô mai dê",
    "mascarpone": "Phô mai Mascarpone",
    "yogurt": "Sữa chua",
    "greek yogurt": "Sữa chua Hy Lạp",
    # Rau củ quả
    "garlic": "Tỏi",
    "garlic cloves": "Tép tỏi",
    "garlic powder": "Bột tỏi",
    "onion": "Hành tây",
    "onions": "Hành tây",
    "red onion": "Hành tím tây",
    "red onions": "Hành tím tây",
    "shallot": "Hành tím",
    "shallots": "Hành tím",
    "challots": "Hành tím",
    "spring onion": "Hành lá",
    "spring onions": "Hành lá",
    "green onion": "Hành lá",
    "green onions": "Hành lá",
    "scallion": "Hành lá",
    "scallions": "Hành lá",
    "leek": "Tỏi tây (Ba-rô)",
    "leeks": "Tỏi tây (Ba-rô)",
    "chives": "Hẹ",
    "callaloo": "Rau callaloo",
    "ginger": "Gừng",
    "ginger root": "Củ gừng",
    "galangal": "Củ riềng",
    "turmeric": "Nghệ",
    "turmeric powder": "Bột nghệ",
    "potato": "Khoai tây",
    "potatoes": "Khoai tây",
    "sweet potato": "Khoai lang",
    "sweet potatoes": "Khoai lang",
    "yam": "Khoai mỡ",
    "carrot": "Cà rốt",
    "carrots": "Cà rốt",
    "tomato": "Cà chua",
    "tomatoes": "Cà chua",
    "cherry tomatoes": "Cà chua bi",
    "plum tomatoes": "Cà chua quả mận",
    "baby plum tomatoes": "Cà chua bi baby",
    "sun-dried tomatoes": "Cà chua sấy khô",
    "tomato puree": "Cà chua xay nhuyễn",
    "tomato paste": "Cà chua cô đặc",
    "canned tomatoes": "Cà chua đóng hộp",
    "chopped tomatoes": "Cà chua thái nhỏ",
    "cucumber": "Dưa leo",
    "cucumbers": "Dưa leo",
    "zucchini": "Bí ngòi xanh",
    "courgette": "Bí ngòi xanh",
    "courgettes": "Bí ngòi xanh",
    "aubergine": "Cà tím",
    "eggplant": "Cà tím",
    "cabbage": "Bắp cải",
    "red cabbage": "Bắp cải tím",
    "savoy cabbage": "Bắp cải Savoy",
    "chinese cabbage": "Cải thảo",
    "bok choy": "Cải thìa",
    "pak choi": "Cải thìa",
    "spinach": "Rau chân vịt (Cải bó xôi)",
    "baby spinach": "Cải bó xôi non",
    "lettuce": "Xà lách",
    "iceberg lettuce": "Xà lách búp",
    "romaine lettuce": "Xà lách Romaine",
    "arugula": "Rau Rocket (Arugula)",
    "rocket": "Rau Rocket",
    "kale": "Cải xoăn Kale",
    "watercress": "Xà lách xoong",
    "broccoli": "Bông cải xanh",
    "cauliflower": "Bông cải trắng",
    "asparagus": "Măng tây",
    "celery": "Cần tây",
    "celeriac": "Củ cần tây",
    "fennel": "Tiểu hồi hương (Thì là tây)",
    "artichoke": "A-ti-sô",
    "artichokes": "A-ti-sô",
    "bell pepper": "Ớt chuông",
    "red pepper": "Ớt chuông đỏ",
    "green pepper": "Ớt chuông xanh",
    "yellow pepper": "Ớt chuông vàng",
    "capsicum": "Ớt chuông",
    "chilli": "Ớt",
    "chili": "Ớt",
    "red chilli": "Ớt đỏ",
    "green chilli": "Ớt xanh",
    "red chili": "Ớt đỏ",
    "green chili": "Ớt xanh",
    "jalapeno": "Ớt Jalapeño",
    "habanero": "Ớt Habanero",
    "cayenne pepper": "Ớt bột Cayenne",
    "chilli flakes": "Ớt khô dạng vảy",
    "chilli powder": "Bột ớt",
    "mushroom": "Nấm",
    "mushrooms": "Nấm",
    "button mushrooms": "Nấm mỡ trắng",
    "cremini mushrooms": "Nấm mỡ nâu",
    "portobello mushrooms": "Nấm Portobello",
    "shiitake mushrooms": "Nấm đông cô",
    "oyster mushrooms": "Nấm bào ngư",
    "corn": "Ngô (Bắp)",
    "sweetcorn": "Bắp ngọt",
    "baby corn": "Bắp non",
    "pumpkin": "Bí đỏ",
    "butternut squash": "Bí đỏ hồ lô",
    "squash": "Bí đỏ",
    "avocado": "Bơ quả",
    "avocados": "Bơ quả",
    "beetroot": "Củ dền",
    "beets": "Củ dền",
    "radish": "Củ cải đỏ",
    "daikon": "Củ cải trắng",
    "turnip": "Củ cải tròn Turnip",
    "parsnip": "Củ cần củ cải trắng Parsnip",
    "bamboo shoots": "Măng tây trúc",
    "bean sprouts": "Giá đỗ",
    "okra": "Đậu bắp",
    "peas": "Đậu Hà Lan",
    "green peas": "Đậu Hà Lan xanh",
    "snap peas": "Đậu ngọt",
    "snow peas": "Đậu ván tuyết",
    "green beans": "Đậu que",
    "string beans": "Đậu cô ve",
    "french beans": "Đậu Pháp",
    # Đậu & Hạt khô
    "beans": "Các loại đậu",
    "black beans": "Đậu đen",
    "kidney beans": "Đậu đỏ Kidney",
    "red kidney beans": "Đậu đỏ Kidney",
    "white beans": "Đậu trắng",
    "cannellini beans": "Đậu trắng Cannellini",
    "haricot beans": "Đậu cúc Haricot",
    "borlotti beans": "Đậu rằn Borlotti",
    "pinto beans": "Đậu cúc Pinto",
    "butter beans": "Đậu ngự Lima",
    "fava beans": "Đậu tằm",
    "broad beans": "Đậu tằm",
    "chickpeas": "Đậu gà Chickpeas",
    "garbanzo beans": "Đậu gà",
    "lentils": "Đậu lăng",
    "red lentils": "Đậu lăng đỏ",
    "brown lentils": "Đậu lăng nâu",
    "green lentils": "Đậu lăng xanh",
    "edamame": "Đậu nành Nhật",
    "soybeans": "Đậu nành",
    "tofu": "Đậu hũ",
    "silken tofu": "Đậu hũ non",
    "firm tofu": "Đậu hũ miếng",
    "tempeh": "Đậu nành lên men Tempeh",
    "nuts": "Các loại hạt",
    "peanuts": "Đậu phộng (Lạc)",
    "peanut": "Đậu phộng",
    "peanut butter": "Bơ đậu phộng",
    "almonds": "Hạnh nhân",
    "almond": "Hạnh nhân",
    "flaked almonds": "Hạnh nhân lát",
    "cashews": "Hạt điều",
    "cashew nuts": "Hạt điều",
    "walnuts": "Hạt óc chó",
    "pecans": "Hạt hồ đào",
    "hazelnuts": "Hạt phỉ",
    "pistachios": "Hạt dẻ cười",
    "pine nuts": "Hạt thông",
    "macadamia": "Hạt mắc ca",
    "sesame": "Hạt mè (Vừng)",
    "sesame seeds": "Mè rang",
    "white sesame seeds": "Mè trắng",
    "black sesame seeds": "Mè đen",
    "tahini": "Sốt mè Tahini",
    "chia seeds": "Hạt chia",
    "flax seeds": "Hạt lanh",
    "pumpkin seeds": "Hạt bí ngô",
    "sunflower seeds": "Hạt hướng dương",
    # Ngũ cốc, Bột & Mì / Bánh
    "rice": "Gạo",
    "white rice": "Gạo trắng",
    "brown rice": "Gạo lứt",
    "basmati rice": "Gạo Basmati",
    "jasmine rice": "Gạo thơm Jasmine",
    "arborio rice": "Gạo Ý Arborio",
    "sushi rice": "Gạo nấu Sushi",
    "wild rice": "Gạo hoang",
    "pasta": "Mì Ý (Pasta)",
    "spaghetti": "Mì Spaghetti",
    "fettuccine": "Mì Fettuccine",
    "penne": "Nui ống Penne",
    "fusilli": "Nui xoắn Fusilli",
    "macaroni": "Nui Macaroni",
    "lasagne sheets": "Lá mì Lasagne",
    "lasagna": "Lá mì Lasagna",
    "tagliatelle": "Mì dẹt Tagliatelle",
    "bowtie pasta": "Nui hình nơ Bowtie",
    "farfalle": "Nui hình nơ Farfalle",
    "orzo": "Mì hạt gạo Orzo",
    "noodles": "Mì sợi",
    "egg noodles": "Mì trứng",
    "rice noodles": "Bánh phở / Bún gạo",
    "rice vermicelli": "Bún gạo sợi nhỏ",
    "vermicelli": "Miến / Bún khô",
    "glass noodles": "Miến dong",
    "soba noodles": "Mì kiều mạch Soba",
    "udon noodles": "Mì Udon",
    "ramen noodles": "Mì Ramen",
    "bread": "Bánh mì",
    "white bread": "Bánh mì trắng",
    "brown bread": "Bánh mì đen nâu",
    "wholemeal bread": "Bánh mì nguyên cám",
    "sourdough": "Bánh mì men chua Sourdough",
    "baguette": "Bánh mì Baguette",
    "pita": "Bánh mì Pita",
    "pita bread": "Bánh mì Pita",
    "naan": "Bánh mì Ấn Độ Naan",
    "tortilla": "Bánh bột ngô Tortilla",
    "tortillas": "Bánh Tortilla",
    "breadcrumbs": "Bột chiên xù",
    "panko": "Bột chiên xù Panko",
    "flour": "Bột mì",
    "plain flour": "Bột mì đa dụng",
    "all-purpose flour": "Bột mì đa dụng",
    "self-raising flour": "Bột mì tự nở",
    "bread flour": "Bột mì làm bánh mì",
    "cake flour": "Bột mì làm bánh bông lan",
    "cornflour": "Bột bắp (Tinh bột ngô)",
    "cornstarch": "Bột bắp",
    "corn starch": "Bột bắp",
    "potato starch": "Tinh bột khoai tây",
    "tapioca starch": "Bột năng",
    "rice flour": "Bột gạo",
    "glutinous rice flour": "Bột nếp",
    "semolina": "Bột mì Semolina",
    "polenta": "Bột ngô Polenta",
    "couscous": "Hạt Couscous",
    "quinoa": "Hạt diêm mạch Quinoa",
    "oats": "Yến mạch",
    "rolled oats": "Yến mạch cán dẹt",
    "baking powder": "Bột nở (Baking powder)",
    "baking soda": "Bột nở muối (Baking soda)",
    "bicarbonate of soda": "Bột muối nở Soda",
    "yeast": "Men nở",
    "dry yeast": "Men nở khô",
    "instant yeast": "Men nở tức thì",
    # Gia vị & Thảo mộc
    "salt": "Muối",
    "sea salt": "Muối biển",
    "kosher salt": "Muối Kosher",
    "black pepper": "Tiêu đen",
    "white pepper": "Tiêu trắng",
    "peppercorns": "Hạt tiêu đen",
    "sugar": "Đường",
    "granulated sugar": "Đường cát trắng",
    "white sugar": "Đường trắng",
    "brown sugar": "Đường nâu",
    "caster sugar": "Đường cát mịn",
    "icing sugar": "Đường bột",
    "powdered sugar": "Đường bột",
    "palm sugar": "Đường thốt nốt",
    "honey": "Mật ong",
    "maple syrup": "Siro cây phong",
    "molasses": "Mật mía",
    "black treacle": "Mật mía đen",
    "golden syrup": "Siro vàng Golden Syrup",
    "vinegar": "Giấm",
    "white vinegar": "Giấm trắng",
    "cider vinegar": "Giấm táo",
    "apple cider vinegar": "Giấm táo",
    "red wine vinegar": "Giấm rượu vang đỏ",
    "white wine vinegar": "Giấm rượu vang trắng",
    "balsamic vinegar": "Giấm Balsamic",
    "rice vinegar": "Giấm gạo",
    "malt vinegar": "Giấm mạch nha",
    "oil": "Dầu ăn",
    "vegetable oil": "Dầu thực vật",
    "sunflower oil": "Dầu hoa hướng dương",
    "canola oil": "Dầu hạt cải",
    "rapeseed oil": "Dầu hạt cải",
    "olive oil": "Dầu ô liu",
    "extra virgin olive oil": "Dầu ô liu nguyên chất",
    "sesame oil": "Dầu mè",
    "toasted sesame oil": "Dầu mè thơm",
    "coconut oil": "Dầu dừa",
    "peanut oil": "Dầu đậu phộng",
    "corn oil": "Dầu ngô",
    "chilli oil": "Dầu ớt",
    "mustard oil": "Dầu mù tạt",
    "soy sauce": "Nước tương (Xì dầu)",
    "dark soy sauce": "Hắc xì dầu",
    "light soy sauce": "Xì dầu thanh",
    "fish sauce": "Nước mắm",
    "oyster sauce": "Dầu hào",
    "worcestershire sauce": "Sốt Worcestershire",
    "hot sauce": "Sốt cay",
    "tabasco": "Sốt Tabasco",
    "sriracha": "Tương ớt Sriracha",
    "chilli sauce": "Tương ớt",
    "sweet chilli sauce": "Tương ớt ngọt",
    "tomato ketchup": "Tương cà Ketchup",
    "ketchup": "Tương cà",
    "mustard": "Mù tạt",
    "dijon mustard": "Mù tạt Dijon",
    "wholegrain mustard": "Mù tạt nguyên hạt",
    "english mustard": "Mù tạt Anh",
    "mayonnaise": "Sốt Mayonnaise",
    "pesto": "Sốt ngò tây Pesto",
    "barbecue sauce": "Sốt nướng BBQ",
    "bbq sauce": "Sốt BBQ",
    "teriyaki sauce": "Sốt Teriyaki",
    "hoisin sauce": "Sốt tương đen Hoisin",
    "miso": "Tương Miso",
    "miso paste": "Tương đậu nành Miso",
    "mirin": "Rượu nấu ăn Mirin",
    "sake": "Rượu Sake",
    "shaoxing wine": "Rượu Thiệu Hưng",
    "white wine": "Rượu vang trắng",
    "red wine": "Rượu vang đỏ",
    "dry white wine": "Rượu vang trắng khô",
    "brandy": "Rượu Brandy",
    "rum": "Rượu Rum",
    "cognac": "Rượu Cognac",
    "bourbon": "Rượu Bourbon",
    "sherry": "Rượu vang Sherry",
    "basil": "Húng quế tây",
    "basil leaves": "Lá húng quế",
    "thai basil": "Húng quế Thái",
    "bay leaf": "Lá nguyệt quế",
    "bay leaves": "Lá nguyệt quế",
    "cilantro": "Ngò rí (Rau mùi)",
    "coriander": "Ngò rí (Rau mùi)",
    "fresh coriander": "Ngò rí tươi",
    "coriander leaves": "Lá ngò rí",
    "coriander seeds": "Hạt ngò rí",
    "ground coriander": "Bột ngò rí",
    "parsley": "Ngò tây (Parsley)",
    "flat leaf parsley": "Ngò tây lá phẳng",
    "curly parsley": "Ngò tây lá xoăn",
    "mint": "Bạc hà (Húng lủi)",
    "fresh mint": "Lá bạc hà tươi",
    "mint leaves": "Lá bạc hà",
    "rosemary": "Hương thảo (Rosemary)",
    "fresh rosemary": "Hương thảo tươi",
    "thyme": "Xạ hương (Thyme)",
    "fresh thyme": "Xạ hương tươi",
    "oregano": "Kinh giới cay (Oregano)",
    "dried oregano": "Lá Oregano khô",
    "sage": "Xô thơm (Sage)",
    "tarragon": "Ngải giấm (Tarragon)",
    "dill": "Thì là (Dill)",
    "lemongrass": "Sả",
    "kaffir lime leaves": "Lá chanh Thái (Kaffir)",
    "lime leaves": "Lá chanh",
    "curry leaves": "Lá cà ri",
    "cumin": "Thì là Ai Cập (Cumin)",
    "cumin seeds": "Hạt thì là Cumin",
    "ground cumin": "Bột thì là Cumin",
    "paprika": "Bột ớt ngọt Paprika",
    "smoked paprika": "Bột ớt Paprika hun khói",
    "cinnamon": "Quế",
    "cinnamon stick": "Thanh quế",
    "ground cinnamon": "Bột quế",
    "nutmeg": "Nhục đậu khấu",
    "ground nutmeg": "Bột nhục đậu khấu",
    "cloves": "Đinh hương",
    "ground cloves": "Bột đinh hương",
    "cardamom": "Thảo quả / Bạch đậu khấu",
    "cardamom pods": "Quả bạch đậu khấu",
    "ground cardamom": "Bột bạch đậu khấu",
    "star anise": "Hoa hồi",
    "fennel seeds": "Hạt tiểu hồi",
    "fenugreek": "Cỏ ca ri Fenugreek",
    "allspice": "Hạt tiêu Jamaica (Allspice)",
    "saffron": "Nhụy hoa nghệ tây (Saffron)",
    "vanilla": "Vani",
    "vanilla extract": "Chiết xuất vani",
    "vanilla pod": "Quả vani",
    "curry powder": "Bột cà ri",
    "curry paste": "Sốt cà ri cô đặc",
    "red curry paste": "Sốt cà ri đỏ",
    "green curry paste": "Sốt cà ri xanh",
    "garam masala": "Bột gia vị Garam Masala",
    "five-spice powder": "Bột ngũ vị hương",
    "biryani masala": "Gia vị cơm Biryani",
    "cajun seasoning": "Gia vị Cajun",
    "cajun": "Gia vị Cajun",
    # Trái cây & Đồ ngọt
    "lemon": "Chanh vàng",
    "lemons": "Chanh vàng",
    "lemon juice": "Nước cốt chanh vàng",
    "lemon zest": "Vỏ chanh vàng bào",
    "lime": "Chanh xanh",
    "limes": "Chanh xanh",
    "lime juice": "Nước cốt chanh xanh",
    "lime zest": "Vỏ chanh xanh bào",
    "orange": "Cam",
    "oranges": "Cam",
    "orange juice": "Nước cam",
    "orange zest": "Vỏ cam bào",
    "apple": "Táo",
    "apples": "Táo",
    "bramley apples": "Táo chua Bramley",
    "green apple": "Táo xanh",
    "banana": "Chuối",
    "bananas": "Chuối",
    "strawberry": "Dâu tây",
    "strawberries": "Dâu tây",
    "blueberry": "Việt quất",
    "blueberries": "Việt quất",
    "raspberry": "Mâm xôi",
    "raspberries": "Mâm xôi",
    "blackberry": "Dâu tằm đen",
    "blackberries": "Dâu tằm đen",
    "cherry": "Anh đào (Cherry)",
    "cherries": "Quả cherry",
    "mango": "Xoài",
    "mangoes": "Xoài",
    "pineapple": "Dứa (Thơm)",
    "pineapples": "Dứa (Thơm)",
    "papaya": "Đu đủ",
    "coconut": "Dừa",
    "desiccated coconut": "Cơm dừa sấy khô",
    "coconut milk": "Nước cốt dừa",
    "coconut cream": "Kem dừa",
    "coconut water": "Nước dừa tươi",
    "shredded coconut": "Cơm dừa nạo sợi",
    "grapes": "Nho",
    "raisins": "Nho khô",
    "sultanas": "Nho khô vàng Sultana",
    "currants": "Nho khô Zante Currant",
    "dates": "Chà là",
    "figs": "Quả sung ngọt",
    "dried figs": "Sung sấy khô",
    "prunes": "Mận sấy khô",
    "peach": "Đào",
    "peaches": "Đào",
    "plum": "Mận",
    "plums": "Mận",
    "pear": "Lê",
    "pears": "Lê",
    "watermelon": "Dưa hấu",
    "melon": "Dưa lưới",
    "cantaloupe": "Dưa vàng Cantaloupe",
    "pomegranate": "Lựu",
    "pomegranate seeds": "Hạt lựu",
    "passion fruit": "Chanh dây",
    "kiwi": "Quả Kiwi",
    "chocolate": "Sô-cô-la",
    "dark chocolate": "Sô-cô-la đen",
    "milk chocolate": "Sô-cô-la sữa",
    "white chocolate": "Sô-cô-la trắng",
    "cocoa powder": "Bột cacao",
    "cacao": "Bột Cacao",
    "chocolate chips": "Hạt sô-cô-la chip",
    "gelatin": "Bột thạch Gelatin",
    "gelatine": "Bột thạch Gelatin",
}


def normalize_key(text: str | None) -> str:
    """Chuẩn hóa khóa tra cứu (chữ thường, bỏ dấu, gộp khoảng trắng)."""
    if not text:
        return ""
    text = text.strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class IngredientTranslator:
    """Công cụ dịch tên nguyên liệu ẩm thực Anh -> Việt có ghi nhớ từ điển."""

    def __init__(self, dict_path: Path | None = None) -> None:
        self.dict_path = dict_path or DEFAULT_DICT
        self.translations: dict[str, str] = {}
        self.load_dict()

    def load_dict(self) -> None:
        """Đọc file từ điển JSON nếu đã có."""
        if self.dict_path.exists():
            try:
                with self.dict_path.open("r", encoding="utf-8") as f:
                    self.translations = json.load(f)
            except Exception as e:
                print(f"[WARN] Không đọc được file từ điển {self.dict_path}: {e}")
                self.translations = {}

    def save_dict(self) -> None:
        """Ghi từ điển JSON ra đĩa (sắp xếp theo alphabet, định dạng đẹp)."""
        self.dict_path.parent.mkdir(parents=True, exist_ok=True)
        sorted_dict = dict(sorted(self.translations.items(), key=lambda x: x[0].lower()))
        with self.dict_path.open("w", encoding="utf-8") as f:
            json.dump(sorted_dict, f, ensure_ascii=False, indent=2)

    def translate(self, english_name: str, force: bool = False) -> tuple[str, bool]:
        """Dịch một tên nguyên liệu. Trả về (tên_tiếng_Việt, is_new)."""
        raw = english_name.strip()
        if not raw:
            return "", False

        key = normalize_key(raw)

        # 1. Tra từ điển đã lưu (nếu không force)
        if not force and key in self.translations:
            return self.translations[key], False

        # 2. Tra từ điển chuẩn ẩm thực BASE_LEXICON
        if key in BASE_LEXICON:
            vi = BASE_LEXICON[key]
            self.translations[key] = vi
            return vi, True

        # 3. Thử bỏ đuôi số nhiều đơn giản (s, es)
        if key.endswith("es") and key[:-2] in BASE_LEXICON:
            vi = BASE_LEXICON[key[:-2]]
            self.translations[key] = vi
            return vi, True
        if key.endswith("s") and key[:-1] in BASE_LEXICON:
            vi = BASE_LEXICON[key[:-1]]
            self.translations[key] = vi
            return vi, True

        # 4. Phân tích cụm từ ghép: [Modifier / Adjective] + [Base Noun] hoặc [Base] + [Suffix]
        vi_compound = self._decompose_and_translate(key, raw)
        if vi_compound:
            self.translations[key] = vi_compound
            return vi_compound, True

        # 5. Nếu chưa có quy tắc khớp, giữ tên gốc và viết hoa chữ cái đầu
        fallback = raw.strip()
        self.translations[key] = fallback
        return fallback, True

    def _decompose_and_translate(self, norm_key: str, raw_name: str) -> str | None:
        words = norm_key.split()
        if len(words) < 2:
            return None

        # Trường hợp 1: [Modifier] + [Base Ingredient]
        # ví dụ: "smoked salmon" -> "Cá hồi hun khói", "ground beef" -> "Thịt bò xay"
        first_word = words[0]
        rest_key = " ".join(words[1:])
        if first_word in MODIFIERS and rest_key in BASE_LEXICON:
            base_vi = BASE_LEXICON[rest_key]
            mod_vi = MODIFIERS[first_word]
            return f"{base_vi} {mod_vi}"

        # Trường hợp 2: [Base Ingredient] + [Suffix/Form]
        # ví dụ: "garlic powder" -> "Bột tỏi", "tomato sauce" -> "Sốt cà chua"
        last_word = words[-1]
        front_key = " ".join(words[:-1])
        if last_word in SUFFIXES and front_key in BASE_LEXICON:
            base_vi = BASE_LEXICON[front_key].lower()
            suf_vi = SUFFIXES[last_word].capitalize()
            # Quy tắc: "flour" chi -> "bột mì" neu co ban la wheat/plain/all-purpose/
            # self-raising/bread;
            # con lai -> "bột <nguyen lieu>" (vi du: almond flour -> "Bot hanh nhan").
            if last_word == "flour" and front_key not in {
                "wheat",
                "plain",
                "all purpose",
                "self raising",
                "bread",
            }:
                suf_vi = "Bột"
            return f"{suf_vi} {base_vi}"

        # Trường hợp 3: [2-word Modifier] + [Base]
        # ví dụ: "extra virgin olive oil" -> "Dầu ô liu nguyên chất"
        if len(words) >= 3:
            first_two = f"{words[0]} {words[1]}"
            rest_key = " ".join(words[2:])
            if first_two in MODIFIERS and rest_key in BASE_LEXICON:
                return f"{BASE_LEXICON[rest_key]} {MODIFIERS[first_two]}"

            # [Base] + [2-word suffix]
            front_key = " ".join(words[:-2])
            last_two = f"{words[-2]} {words[-1]}"
            if last_two in SUFFIXES and front_key in BASE_LEXICON:
                return f"{SUFFIXES[last_two].capitalize()} {BASE_LEXICON[front_key].lower()}"

        return None


def run_translation(
    input_file: Path,
    dict_file: Path,
    force: bool = False,
    apply_save: bool = True,
) -> dict[str, Any]:
    """Hàm chạy dịch hàng loạt cho file nguyên liệu JSONL."""
    translator = IngredientTranslator(dict_file)

    if not input_file.exists():
        raise FileNotFoundError(f"Không tìm thấy file nguyên liệu: {input_file}")

    total = 0
    translated_count = 0
    fallback_count = 0
    results: list[dict[str, str]] = []

    with input_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            name = item.get("name", "")
            vi, is_new = translator.translate(name, force=force)
            norm_key = normalize_key(name)
            total += 1

            # Kiểm tra xem co phai fallback (chua dich duoc sang tieng Viet)
            # Muc da co dau tieng Viet hoac co trong tu dien = "da tieng Viet";
            # chi bao "can dich" voi muc that sua con tieng Anh.
            has_vn_diacritics = any(c in VN_CHARS for c in name.lower())
            if vi.lower() == name.lower() and not has_vn_diacritics:
                fallback_count += 1
            else:
                translated_count += 1

            results.append({"english": name, "vietnamese": vi, "key": norm_key})

    if apply_save:
        translator.save_dict()

    return {
        "total": total,
        "translated": translated_count,
        "fallback": fallback_count,
        "dict_path": str(dict_file),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dịch tên nguyên liệu ẩm thực Anh -> Việt cho EasyMeals."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Đường dẫn file JSONL chứa nguyên liệu (mặc định: data/open/ingredients.jsonl)",
    )
    parser.add_argument(
        "--dict",
        type=Path,
        default=DEFAULT_DICT,
        help="Đường dẫn file từ điển JSON (mặc định: data/ingredient_translations.json)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Dịch lại toàn bộ và ghi đè từ điển hiện có.",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Chỉ in thống kê độ bao phủ bản dịch.",
    )
    args = parser.parse_args()

    print(f"-> Đang xử lý file: {args.input}")
    res = run_translation(args.input, args.dict, force=args.force)

    print("\n== KẾT QUẢ DỊCH NGUYÊN LIỆU ==")
    print(f"  Tổng số nguyên liệu : {res['total']}")
    ratio = res["translated"] / max(1, res["total"])
    print(f"  Đã dịch sang tiếng Việt: {res['translated']} ({ratio:.1%})")
    print(f"  Chưa dịch (giữ tên gốc): {res['fallback']}")
    print(f"  File từ điển lưu tại: {res['dict_path']}")

    if res["fallback"] > 0 and args.stats:
        print("\nDanh sách một số mục giữ tên gốc:")
        for item in [r for r in res["results"] if r["english"].lower() == r["vietnamese"].lower()][
            :30
        ]:
            print(f"  - {item['english']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
