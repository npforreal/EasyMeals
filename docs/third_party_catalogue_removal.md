# Ghi chú về việc loại bỏ nguồn dữ liệu TheMealDB

Dự án EasyMeals đã loại bỏ hoàn toàn toàn bộ dữ liệu, mã nguồn và mọi tham chiếu liên quan đến TheMealDB (TheMealDB.com) ra khỏi kho lưu trữ và ứng dụng.

## Lý do quyết định

1. **Điều khoản cấp phép không phù hợp cho phân phối ứng dụng**:
   - Khoá API thử nghiệm miễn phí chỉ dành riêng cho mục đích phát triển cục bộ và học tập.
   - Điều khoản chính thức của dịch vụ quy định rõ: *"You cannot publish apps to an appstore unless you are a paid subscriber"*.
2. **Quyền sở hữu và phân phối lại dữ liệu trong dự án mã nguồn mở**:
   - Dịch vụ yêu cầu giữ thông báo bản quyền và ghi nguồn chặt chẽ, đồng thời nội dung từ bên thứ ba cần sự cho phép bằng văn bản của chủ sở hữu gốc.
   - Đưa một bản sao cơ sở dữ liệu của bên thứ ba vào một kho lưu trữ mã nguồn mở công khai (public repository) cấu thành hành vi tái phân phối mà dự án không có sự uỷ quyền rõ ràng.
3. **Chất lượng và tính thực tế của ẩm thực Việt Nam**:
   - EasyMeals định vị là ứng dụng sổ tay bếp thông minh với trọng tâm là các món ăn gia đình Việt Nam và một số món quốc tế quen thuộc. Dữ liệu TheMealDB chủ yếu là các món phương Tây với định lượng ước lượng (tbsp, cup, to taste...) không tương thích với mô hình quản lý kho chính xác theo đơn vị hệ mét (g, kg, ml, piece).

## Hướng giải quyết

- Toàn bộ danh mục công thức hiện tại của EasyMeals được tự biên soạn độc lập bởi đội ngũ dự án (~133 món ăn: 107 món gia đình Việt, 24 món quốc tế quen thuộc đã được Việt hoá, và bộ chuẩn nội bộ) với 147 nguyên liệu nhất quán về đơn vị.
- Dữ liệu công thức được phân phối theo giấy phép mở **CC BY-SA 4.0**.
