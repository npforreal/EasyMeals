# Chính sách bảo mật (Security Policy)

Dự án EasyMeals coi trọng sự an toàn và tính riêng tư của người dùng lên hàng đầu.

---

## 1. Phiên bản được hỗ trợ (Supported Versions)

Chúng tôi chỉ phát hành các bản vá bảo mật cho phiên bản mới nhất đang hoạt động trên nhánh `main`:

| Phiên bản | Được hỗ trợ |
|---|---|
| main (phiên bản mới nhất) | :white_check_mark: |
| < 2.0.0 | :x: |

---

## 2. Báo cáo lỗ hổng bảo mật (Reporting a Vulnerability)

> [!IMPORTANT]
> **Tuyệt đối không tạo Issue công khai trên GitHub để báo cáo lỗ hổng bảo mật.**

Nếu bạn phát hiện một vấn đề hoặc lỗ hổng bảo mật tiềm ẩn trong EasyMeals:

1. **Phương thức báo cáo**:
   - Vui lòng sử dụng tính năng **Private Vulnerability Reporting** trực tiếp trên trang bảo mật của repository GitHub (mục *Security* -> *Advisories* -> *Report a vulnerability*).
   - Hoặc gửi email trực tiếp tới quản trị viên dự án: `security@easymeals.local` (hoặc liên hệ qua kênh bảo mật nội bộ được chỉ định).

2. **Nội dung báo cáo**:
   - Mô tả ngắn gọn về loại lỗ hổng (ví dụ: XSS, bypass validation, privilege escalation, injection...).
   - Các bước cụ thể để tái hiện (reproduction steps) hoặc Proof of Concept (PoC).
   - Đánh giá mức độ ảnh hưởng tiềm tàng tới người dùng.

3. **Thời gian phản hồi**:
   - Đội ngũ dự án sẽ xác nhận đã nhận được báo cáo trong vòng **48 giờ**.
   - Chúng tôi sẽ phối hợp với bạn để kiểm chứng và chuẩn bị bản vá bảo mật trước khi công bố ra công chúng.
