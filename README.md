# EasyMeals — Sổ Tay Bếp Thông Minh

[![Live Web App](https://img.shields.io/badge/Web%20App-easymeals--nine.vercel.app-2ea44f?style=flat-square&logo=vercel)](https://easymeals-nine.vercel.app)
[![Latest Release](https://img.shields.io/github/v/release/npforreal/EasyMeals?style=flat-square&color=blue)](https://github.com/npforreal/EasyMeals/releases)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg?style=flat-square)](LICENSE)
[![Culinary Data: CC BY-SA 4.0](https://img.shields.io/badge/Data-CC_BY--SA_4.0-lightgrey.svg?style=flat-square)](data/LICENSE)

Ứng dụng lập kế hoạch bữa ăn dựa trên nguyên liệu sẵn có trong tủ lạnh, tự động tính toán định lượng mâm cơm gia đình Việt, trừ kho theo nguyên tắc FIFO và tái sử dụng đồ ăn dư để chống lãng phí thực phẩm.

- 🌐 **Truy cập bản Web**: [https://easymeals-nine.vercel.app](https://easymeals-nine.vercel.app)
- 📦 **Tải ứng dụng Mobile (v2.0.0)**: [GitHub Releases](https://github.com/npforreal/EasyMeals/releases) (APK Android & gói cài iOS)
- 📚 **Tài liệu**: [Kiến trúc](docs/architecture.md) • [Cài đặt](INSTALL.md) • [Triển khai](docs/deploy.md) • [Quy trình phát hành](docs/release.md) • [Bảo mật](SECURITY.md)

---

## Điểm Khác Biệt Trong Kiến Trúc

EasyMeals được xây dựng theo nguyên tắc **Zero Server-side Personal Data (Không lưu dữ liệu cá nhân trên máy chủ)** và **Local-first**:

1. **Không tài khoản, không theo dõi**: Không đăng ký, không cookie định danh, không có bảng dữ liệu người dùng trên cloud.
2. **Lưu trữ cục bộ trên thiết bị**: Toàn bộ dữ liệu tủ lạnh, thực đơn, danh sách đi chợ và lịch sử biến động kho nằm hoàn toàn trong **IndexedDB** (trên Web) hoặc cơ sở dữ liệu cục bộ trên máy (Android Room / iOS SwiftData). Hỗ trợ xuất/nhập file sao lưu JSON an toàn giữa các thiết bị.
3. **Hai nền tảng phục vụ**:
   - **Bản Web & PWA**: Backend FastAPI trên Vercel hoàn toàn không trạng thái (stateless), tiếp nhận dữ liệu từ client để tính toán thực đơn và biến động kho rồi trả kết quả về máy người dùng mà **không ghi gì xuống database hay ổ đĩa**. Cơ sở dữ liệu Supabase chỉ đóng vai trò kho danh mục công khai ở chế độ **chỉ đọc (SELECT-only via RLS)**.
   - **Bản Mobile Native (Android & iOS)**: Viết bằng **Kotlin / Jetpack Compose** (Android) và **SwiftUI** (iOS), **chạy 100% offline**, không cần kết nối mạng. Danh mục món ăn (`catalogue.json`) được đóng gói sẵn trong ứng dụng; toàn bộ thuật toán tính toán và trừ kho chạy trực tiếp trên thiết bị với số học Decimal chính xác.

---

## Tính Năng Chính

- 🥬 **Quản lý tủ lạnh (Pantry)**: Quản lý chi tiết từng lô thực phẩm theo ngày mua, hạn dùng, đơn vị đo (`g`, `kg`, `ml`, `l`, `piece`). Cảnh báo thực phẩm sắp hết hạn và hỗ trợ gia hạn độ tươi.
- 📅 **Lập thực đơn mâm cơm gia đình (Meal Planning)**:
  - Linh hoạt từ 1 đến 7 ngày (mặc định 3 ngày).
  - Cân bằng cơ cấu mâm cơm truyền thống (Món Mặn, Rau, Canh).
  - Tuyệt đối không lặp lại món ăn trong đợt; tự động tránh các nguyên liệu dị ứng theo cài đặt.
  - Tuỳ chọn bữa ăn (sáng/trưa/tối), khẩu phần ăn mỗi người, và bỏ qua các ngày ăn ngoài.
- 🍲 **Tái sử dụng đồ ăn dư (Leftovers)**: Tự động tính toán lượng thức ăn dư từ bữa trước để dùng lại trong 1–3 ngày tiếp theo, tránh lãng phí.
- 🍚 **Quy đổi nguyên liệu thông minh**: Tự động quy đổi tỷ lệ thực phẩm (ví dụ: *Gạo $\leftrightarrow$ Cơm* với tỷ lệ nở 1:2.5) để trừ kho và lên danh sách mua chuẩn xác.
- 📖 **Sổ tay 133 món ăn chuẩn hoá**: Danh mục 133 món Việt và quốc tế kèm 148 nguyên liệu, hướng dẫn nấu, thời gian chuẩn bị/nấu và mẹo bảo quản thực phẩm theo hướng dẫn FDA.
- 🛒 **Danh sách đi chợ thông minh (Shopping List)**: Tự động tổng hợp các nguyên liệu còn thiếu khi lên thực đơn; cho phép gộp các món cùng nguyên liệu và chuyển đồ đã mua thẳng vào tủ lạnh.
- ⚡ **Trừ kho FIFO & Hoàn tác giao dịch**: Trừ kho nguyên liệu mua trước dùng trước, chống trừ lặp (idempotency key), cho phép hoàn tác phục hồi kho bất cứ lúc nào.
- 🔄 **Sao lưu & Khôi phục JSON**: Xuất và nhập dữ liệu cá nhân dạng JSON độc lập, hỗ trợ cả 2 chế độ Hợp nhất (Merge) hoặc Ghi đè (Replace).

---

## Cài Đặt Ứng Dụng

### 1. Web & PWA
Truy cập [https://easymeals-nine.vercel.app](https://easymeals-nine.vercel.app). 
- Trên Chrome (Android / Desktop): Bấm biểu tượng cài đặt trên thanh địa chỉ hoặc menu `⋮` $\rightarrow$ **Cài đặt EasyMeals**.
- Trên Safari (iOS): Bấm biểu tượng Chia sẻ $\rightarrow$ **Thêm vào Màn hình chính (Add to Home Screen)**.

### 2. Bản Cài Đặt Mobile Native
Tải tệp cài đặt mới nhất từ [GitHub Releases](https://github.com/npforreal/EasyMeals/releases):
- **Android**: Tải file `EasyMeals-vX.Y.Z-android-debug.apk` và cài đặt trực tiếp.
- **iOS**: Xem hướng dẫn build mã nguồn qua Xcode trong [mobile/README.md](mobile/README.md).

---

## Hướng Dẫn Phát Triển (Developer Guide)

### Yêu Cầu Môi Trường
- **Python**: $\ge$ 3.12
- **Node.js**: $\ge$ 20 (dùng cho công cụ build asset và kiểm thử Playwright)
- **Android Studio / Xcode**: Dành cho phát triển ứng dụng di động native

### Khởi Chạy Local (Backend & Web)

```bash
# 1. Clone mã nguồn
git clone https://github.com/npforreal/EasyMeals.git
cd EasyMeals

# 2. Khởi tạo môi trường ảo Python & cài đặt dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install ruff pytest

# 3. Cài đặt Node dependencies
npm install

# 4. Cấu hình môi trường dev
cp .env.example .env
# Mặc định APP_ENV=development, hệ thống tự động nạp FixtureCatalogueRepository
# (không cần kết nối Supabase thật để chạy test và dev cục bộ)

# 5. Khởi chạy máy chủ phát triển
uvicorn app.main:app --reload --port 8000
```
Mở trình duyệt tại: `http://localhost:8000`

---

## Kiểm Thử & Đảm Bảo Chất Lượng

Dự án áp dụng quy chuẩn kiểm thử một lệnh duy nhất:

```bash
# Chạy nhanh trong quá trình code (bỏ qua Playwright e2e):
bash scripts/check.sh --fast

# Chạy kiểm tra toàn diện trước khi phát hành:
bash scripts/check.sh
```

Quy trình tự động xác minh:
1. Đồng bộ Design Tokens (`tokens.json` & `labels.json`) và số phiên bản ở tất cả nền tảng.
2. Kiểm tra cú pháp và định dạng mã (`ruff check`, `ruff format`).
3. Chạy toàn bộ unit test logic Python (`pytest` - thuật toán FIFO, quy tắc thực đơn, an toàn RLS, xử lý lỗi).
4. Chạy kiểm thử JavaScript trên môi trường Node (`npm run test:js` - IndexedDB, tính tương đương của Engine).
5. Đóng gói mã nguồn tĩnh và quét kiểm tra an toàn thư mục `www/`.
6. Kiểm thử hành trình người dùng E2E trên trình duyệt thực với Playwright (Desktop & Mobile).

Với mã nguồn Native Mobile:
```bash
# Kiểm tra Android Unit Tests & iOS Swift Tests:
bash scripts/check_mobile.sh
```

---

## Cấu Trúc Dự Án

```text
EasyMeals/
├── app/                      # Backend FastAPI stateless & Web Frontend
│   ├── main.py               # Khởi tạo FastAPI, middleware bảo mật, xử lý lỗi
│   ├── schemas.py            # Pydantic schemas xác thực request/response
│   ├── api/                  # Endpoints tính toán không trạng thái (/planner, /catalogue...)
│   ├── domain/               # Logic nghiệp vụ độc lập (inventory, planner, models)
│   ├── storage/              # Repository danh mục: Fixture (dev) vs Supabase (prod)
│   ├── static/               # Mã nguồn giao diện Web: app.js, css, icons
│   │   └── js/               # IndexedDB (db.js), Engine tính toán cục bộ (engine.js)
│   └── templates/            # Giao diện Jinja2 HTML (index, planner, recipes, shopping, settings)
├── data/                     # Dữ liệu danh mục chuẩn hoá (catalogue.json, open/*.jsonl)
├── mobile/                   # Ứng dụng di động Native 100%
│   ├── android/              # Mã nguồn Android (Kotlin / Jetpack Compose)
│   └── ios/                  # Mã nguồn iOS (SwiftUI)
├── supabase/                 # Migration SQL và schema danh mục chỉ đọc
│   ├── full_schema.sql       # Toàn bộ schema 6 bảng danh mục chuẩn
│   └── migrations/           # Các bản migration có đánh số phiên bản
├── docs/                     # Tài liệu kỹ thuật chi tiết
│   ├── architecture.md       # Thiết kế kiến trúc Local-first & Zero Server-side Personal Data
│   ├── deploy.md             # Hướng dẫn triển khai Supabase & Vercel
│   ├── release.md            # Chính sách phiên bản và quy trình phát hành
│   └── parity.md             # Bảng đối sánh tính năng giữa Web, Android và iOS
└── scripts/                  # Bộ script tiện ích tự động hoá
    ├── check.sh              # Kiểm tra tổng hợp toàn bộ dự án
    ├── check_mobile.sh       # Kiểm tra toàn bộ mã nguồn Android & iOS
    └── upload_catalogue_to_supabase.py # Nạp danh mục lên Supabase
```

---

## Đóng Góp & Bảo Mật

- Hướng dẫn đóng góp mã nguồn: [CONTRIBUTING.md](CONTRIBUTING.md)
- Quy tắc ứng xử cộng đồng: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Chính sách báo cáo lỗ hổng bảo mật: [SECURITY.md](SECURITY.md)

---

## Giấy Phép & Bản Quyền

- **Mã nguồn (Source Code)**: Phát hành theo giấy phép **Apache License 2.0** (xem [LICENSE](LICENSE) và [NOTICE](NOTICE)).
- **Dữ liệu ẩm thực (Culinary Data)**: Dữ liệu công thức và nguyên liệu trong thư mục `data/` được cấp phép theo **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)** (xem [data/LICENSE](data/LICENSE)).
