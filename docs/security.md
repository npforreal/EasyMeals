# EasyMeals — Hướng dẫn và Kiến trúc Bảo mật (Security Guide)

Tài liệu này mô tả mô hình bảo mật, thiết kế phòng chống tấn công và các bước cấu hình quan trọng cho kiến trúc mới của EasyMeals: **Dữ liệu cá nhân cục bộ trên máy người dùng, Backend không trạng thái và Database danh mục công khai chỉ đọc**.

---

## 1. Mô hình Đe dọa & Kiến trúc Bảo vệ (Threat Model)

| Lỗ hổng tiềm ẩn | Biện pháp ngăn chặn & Thiết kế bảo vệ | Mã phát hiện đã vá |
|---|---|---|
| **Lộ dữ liệu cá nhân trên Server / DB** | **Thiết kế mặc định an toàn (Zero Server-side Storage)**: Server và Supabase không lưu bất kỳ thông tin nào về người dùng, tài khoản, tủ thực phẩm hay thực đơn. Mọi dữ liệu cá nhân chỉ lưu trong IndexedDB trên thiết bị. | **Kiến trúc mới** |
| **Bỏ qua RLS qua Service Key** | Runtime máy chủ **từ chối chạy nếu phát hiện `SUPABASE_SERVICE_ROLE_KEY` trong môi trường**. Truy vấn Supabase từ server chỉ sử dụng `SUPABASE_ANON_KEY` với quyền chỉ đọc. Khoá service key chỉ dùng cục bộ cho script seed. | **S1, Quy tắc cứng** |
| **Lộ tài liệu API công khai** | Tự động tắt Swagger (`/docs`), ReDoc (`/redoc`) và `/openapi.json` khi chạy ở môi trường production (`VERCEL_ENV`, `VERCEL`, hoặc `APP_ENV != 'development'`). | **S2** |
| **Lộ thông tin nội bộ qua `/health`** | Endpoint `/health` trả về trạng thái tối thiểu (`{"status": "ok"}`), không để lộ chi tiết cấu hình hệ thống hay biến môi trường. | **S3** |
| **Clickjacking & XSS** | Thiết lập Security Headers nghiêm ngặt: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Content-Security-Policy` chặn script inline (`script-src 'self'`). Mọi dữ liệu động đều escape bằng `textContent`. | **S4, S8** |
| **Lạm dụng tính toán DoS qua Planner API** | Giới hạn kỳ lập thực đơn tối đa 31 ngày, giới hạn payload $\le 256$ KB, giới hạn số lot trong tủ $\le 500$. Trả về HTTP `422` hoặc `413` nếu vượt ngưỡng. | **S5, S7** |
| **Tệp JSON độc hại khi Nhập dữ liệu (Malicious Import)** | Kiểm tra schema nghiêm ngặt: validate cấu trúc, kiểu dữ liệu, enum, giới hạn độ dài chuỗi, giới hạn kích thước file ($\le 10$ MB), giới hạn số bản ghi. Không tin cậy dữ liệu nhập vào DOM. | **Mới (Client-side)** |
| **Trừ kho trùng lặp (Double Deduction / Race Condition)** | Client thực hiện thao tác đánh dấu "Đã ăn" và "Hoàn tác" bên trong một IndexedDB Transaction nguyên tử (`readwrite`), kiểm tra trạng thái `eaten_at` ngay trong transaction để chống xung đột giữa 2 tab hoặc bấm đúp. | **Mới (IndexedDB)** |
| **Cạn kiệt lưu trữ / Mất dữ liệu trình duyệt** | Tự động gọi `navigator.storage.persist()`. Cung cấp chức năng Xuất/Nhập JSON và hiển thị cảnh báo nhắc nhở người dùng sao lưu định kỳ trên trang Cài đặt. | **Mới (Storage)** |
| **Lộ dữ liệu qua thông báo nhắc việc (F2)** | Nhắc việc chỉ tạo cục bộ trên máy, nội dung lấy từ dữ liệu trên máy; không gửi nội dung lên máy chủ hay dịch vụ push. Quyền chỉ xin khi người dùng bật; tắt là huỷ toàn bộ lịch. Nội dung ngắn (tên lô/bữa) có thể hiện trên màn hình khoá — đây là đánh đổi đã biết, người dùng tự chọn bật. Receiver Android `exported="false"`. Không thêm `INTERNET`. | **F2, Vòng 13** |

---

## 2. Loại Bỏ Xác Thực & Quản Lý Phiên (No Auth Architecture)

Trong kiến trúc mới:
- **Không có tài khoản người dùng, không có đăng nhập / đăng ký.**
- Loại bỏ hoàn toàn Supabase Auth, JWT validation, cookie phiên đăng nhập (`sb-access-token`, `sb-refresh-token`), CSRF double-submit tokens, và header `X-User-Id`.
- Mọi người dùng đều sử dụng chung một catalog danh mục công khai (đọc qua backend FastAPI anon key).
- WebView trên Android và iOS (Capacitor) hoạt động với origin cục bộ và kết nối đến API backend qua CORS tối thiểu (chỉ cho phép các phương thức cần thiết, không credentials).

---

### 2.1 Quyền và Thông báo trên Ứng dụng Di động (F2 — Vòng 13)

| Nền tảng | Quyền khai báo | Khi nào xin | Dùng để làm gì |
|---|---|---|---|
| Android | `android.permission.VIBRATE` | Không cần xin (normal permission) | Rung khi hiển thị thông báo |
| Android | `android.permission.POST_NOTIFICATIONS` | **Chỉ khi** người dùng bật công tắc "Nhắc việc" trong Cài đặt (Android 13+) | Hiển thị thông báo nhắc hạn dùng/bữa ăn |
| Android | ~~`android.permission.INTERNET`~~ | **Bị cấm tuyệt đối** — test `tests/test_hardening_l.py` chặn nếu xuất hiện | — |
| iOS | Quyền thông báo hệ thống (`UNUserNotificationCenter`) | **Chỉ khi** người dùng bật công tắc "Nhắc việc" | Thông báo cục bộ |

Nguyên tắc:
- Từ chối quyền → công tắc tự trả về tắt, ứng dụng vẫn dùng bình thường, có hướng dẫn mở Cài đặt hệ thống.
- Tắt nhắc việc → huỷ toàn bộ thông báo đã lên lịch (Android `AlarmManager.cancel`, iOS `removeAllPendingNotificationRequests`).
- Không có push server, không có token thiết bị, không có SDK bên thứ ba.
- Android dùng `setAndAllowWhileIdle` (không exact-alarm) nên **không** cần `SCHEDULE_EXACT_ALARM`/`USE_EXACT_ALARM`; thông báo có thể trễ vài phút.
- Receiver nhắc việc là `android:exported="false"`: ứng dụng khác không thể kích hoạt.
- Web không gửi thông báo nền; Cài đặt Web chỉ ghi chú khác biệt, không xin quyền.

---

## 3. Các bước Quản trị viên cần thực hiện

### A. Cấu hình Supabase Dashboard
1. **Tạo Project Supabase mới**:
   - Chạy migration duy nhất `001_catalogue_baseline.sql` trong SQL Editor hoặc CLI.
   - Bật RLS cho tất cả 4 bảng: `ingredients`, `ingredient_aliases`, `recipes`, `recipe_ingredients`.
   - Chỉ cấp quyền `SELECT` cho role `anon` (và `authenticated`).
   - Huỷ bỏ (`REVOKE`) toàn bộ quyền `INSERT, UPDATE, DELETE` của role `anon` và `authenticated`.
2. **Nạp dữ liệu Danh mục ban đầu**:
   - Chạy script nạp danh mục `scripts/seed_catalogue.py` từ máy cục bộ của bạn với tham số `--apply`. `SUPABASE_URL` có thể nằm trong `.env`, nhưng **`SUPABASE_SERVICE_ROLE_KEY` chỉ được truyền qua biến môi trường của dòng lệnh trong phiên chạy đó** (ví dụ `SUPABASE_SERVICE_ROLE_KEY=... python scripts/seed_catalogue.py --apply`), **không lưu vào `.env`** (khớp `docs/deploy.md`). Agent/CI không bao giờ cần và không được đọc `.env`; kiểm tra cấu hình bằng `python scripts/check_supabase_config.py --offline`.
   - Không bao giờ đưa khoá `service_role` lên Vercel.

### B. Cấu hình Vercel Dashboard
1. **Biến Môi trường Runtime**:
   - Vào **Settings** > **Environment Variables**.
   - Thiết lập:
     - `SUPABASE_URL`: URL của Supabase project mới.
     - `SUPABASE_ANON_KEY`: Anon / public API key của Supabase project mới.
     - `APP_ENV`: `production` (mặc định nếu không đặt thì app vẫn coi là production khi chạy trên Vercel).
   - **TUYỆT ĐỐI KHÔNG** cấu hình `SUPABASE_SERVICE_ROLE_KEY` hoặc `SUPABASE_JWT_SECRET`.
2. **Bật Vercel Firewall / WAF Rate Limiting**:
   - Vào **Security** > **Firewall** > **Custom Rules** (hoặc Rate Limiting):
     - **Quy tắc 1 (Planner Computational API)**:
       - Đường dẫn: `/api/planner/*`
       - Ngưỡng giới hạn: tối đa **30 requests / phút** theo IP.
       - Hành động: Rate Limit (trả về 429).
     - **Quy tắc 2 (Catalogue & Static API)**:
       - Đường dẫn: `/api/*`
       - Ngưỡng giới hạn: tối đa **120 requests / phút** theo IP.
       - Hành động: Rate Limit.

---

## 4. Chạy Kiểm tra Bảo mật Tự động

Chạy toàn bộ kiểm tra bảo mật (Unit test Python, API limits, Security Headers, JS Storage test, Playwright e2e):

```bash
bash scripts/check.sh
```

Quét lỗ hổng phụ thuộc:
```bash
# Quét thư viện Python
python -m pip_audit

# Quét thư viện Mobile/NPM
npm audit
```
