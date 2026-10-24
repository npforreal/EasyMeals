# Hướng dẫn đóng góp cho EasyMeals (Contributing Guide)

Cảm ơn bạn đã quan tâm đóng góp cho EasyMeals! EasyMeals là một dự án mã nguồn mở hướng tới việc lập thực đơn và quản lý nguyên liệu bếp gia đình thông minh, tôn trọng tối đa quyền riêng tư của người dùng (Zero Server-side Personal Data).

---

## 1. Nguyên tắc cốt lõi (Core Principles)

- **Quyền riêng tư tuyệt đối (Privacy First)**: Không bao giờ lưu trữ dữ liệu cá nhân của người dùng (tủ lạnh, thực đơn, nhật ký ăn uống) lên máy chủ. Tất cả dữ liệu cá nhân phải nằm tại thiết bị người dùng (IndexedDB / SQLite nội bộ).
- **Offline 100%**: Ứng dụng hoạt động trọn vẹn không cần kết nối mạng. Danh mục món ăn và nguyên liệu được đóng gói sẵn.
- **Số học chính xác**: Toàn bộ tính toán định lượng phải sử dụng kiểu số học chính xác (`Decimal` trong Python/JS/Swift, `BigDecimal` trong Kotlin). Không dùng `float` / `double` cho số lượng nguyên liệu.
- **Kiểm thử bắt buộc**: Mọi thay đổi logic đều cần có bài kiểm thử tương ứng. Lệnh `bash scripts/check.sh` phải luôn báo xanh.

---

## 2. Quy trình đóng góp (Contribution Workflow)

1. **Fork repository** và tạo nhánh mới từ `main`:
   ```bash
   git checkout -b feature/ten-tinh-nang
   ```
2. **Cài đặt môi trường phát triển cục bộ**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   npm install
   ```
3. **Chạy kiểm thử trước khi commit**:
   ```bash
   bash scripts/check.sh
   ```
4. **Tạo Pull Request**:
   - Viết mô tả rõ ràng về thay đổi và lý do thực hiện.
   - Đảm bảo toàn bộ kiểm thử tự động đều vượt qua.

---

## 3. Báo lỗi và đề xuất tính năng (Issues)

- Nếu bạn phát hiện lỗi, hãy tạo một Issue bằng mẫu **Bug report**.
- Nếu bạn có ý tưởng tính năng mới, hãy tạo một Issue bằng mẫu **Feature request**.
- Đối với các phát hiện về lỗ hổng bảo mật, xin vui lòng xem hướng dẫn tại [SECURITY.md](SECURITY.md) (báo cáo riêng tư, không công khai).

---

## International Contributors (English Summary)

EasyMeals welcomes contributions from everyone worldwide!
- **Code License**: Apache License 2.0.
- **Data License**: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0).
- Please ensure that:
  1. No personal user data is ever sent to or stored on backend servers.
  2. All calculations use precise decimals (no float/double rounding errors).
  3. All tests pass cleanly (`bash scripts/check.sh`).
  4. Follow the code of conduct outlined in [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
