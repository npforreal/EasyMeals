# Hướng Dẫn Cài Đặt & Triển Khai EasyMeals (INSTALL.md)

Tài liệu này hướng dẫn chi tiết từng bước từ A đến Z cách thiết lập cơ sở dữ liệu **Supabase**, triển khai ứng dụng web **Vercel**, nạp kho dữ liệu món ăn ẩm thực Việt Nam phong phú, và đóng gói ứng dụng di động **Android / iOS** chạy hoàn toàn offline.

---

## 📌 1. Kiến Trúc Bảo Mật Cần Nắm Rõ
EasyMeals được thiết kế theo kiến trúc **Zero Server-side Personal Data**:
* **Không lưu dữ liệu cá nhân trên Server**: Toàn bộ dữ liệu thực phẩm trong tủ lạnh, thực đơn hàng ngày, lịch sử ăn uống và danh sách đi chợ được lưu trữ **100% trong IndexedDB** trên thiết bị của người dùng (trình duyệt hoặc ứng dụng di động).
* **Supabase (Cơ sở dữ liệu danh mục chỉ đọc)**: Chỉ chứa 4 bảng danh mục chung công khai: `ingredients` (nguyên liệu), `ingredient_aliases` (bí danh), `recipes` (món ăn), và `recipe_ingredients` (định lượng). Tất cả được bảo vệ bởi **Row Level Security (RLS)** ở chế độ `SELECT-only`.
* **Vercel (Backend không trạng thái - Stateless)**: FastAPI chỉ thực hiện các thuật toán tính toán (gợi ý thực đơn, tính toán trừ kho FIFO) và trả về kết quả cho client.

---

## 🚀 2. Thiết Lập Supabase Từ A Đến Z

### Bước 2.1: Tạo Project Trên Supabase
1. Truy cập [https://supabase.com](https://supabase.com) và đăng nhập (hoặc đăng ký tài khoản miễn phí).
2. Nhấn nút **New Project**.
3. Điền các thông tin:
   * **Name**: `easymeals` (hoặc tên tùy thích).
   * **Database Password**: Nhập mật khẩu an toàn và lưu lại.
   * **Region**: Chọn khu vực gần Việt Nam nhất (khuyến nghị: **Singapore - ap-southeast-1**).
   * **Pricing Plan**: Chọn gói **Free** (hoàn toàn miễn phí).
4. Nhấn **Create new project** và chờ khoảng 1 - 2 phút để hệ thống khởi tạo.

### Bước 2.2: Lấy Thông Tin API Keys
Vào mục **Project Settings** (biểu tượng bánh răng ở góc dưới bên trái) -> Chọn **API**:
1. **Project URL**: Có dạng `https://[project-id].supabase.co`.
2. **Anon / Publishable Key**: Dòng khoá dán nhãn `anon` `public` (bắt đầu bằng `eyJ...` hoặc `sb_publishable_...`). Đây là khoá công khai chỉ đọc, an toàn để sử dụng trên Vercel.
3. **Service Role Key**: Dòng khoá dán nhãn `service_role` `secret` (bắt đầu bằng `eyJ...` hoặc `sb_secret_...`). 
   > [!CAUTION] **CẢNH BÁO BẢO MẬT**
   > Khoá `service_role` có quyền vượt qua RLS và chỉ được dùng **duy nhất một lần trên máy tính cá nhân của bạn** khi chạy script nạp danh mục (seed). Tuyệt đối **KHÔNG** đưa khoá này lên Vercel hay lưu vào file `.env` của ứng dụng.

### Bước 2.3: Chạy SQL Migration Thiết Lập Bảng & RLS
1. Trên thanh menu bên trái Supabase Dashboard, chọn **SQL Editor**.
2. Nhấn **New Query**.
3. Mở tệp [`supabase/migrations/202610240001_catalogue_baseline.sql`](supabase/migrations/202610240001_catalogue_baseline.sql) trong thư mục mã nguồn EasyMeals, copy toàn bộ nội dung dán vào ô soạn thảo SQL.
4. Nhấn nút **Run** (màu xanh lá) ở góc dưới bên phải.
5. Kiểm tra thông báo `Success. No rows returned`.
   * *Tác vụ này sẽ tạo 4 bảng chuẩn, kích hoạt RLS 100%, cấp quyền SELECT cho role `anon` và thu hồi toàn bộ quyền INSERT/UPDATE/DELETE.*

### Bước 2.4: Nạp Kho Món Ăn & Nguyên Liệu (Seed Data)
Mở cửa sổ terminal trên máy tính của bạn tại thư mục gốc của dự án `EasyMeals`:

```bash
# Kích hoạt môi trường ảo Python
source .venv/bin/activate

# LỰA CHỌN 1: Nạp bộ món Việt mẫu cơ bản (29 nguyên liệu, 5 món kinh điển)
SUPABASE_URL="https://[project-id].supabase.co" \
SUPABASE_SERVICE_ROLE_KEY="[khoá-service-role-của-bạn]" \
python scripts/seed_catalogue.py --apply

# LỰA CHỌN 2 (KHUYẾN NGHỊ): Nạp TOÀN BỘ kho 105+ món gia đình Việt Nam và 25 món quốc tế chuẩn
SUPABASE_URL="https://[project-id].supabase.co" \
SUPABASE_SERVICE_ROLE_KEY="[khoá-service-role-của-bạn]" \
python scripts/seed_catalogue.py --apply --with-harvest
```

Sau khi chạy xong, terminal sẽ thông báo số lượng nguyên liệu và công thức đã được nạp thành công vào Supabase.

### Bước 2.5: Kiểm Tra Lại Chính Sách RLS
Chạy script kiểm tra độc lập bằng khoá công khai `anon`:
```bash
SUPABASE_URL="https://[project-id].supabase.co" \
SUPABASE_ANON_KEY="[khoá-anon-của-bạn]" \
python scripts/verify_rls.py
```
Kết quả hiển thị `[OK]` cho tất cả các bảng (SELECT thành công, các lệnh ghi bị chặn 100%).

---

## ⚡ 3. Triển Khai Backend Lên Vercel Từ A Đến Z

### Bước 3.1: Nhập Kho Lưu Trữ (Import Git Repo)
1. Truy cập [https://vercel.com](https://vercel.com) và đăng nhập bằng tài khoản GitHub của bạn.
2. Tại trang Tổng quan (Dashboard), nhấn **Add New...** -> chọn **Project**.
3. Tìm và chọn repository `EasyMeals` (hoặc `npforreal/EasyMeals`), nhấn **Import**.

### Bước 3.2: Cấu Hình Dự Án Trên Vercel
* **Framework Preset**: Chọn **Other** (hệ thống tự động sử dụng cấu hình từ tệp `vercel.json` và `pyproject.toml`).
* **Root Directory**: Giữ nguyên `./`.

### Bước 3.3: Thêm Biến Môi Trường (Environment Variables)
Mở rộng phần **Environment Variables** và thêm 3 biến sau:

| Tên Biến (Name) | Giá Trị Ví Dụ (Value) | Môi Trường Áp Dụng | Ghi Chú |
|---|---|---|---|
| `SUPABASE_URL` | `https://xyz.supabase.co` | Production, Preview, Development | URL của project Supabase bạn vừa tạo |
| `SUPABASE_ANON_KEY` | `eyJhbGciOi...` hoặc `sb_publishable_...` | Production, Preview, Development | Khoá `anon public` (hoặc đặt tên `SUPABASE_PUBLISHABLE_KEY`) |
| `APP_ENV` | `production` | Production, Preview, Development | Kích hoạt chế độ bảo vệ Production |

> [!TIP]
> Nhớ tích chọn cả 3 ô: **Production**, **Preview**, và **Development** để khi truy cập link xem thử không bị lỗi thiếu biến môi trường.

### Bước 3.4: Bấm Deploy & Lưu Ý Về Redeploy
1. Nhấn nút **Deploy**. Vercel sẽ tự động cài đặt các thư viện Python, tối ưu mã nguồn và triển khai trong khoảng 1 phút.
2. **Lưu ý quan trọng**: Nếu trước đó bạn đã deploy mà chưa thêm biến môi trường (hoặc vừa chỉnh sửa biến môi trường):
   * Vào tab **Deployments**.
   * Bấm nút **`...`** (ba chấm) ở bản deploy mới nhất -> Chọn **Redeploy**.
   * Biến môi trường chỉ có hiệu lực sau khi bạn Redeploy lại phiên bản mới!

---

## 🔍 4. Kiểm Tra & Xác Minh Hoạt Động

Sau khi triển khai thành công, bạn sẽ nhận được đường dẫn dạng `https://easymeals-xyz.vercel.app`:

1. **Kiểm tra trạng thái liveness**:
   * Truy cập: `https://[tên-web].vercel.app/health`
   * Phản hồi chuẩn: `{"status": "ok", "service": "easymeals"}`
2. **Kiểm tra kết nối danh mục Supabase**:
   * Truy cập: `https://[tên-web].vercel.app/api/catalogue`
   * Phản hồi JSON chứa danh sách `ingredients` và `recipes` đầy đủ kèm header `ETag`.
3. **Kiểm tra khóa an toàn Production**:
   * Truy cập `https://[tên-web].vercel.app/docs` -> Trả về `404 Not Found` (đã được khoá an toàn ở chế độ production).
4. **Trải nghiệm ứng dụng trên Web**:
   * Vào trang chủ `/`: Tìm kiếm nguyên liệu và thêm vào tủ lạnh (dữ liệu lưu vào IndexedDB).
   * Vào trang `/planner`: Chọn số ngày và bấm **Lập thực đơn tự động** (FastAPI tính toán không trạng thái).
   * Bấm **Đã ăn** -> Số lượng thực phẩm trong tủ được tự động trừ theo nguyên lý FIFO.
   * Vào `/settings`: Bấm **Xuất file sao lưu (JSON)** để tải file dữ liệu về máy an toàn.

---

## 📱 5. Đóng Gói Ứng Dụng Di Động Chạy Offline (Native)

EasyMeals có ứng dụng native độc lập cho **Android** (Kotlin/Compose) và **iOS** (SwiftUI), không cần mạng hay Supabase. Danh mục đi kèm trong ứng dụng.

```bash
# 1. Xuất danh mục chuẩn và đồng bộ vào hai ứng dụng
python scripts/export_catalogue.py
python scripts/sync_mobile_assets.py

# 2. Android: build APK debug
cd mobile/android && ./gradlew assembleDebug
# → mobile/android/app/build/outputs/apk/debug/app-debug.apk

# 3. iOS: sinh project rồi mở bằng Xcode (cần `brew install xcodegen`)
cd ../ios && xcodegen generate && open EasyMeals.xcodeproj
```

### 🔗 Tài liệu chi tiết di động

EasyMeals hỗ trợ cả hai hình thức:
- **Ứng dụng Native**: Nằm tại `mobile/android/` (Kotlin + Jetpack Compose) và `mobile/ios/` (Swift + SwiftUI). Chạy hoàn toàn offline không cần quyền Internet. Kiểm thử tự động bằng `bash scripts/check_mobile.sh`.
- Bản Hybrid (Capacitor) cũ đã được gỡ bỏ; `www/` chỉ còn dùng làm bản web tĩnh cho kiểm thử E2E Offline.

Hướng dẫn chi tiết đóng gói, build và phát hành ứng dụng di động nằm tại [`mobile/README.md`](mobile/README.md).

**Lưu ý quan trọng về phát hành:**
- `www/` là artifact sinh ra từ bản build (`python scripts/build_mobile_web.py`), **không được commit** vào kho lưu trữ.
- Chưa có artifact release đã ký (AAB cho Google Play, IPA cho App Store). Bản APK/IPA đính kèm release chỉ để thử nghiệm (APK debug, IPA chưa ký); việc ký để phát hành lên cửa hàng ứng dụng do chủ dự án thực hiện.

---

## 🛠️ 6. Xử Lý Sự Cố Thường Gặp (Troubleshooting)

### Lỗi 1: Trang web mở lên nhưng báo "0 nguyên liệu, 0 công thức"
* **Nguyên nhân 1**: Bạn thêm biến môi trường trên Vercel sau khi deploy -> **Khắc phục**: Vào Vercel -> *Deployments* -> bấm `...` cạnh bản deploy mới nhất -> chọn **Redeploy**.
* **Nguyên nhân 2**: Cơ sở dữ liệu Supabase chưa được nạp seed -> **Khắc phục**: Chạy lệnh `python scripts/seed_catalogue.py --apply --with-harvest` từ terminal máy bạn.
* **Nguyên nhân 3**: Trình duyệt đang giữ cache IndexedDB rỗng của lần truy cập lỗi trước đó -> **Khắc phục**: Nhấn `Ctrl + F5` (hoặc `Cmd + Shift + R`), hoặc vào `/settings` bấm **Xoá toàn bộ dữ liệu trên máy này** và tải lại trang.

### Lỗi 2: API trả về mã lỗi 500 khi gọi `/api/catalogue`
* Kiểm tra log runtime trên Vercel (mục *Logs*).
* Đảm bảo giá trị biến `SUPABASE_URL` bắt đầu bằng `https://` và không thừa dấu cách ở đầu/cuối.
* Đảm bảo không truyền nhầm `SUPABASE_SERVICE_ROLE_KEY` vào biến môi trường Vercel (hệ thống sẽ chủ động từ chối khởi động nếu phát hiện khoá này).

### Lỗi 3: Chạy script seed báo `ModuleNotFoundError`
* Đảm bảo bạn đã kích hoạt đúng môi trường ảo Python trước khi chạy:
  ```bash
  source .venv/bin/activate
  ```
