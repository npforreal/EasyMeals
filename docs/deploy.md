# Hướng Dẫn Triển Khai EasyMeals (Deployment Guide)

Tài liệu này hướng dẫn chi tiết quy trình triển khai EasyMeals theo kiến trúc mới: **Zero Server-side Personal Data** (Không lưu dữ liệu cá nhân trên server), **Client-stored Data** (Lưu trữ toàn bộ tại IndexedDB trên trình duyệt/thiết bị di động), và **Stateless Backend** (FastAPI tính toán không trạng thái kết hợp Supabase danh mục chỉ đọc).

---

## 1. Kiến Trúc Triển Khai

```
+--------------------------------------------------------------------+
|                         CLIENT (Thiết bị)                          |
|  - Trình duyệt Web / PWA / App native (Android & iOS)              |
|  - IndexedDB: pantry, plans, movements, settings, catalogue cache   |
|  - Tính năng offline, sao lưu & phục hồi JSON                      |
+-------------------+------------------------------------------------+
                    |
                    | (HTTPS - API Calls)
                    v
+--------------------------------------------------------------------+
|                      BACKEND WEB (Vercel)                          |
|  - FastAPI (Python 3.12+) hoàn toàn không trạng thái (stateless)   |
|  - Không database người dùng, không session, không cookies auth   |
|  - Giới hạn payload 256KB, khoá /docs ở production, CSP nghiêm ngặt|
|  - Tính toán: Tạo thực đơn (generate), Trừ kho FIFO (eat/undo)     |
+-------------------+------------------------------------------------+
                    |
                    | (SELECT qua anon key công khai)
                    v
+--------------------------------------------------------------------+
|                 SHARED DATABASE (Supabase)                         |
|  - CHỈ chứa 6 bảng danh mục: ingredient_categories, ingredients,   |
|    ingredient_aliases, recipes, recipe_ingredients,                |
|    ingredient_conversions                                          |
|  - Row Level Security (RLS) bật 100%: chỉ cho phép SELECT           |
|  - Bị thu hồi toàn bộ quyền INSERT / UPDATE / DELETE cho mọi role  |
+--------------------------------------------------------------------+
```

---

## 2. Khởi Tạo Cơ Sở Dữ Liệu Supabase Mới

### Bước 2.1: Tạo Project Supabase
1. Đăng nhập [Supabase Dashboard](https://supabase.com).
2. Tạo một Project mới (chọn Region gần người dùng, ví dụ: `Singapore - ap-southeast-1`).
3. Lưu lại các thông tin:
   - **Project URL**: dạng `https://[project-id].supabase.co`
   - **Anon / Publishable Key**: trong mục *Settings* -> *API* (trên Supabase Dashboard có thể dán nhãn là `anon` `public` hoặc `Publishable key`, bắt đầu bằng `eyJ...` hoặc `sb_publishable_...`).
   - **Service Role Key**: dùng duy nhất một lần offline khi nạp dữ liệu danh mục ban đầu (bắt đầu bằng `eyJ...` hoặc `sb_secret_...`).

### Bước 2.2: Chạy Migration Baseline & Cập Nhật Schema
Mở mục **SQL Editor** trong Supabase Dashboard:
1. Nếu là dự án mới: dán toàn bộ nội dung tệp [supabase/full_schema.sql](supabase/full_schema.sql) và nhấn **Run**.
2. Nếu là dự án đã có baseline: chạy tiếp migration [supabase/migrations/202610250001_categories_conversions.sql](supabase/migrations/202610250001_categories_conversions.sql).

Migration này sẽ:
- Thiết lập schema 6 bảng danh mục chuẩn: `ingredient_categories`, `ingredients`, `ingredient_aliases`, `recipes`, `recipe_ingredients`, `ingredient_conversions`.
- Thêm cột `default_unit` và ràng buộc `category` hợp lệ cho bảng `ingredients`.
- Kích hoạt RLS (Row Level Security) trên toàn bộ 6 bảng.
- Tạo policy `Allow public read-only access for anon and authenticated` (chỉ SELECT).
- Thu hồi tường minh quyền `INSERT, UPDATE, DELETE, TRUNCATE` đối với role `anon`, `authenticated` và `public`.

### Bước 2.3: Nạp Dữ Liệu Danh Mục (Reset & Upload Catalogue)
Để nạp hoặc làm mới hoàn toàn danh mục chuẩn lên Supabase, chủ dự án tự chạy các lệnh sau từ máy cục bộ bằng khoá `service_role` của mình (chú ý: không chạy tự động trong CI hay do agent tự ý chạy lên Supabase thật):

```bash
# 1. Tuỳ chọn: Xoá sạch dữ liệu danh mục cũ (yêu cầu --confirm)
SUPABASE_URL="https://[project-id].supabase.co" \
SUPABASE_SERVICE_ROLE_KEY="[your-service-role-key]" \
python scripts/reset_supabase.py --confirm

# 2. Nạp toàn bộ danh mục mới từ data/catalogue.json (bao gồm categories và conversions)
SUPABASE_URL="https://[project-id].supabase.co" \
SUPABASE_SERVICE_ROLE_KEY="[your-service-role-key]" \
python scripts/upload_catalogue_to_supabase.py --apply
```

> [!CAUTION] **QUY TẮC BẢO MẬT BẮT BUỘC**
> `SUPABASE_SERVICE_ROLE_KEY` chỉ được truyền qua biến môi trường dòng lệnh trong phiên chạy script seed của chủ dự án. **Tuyệt đối không lưu khoá này vào file `.env` hoặc đưa lên Vercel.** Backend FastAPI sẽ từ chối khởi động và báo lỗi ngay lập tức nếu phát hiện biến `SUPABASE_SERVICE_ROLE_KEY` trong môi trường runtime.

> **Cập nhật nhanh khi phát hành bản mới:** dùng `bash scripts/update_supabase.sh` (dry-run mặc định), `--migrations` để liệt kê SQL cần chạy, `--apply` để nạp danh mục (script hỏi `service_role` key ở dạng ẩn, không lưu, rồi tự kiểm chứng RLS bằng anon key). Chỉ chủ dự án chạy script này.

### Bước 2.4: Kiểm Chứng RLS Thực Tế Trên Supabase
Sau khi chạy migration và nạp seed, kiểm tra trực tiếp chính sách RLS bằng script `scripts/verify_rls.py` (chạy thủ công, chỉ dùng anon key):

```bash
SUPABASE_URL="https://[project-id].supabase.co" \
SUPABASE_ANON_KEY="[your-anon-key]" \
python scripts/verify_rls.py
```

Script sẽ xác minh:
1. `SELECT` trên cả 6 bảng danh mục thành công.
2. `INSERT`, `UPDATE`, `DELETE` bằng anon key bị từ chối 100% bởi RLS.
3. Từ chối thực thi nếu phát hiện `SUPABASE_SERVICE_ROLE_KEY` trong môi trường.

*(Ghi chú: Nếu môi trường phát triển chưa có kết nối Supabase production thật, script được kiểm thử cục bộ tự động qua bộ mock test `tests/test_verify_rls.py`).*

---


## 3. Triển Khai Backend Lên Vercel

### Bước 3.1: Kết Nối Repository
1. Đăng nhập [Vercel Dashboard](https://vercel.com).
2. Chọn **Add New Project** và liên kết với kho lưu trữ GitHub của EasyMeals.
3. Framework Preset: chọn **Other** (FastAPI tự động nhận diện qua `vercel.json` và `app/main.py`).

### Bước 3.2: Cấu Hình Biến Môi Trường (Environment Variables)
Cấu hình 3 biến duy nhất tại mục *Settings* -> *Environment Variables* của project trên Vercel:

| Tên Biến | Giá Trị Ví Dụ | Mục Đích |
|---|---|---|
| `SUPABASE_URL` | `https://xyz.supabase.co` | Endpoint Supabase danh mục |
| `SUPABASE_ANON_KEY` | `eyJhbGciOi...` hoặc `sb_publishable_...` | Anon / Publishable key (chỉ đọc, hệ thống hỗ trợ cả alias `SUPABASE_PUBLISHABLE_KEY`) |
| `APP_ENV` | `production` | Bật chế độ bảo vệ production |

> [!IMPORTANT]
> Tuyệt đối **KHÔNG** thêm `SUPABASE_SERVICE_ROLE_KEY`, `SESSION_SECRET`, `JWT_SECRET`, hay bất kỳ khoá bí mật nào lên Vercel.

### Bước 3.3: Tự Động Khoá & Bảo Vệ Production
Khi `APP_ENV=production` được thiết lập trên Vercel:
- Tài liệu API `/docs`, `/redoc`, `/openapi.json` tự động bị vô hiệu hoá (trả về 404).
- Bộ lọc middleware tự động từ chối các request body lớn hơn 256KB (chống DoS / cạn kiệt bộ nhớ).
- Content Security Policy (CSP) chặn mọi inline script độc hại.

### Bước 3.4: Cấu Hình Giới Hạn Tần Suất (WAF / Rate Limiting)
Trên Vercel Dashboard (mục *Security* -> *Attack Challenge Mode* hoặc *Firewall*):
- Thiết lập Rate Limiting: tối đa 60 requests/phút cho các route `/api/planner/*` theo địa chỉ IP để chống lạm dụng CPU tính toán.

### Bước 3.5: Cơ Chế Cache `/api/catalogue` & Quy Trình Cập Nhật Danh Mục
1. **Cơ chế ETag băm nội dung**:
   - Header `ETag` của `/api/catalogue` được tính bằng hàm băm SHA-256 (16 ký tự đầu) trên toàn bộ JSON dữ liệu danh mục (`CATALOGUE_VERSION` + danh sách nguyên liệu, bí danh, công thức đã sắp xếp).
   - Khi client gửi header `If-None-Match: <etag>`, nếu dữ liệu trên server không đổi, server trả về ngay lập tức `304 Not Modified` (0 bytes payload), giúp tối ưu băng thông và tốc độ tải.
   - Cache-Control header: `public, max-age=3600, stale-while-revalidate=86400`.
2. **Quy trình cập nhật danh mục**:
   - Khi có thay đổi công thức hoặc bổ sung nguyên liệu mới, chạy lại script seed:
     ```bash
     SUPABASE_URL="..." SUPABASE_SERVICE_ROLE_KEY="..." python scripts/seed_catalogue.py --apply
     ```
   - ETag của bundle tự động thay đổi ngay lập tức theo nội dung mới mà không cần can thiệp thủ công.
   - Ở lần truy cập tiếp theo, trình duyệt/client phát hiện ETag mới, tải bundle 200 OK và cập nhật vào store `catalogue` trong IndexedDB mà không đụng chạm đến dữ liệu cá nhân của người dùng.


---

## 4. Đóng Gói Ứng Dụng Di Động Offline (Native)

Ứng dụng di động là native (Android Kotlin/Compose, iOS SwiftUI) với thiết kế **100% offline**:
- **Không gọi Supabase, không cần backend**: lập thực đơn và trừ kho FIFO chạy trên thiết bị bằng engine native (số học Decimal chính xác); Android không có quyền Internet.
- **Danh mục đóng gói sẵn**: `catalogue.json` được sao từ `data/catalogue.json` vào gói ứng dụng bằng `python scripts/sync_mobile_assets.py` (không tự sửa tay các bản sao này).

```bash
python scripts/export_catalogue.py
python scripts/sync_mobile_assets.py
cd mobile/android && ./gradlew assembleDebug      # APK debug
cd ../ios && xcodegen generate                    # sinh EasyMeals.xcodeproj rồi build bằng Xcode
```

Quy trình đóng gói và phát hành đầy đủ: [`docs/release.md`](release.md). Hướng dẫn thiết bị: [`mobile/README.md`](../mobile/README.md).

## 5. Quy Trình Vận Hành & Khắc Phục Sự Cố

### Kiểm Tra Sức Khoẻ (Health Check)
Endpoint công khai không cần khoá để giám sát uptime:
```bash
curl -i https://[your-app-domain].vercel.app/health
# Trả về: {"status": "ok", "app": "EasyMeals", "mode": "stateless"}
```

### Quản Lý Dữ Liệu Của Người Dùng
- **Sao lưu**: Người dùng mở mục **Dữ liệu** (`/settings`), bấm nút **Xuất file sao lưu (JSON)** để tải file về máy.
- **Phục hồi**: Chọn tệp JSON sao lưu tại trang `/settings`, chọn chế độ **Hợp nhất** (Merge) hoặc **Ghi đè** (Replace).
- **Xoá sạch dữ liệu**: Nhấn **Xoá toàn bộ dữ liệu trên máy này** và xác nhận tại hộp thoại 2 bước.

### Kiểm Tra Toàn Bộ Hệ Thống Trước Khi Phát Hành
Trước khi đẩy commit hoặc phát hành bản mới, luôn chạy bộ kiểm tra toàn diện một lệnh:
```bash
bash scripts/check.sh
```
Lệnh này tự động kiểm tra cú pháp mã (Ruff), 53 bài test logic backend Python (Pytest), kiểm thử IndexedDB trên môi trường Node (Node Test runner), và kiểm thử hành trình người dùng E2E trên trình duyệt thực (Playwright Desktop & Mobile).
