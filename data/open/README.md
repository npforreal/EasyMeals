# data/open

Danh mục nguyên liệu và công thức nấu ăn thuần Việt và quốc tế chuẩn hoá của EasyMeals.

- `ingredients_vi.jsonl`: Danh mục 147 nguyên liệu chuẩn hoá tiếng Việt, phân loại rõ ràng và đầy đủ bí danh (aliases).
- `vietnamese_recipes.jsonl`: 105 món ăn gia đình Việt Nam kinh điển (mặn, rau, canh) với định lượng thực tế theo khẩu phần 4 người.
- `international_recipes_vi.jsonl`: 25 món ăn quốc tế phổ biến đã được Việt hoá nguyên liệu và hướng dẫn.

Giấy phép dữ liệu: **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**.
Xem thêm [docs/third_party_catalogue_removal.md](../../docs/third_party_catalogue_removal.md) về lý do loại bỏ hoàn toàn các nguồn dữ liệu bên thứ ba không rõ ràng về bản quyền.

## Metadata công thức

- `storage_rules.json`: quy tắc mẹo bảo quản theo nhóm món (canh / món có đạm động vật / món khác + quy tắc chung), mỗi quy tắc dẫn nguồn. Nguồn hiện dùng: FDA "Safe Food Handling" (phạm vi công cộng), diễn giải tiếng Việt, đổi °F sang °C. Chưa có số ngày bảo quản cụ thể vì chưa truy cập được nguồn FSIS/FoodKeeper; không suy diễn thêm.
- `recipe_metadata.jsonl` (tuỳ chọn, chưa tồn tại): thời gian chuẩn bị/nấu và độ khó đã được người duyệt xác nhận, tạo bằng `python scripts/estimate_recipe_times.py apply --csv ...` từ `data/review/recipe_time_draft.csv`. Giá trị trong CSV nháp chỉ là ước lượng, không được đưa vào catalogue khi chưa có người duyệt và ngày xác minh.
