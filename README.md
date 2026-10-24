# EasyMeals — Sổ Tay Bữa Ăn Thông Minh

> Ứng dụng web, PWA & Mobile lập kế hoạch bữa ăn dựa trên nguyên liệu sẵn có trong tủ lạnh, tự động trừ kho khi nấu và giữ lại đồ thừa cho thực đơn sau theo chuẩn văn hoá ẩm thực gia đình Việt.
>
> **Đặc trưng kiến trúc**: Không lưu dữ liệu cá nhân trên server (Zero Server-side Personal Data). Toàn bộ thực phẩm, thực đơn và lịch sử kho lưu trong IndexedDB của thiết bị; Backend FastAPI hoàn toàn không trạng thái (stateless); Supabase chỉ lưu danh mục công khai chỉ đọc cho Web.
>
> **Hai đường dữ liệu chuyên biệt**:
> - **Bản Web (Desktop & Mobile Browser / PWA)**: Đồng bộ danh mục từ Supabase (`/api/catalogue` với ETag 304). Dữ liệu cá nhân lưu trong IndexedDB của trình duyệt.
> - **Bản Mobile (Capacitor Android / iOS)**: **Chạy 100% offline hoàn toàn**, không gọi Supabase, không gọi backend. Danh mục được đóng gói sẵn trong ứng dụng (`catalogue.json`), thuật toán lập thực đơn và trừ kho FIFO chạy trực tiếp trên thiết bị bằng JavaScript Engine (`engine.js`) với số học Decimal chính xác.


---

## MỤC LỤC
- [Phần 1: Hướng dẫn dành cho Người dùng (User Guide)](#phần-1-hướng-dẫn-dành-cho-người-dùng-user-guide)
  - [1. Giới thiệu tổng quan](#1-giới-thiệu-tổng-quan)
  - [2. Các tính năng chính](#2-các-tính-năng-chính)
  - [3. Hướng dẫn sử dụng chi tiết](#3-hướng-dẫn-sử-dụng-chi-tiết)
  - [4. Quản lý dữ liệu, Sao lưu & Phục hồi](#4-quản-lý-dữ-liệu-sao-lưu--phục-hồi)
  - [5. Cài đặt ứng dụng (PWA & Mobile)](#5-cài-đặt-ứng-dụng-pwa--mobile)
- [Phần 2: Hướng dẫn dành cho Lập trình viên (Developer Guide)](#phần-2-hướng-dẫn-dành-cho-lập-trình-viên-developer-guide)
  - [1. Yêu cầu môi trường](#1-yêu-cầu-môi-trường)
  - [2. Cài đặt và chạy Local](#2-cài-đặt-và-chạy-local)
  - [3. Cấu trúc thư mục dự án](#3-cấu-trúc-thư-mục-dự-án)
  - [4. Cơ sở dữ liệu danh mục & RLS](#4-cơ-sở-dữ-liệu-danh-mục--rls)
  - [5. Kiểm thử và đảm bảo chất lượng](#5-kiểm-thử-và-đảm-bảo-chất-lượng)
  - [6. Triển khai (Deployment Guide)](#6-triển-khai-deployment-guide)

---

# Phần 1: Hướng dẫn dành cho Người dùng (User Guide)

### 1. Giới thiệu tổng quan
**EasyMeals** được thiết kế theo phong cách *"Sổ tay bếp"* (kitchen notebook) ấm cúng, tối giản và trực quan, hỗ trợ đầy đủ cả chế độ **Sáng (Light Mode)** và **Tối (Dark Mode)**, tương thích xuất sắc trên cả máy tính lẫn điện thoại di động.

Điểm nổi bật nhất của EasyMeals là **Bảo vệ quyền riêng tư tuyệt đối**: Bạn không cần đăng ký tài khoản hay đăng nhập. Mọi thông tin về đồ ăn trong nhà, lịch sử ăn uống hoàn toàn nằm trên máy của bạn và không bao giờ bị thu thập lên máy chủ.

---

### 2. Các tính năng chính
- 🥦 **Quản lý tủ lạnh (Pantry Tracking)**: Theo dõi khối lượng từng loại thịt, cá, rau củ theo đơn vị chuẩn (`g`, `kg`, `ml`, `l`, `cái`).
- 📅 **Lập thực đơn chuẩn mâm cơm gia đình (Meal Planning)**:
  - Cân bằng dinh dưỡng: Món Mặn, Món Rau, Món Canh trong một bữa (tối đa 2 món mỗi nhóm).
  - Thuật toán thông minh **không lặp lại món đã nấu** trong chu kỳ đợt.
  - Tự động tận dụng thức ăn còn dư (leftovers) từ bữa trước để tránh lãng phí.
- 🍲 **Sổ tay công thức (Recipes)**: Hơn 1.200 nguyên liệu và công thức phong phú kèm định lượng và hướng dẫn nấu chi tiết.
- 🛒 **Danh sách đi chợ (Shopping List)**: Tự động tổng hợp danh sách nguyên liệu cần mua bổ sung nếu tủ lạnh thiếu đồ để nấu đủ món mới.
- ✅ **Đánh dấu "Đã ăn" & Trừ kho tự động**:
  - Trừ kho theo nguyên tắc FIFO (nguyên liệu mua trước dùng trước).
  - Giao dịch nguyên tử (atomic transaction): Chống trừ đúp khi bấm nhiều lần; có nút "Hoàn tác" để phục hồi nguyên liệu ngay lập tức.
- 💾 **Sao lưu & Khôi phục dữ liệu**: Xuất và nhập file sao lưu định dạng JSON bảo mật, độc lập giữa các thiết bị.

---

### 3. Hướng dẫn sử dụng chi tiết

#### Bước 1: Khai báo nguyên liệu trong tủ
1. Tại trang **Tủ lạnh** (`/`), nhập tên nguyên liệu vào ô tìm kiếm (gợi ý tự động cả tiếng Việt như *"Thịt ba chỉ"*, *"Rau muống"* và các tên gọi đồng nghĩa).
2. Nhập số lượng và chọn đơn vị tính (`g`, `kg`, `ml`, `l`, `cái`).
3. Bấm **Lưu vào tủ lạnh**. Nguyên liệu sẽ xuất hiện ngay trong danh sách tồn kho trên máy của bạn.

#### Bước 2: Tạo kế hoạch bữa ăn
1. Chuyển sang trang **Thực đơn** (`/planner`).
2. Chọn khoảng thời gian (mặc định 1 tuần), tuỳ chọn cho phép ăn lại đồ dư thừa.
3. Bấm **Tạo thực đơn tự động**: Hệ thống sẽ tính toán và lên lịch chi tiết từng bữa ăn cân đối.
4. Nếu tủ còn thiếu nguyên liệu, cảnh báo sẽ xuất hiện kèm liên kết dẫn đến trang **Cần mua** (`/shopping-list`).

#### Bước 3: Nấu ăn và Đánh dấu hoàn thành
1. Bấm vào món ăn để xem chi tiết công thức và các bước nấu.
2. Sau khi dùng bữa, bấm nút **Đánh dấu Đã ăn (Trừ kho)**:
   - Các nguyên liệu tương ứng sẽ tự động được trừ khỏi tủ lạnh theo nguyên tắc FIFO.
   - Thao tác có thể hoàn tác bất kỳ lúc nào bằng nút **Hoàn tác bữa ăn**.

---

### 4. Quản lý dữ liệu, Sao lưu & Phục hồi
Truy cập trang **Dữ liệu** (`/settings`):
- **Xuất tệp sao lưu**: Bấm **Xuất file sao lưu (JSON)** để tải toàn bộ nguyên liệu, thực đơn và lịch sử kho về máy tính/điện thoại.
- **Nhập từ file sao lưu**: Chọn file sao lưu đã có. Bạn có thể chọn **Hợp nhất (Merge)** hoặc **Ghi đè (Replace)**.
- **Xoá sạch dữ liệu**: Bấm **Xoá toàn bộ dữ liệu trên máy này** (yêu cầu xác nhận 2 bước) để dọn sạch dữ liệu cục bộ.

---

### 5. Cài đặt ứng dụng (PWA & Mobile)
- **Trên Android (Chrome)**: Mở trang web -> Bấm biểu tượng ba chấm `⋮` -> Chọn **Cài đặt ứng dụng** (Install App).
- **Trên iOS / iPhone (Safari)**: Mở trang web -> Bấm biểu tượng **Chia sẻ** -> Chọn **Thêm vào MH chính** (Add to Home Screen).
- **Ứng dụng Native (Capacitor)**: Dự án hỗ trợ đóng gói trực tiếp thành APK cho Android và ứng dụng iOS thông qua thư mục `android/` và `ios/`.

---

# Phần 2: Hướng dẫn dành cho Lập trình viên (Developer Guide)

### 1. Yêu cầu môi trường
- **Python**: Phiên bản 3.12 trở lên.
- **Node.js**: Phiên bản 20 trở lên (để chạy Playwright e2e và JS tests).
- **Supabase**: Một project Supabase (chỉ cần Anon / Public Key cho runtime).

---

### 2. Cài đặt và chạy Local

```bash
# 1. Clone repository
git clone https://github.com/npforreal/EasyMeals.git
cd EasyMeals

# 2. Khởi tạo môi trường ảo Python & cài đặt dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install ruff pytest

# 3. Cài đặt Node dependencies & Playwright browsers
npm install
npx playwright install chromium

# 4. Thiết lập biến môi trường
cp .env.example .env
# Mặc định APP_ENV=development app sẽ tự động dùng FixtureCatalogueRepository
# (không bắt buộc phải có kết nối Supabase thật để chạy dev hay test)

# 5. Khởi chạy ứng dụng dev server
uvicorn app.main:app --reload --port 8000
```
Truy cập trình duyệt tại `http://localhost:8000`.

---

### 3. Cấu trúc thư mục dự án

```text
EasyMeals/
├── app/
│   ├── main.py              # Khởi tạo FastAPI app, middleware (256KB limit, CSP, lockdown /docs)
│   ├── schemas.py           # Pydantic schemas (Stateless request/response validation)
│   ├── api/                 # REST API Routers không trạng thái
│   │   ├── deps.py          # Dependency injection (Repository provider)
│   │   ├── catalogue_routes.py  # GET /api/catalogue (ETag / If-None-Match caching)
│   │   ├── ingredient_routes.py # Tra cứu nguyên liệu
│   │   ├── planner_routes.py    # /generate, /eat, /undo-eat (tính toán không trạng thái)
│   │   └── recipe_routes.py     # Tra cứu công thức
│   ├── domain/              # Logic nghiệp vụ độc lập framework
│   │   ├── models.py        # Domain entities (Ingredient, Recipe, PantryLot...)
│   │   ├── inventory.py     # Thuật toán trừ kho FIFO, hoàn tác biến động kho
│   │   └── planner.py       # Quy tắc thực đơn (cân bằng mặn/rau/canh, không lặp món)
│   ├── storage/
│   │   └── repository.py    # Repository danh mục chỉ đọc: Fixture vs Supabase (anon key)
│   ├── static/              # Assets tĩnh & Client Storage
│   │   ├── app.js           # UI Controller điều khiển toàn bộ logic cục bộ
│   │   ├── sw.js            # Service Worker offline cache
│   │   ├── styles.css       # Design tokens, responsive CSS & dark mode
│   │   └── js/
│   │       ├── db.js        # IndexedDB wrapper (pantry, plans, movements, settings, catalogue)
│   │       ├── engine.js    # Client computational engine (Decimal math, FIFO deduction, planner offline)
│   │       └── storage.js   # Client CRUD, atomic eat/undo, JSON export/import, bundled/remote catalogue
│   └── templates/           # Jinja2 HTML templates (5 trang: index, planner, recipes, shopping, settings)
├── docs/
│   ├── architecture.md      # Tài liệu kiến trúc Zero Server-side Personal Data (Web vs Mobile)
│   ├── security.md          # Đánh giá và mô hình bảo mật
│   └── deploy.md            # Hướng dẫn chi tiết triển khai Supabase, Vercel & đóng gói Mobile Offline
├── scripts/
│   ├── check.sh             # Một lệnh chạy toàn bộ test: Ruff lint, Pytest, Node test, Playwright e2e
│   ├── export_catalogue.py  # Xuất gói danh mục catalogue.json cho Mobile App
│   ├── build_mobile_web.py  # Đóng gói trang web tĩnh vào www/ cho Capacitor (quét sạch bí mật)
│   ├── verify_rls.py        # Kiểm chứng RLS Supabase chỉ đọc với khoá anon
│   └── seed_catalogue.py    # Nạp dữ liệu danh mục ban đầu vào Supabase (idempotent)
├── supabase/
│   ├── full_schema.sql      # Schema SQL tổng hợp của 4 bảng danh mục
│   └── migrations/
│       └── 202610240001_catalogue_baseline.sql # Migration duy nhất cho danh mục chỉ đọc & RLS
├── tests/
│   ├── e2e/                 # Playwright E2E tests (Desktop Chrome & Pixel 5 Mobile)
│   ├── js/                  # Node unit tests cho IndexedDB storage
│   ├── test_api.py          # Test endpoints không trạng thái
│   ├── test_catalogue_schema.py # Test RLS và schema Supabase
│   └── ...
└── INSTALL.md               # Hướng dẫn cài đặt chi tiết
```

---

### 4. Cơ sở dữ liệu danh mục & RLS

Cơ sở dữ liệu Supabase được tái cấu trúc thành **Shared Read-Only Catalogue**:
- Chỉ lưu 4 bảng: `ingredients`, `ingredient_aliases`, `recipes`, `recipe_ingredients`.
- RLS được kích hoạt 100%: Chỉ cho phép quyền `SELECT` cho role `anon` và `authenticated`.
- Thu hồi tường minh toàn bộ quyền ghi (`INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`).
- Script nạp seed [`scripts/seed_catalogue.py`](file:///Users/phucnguyen/projects/app/EasyMeals/scripts/seed_catalogue.py) là công cụ duy nhất dùng `SUPABASE_SERVICE_ROLE_KEY` và chỉ chạy 1 lần ngoại tuyến từ máy lập trình viên. Server web runtime tuyệt đối cấm khoá này.

---

### 5. Kiểm thử và đảm bảo chất lượng

Dự án tuân thủ nghiêm ngặt nguyên tắc **một lệnh chạy tất cả**:
```bash
bash scripts/check.sh
```

Quy trình tự động thực hiện 5 bước:
1. `ruff check`: Kiểm tra cú pháp và quy chuẩn mã nguồn Python.
2. `ruff format --check`: Kiểm tra định dạng code.
3. `pytest tests/`: Chạy toàn bộ bài kiểm thử unit test Python (thuật toán FIFO, quy tắc thực đơn, bảo mật DoS, schema catalogue, fixture tương đương).
4. `npm run test:js`: Kiểm thử unit test cho tầng lưu trữ IndexedDB, transaction nguyên tử, kiểm tra sao lưu và engine tính toán JS.
5. `npx playwright test`: Kiểm thử tự động hành trình người dùng toàn diện (E2E User Journey) trên cả Desktop Chrome, Mobile Chrome và static build offline.

---

### 6. Triển khai (Deployment Guide)
Xem tài liệu hướng dẫn chi tiết tại [docs/deploy.md](file:///Users/phucnguyen/projects/app/EasyMeals/docs/deploy.md).

---

## Lịch sử phiên bản
Lịch sử commit cũ của repository đã bị xoá vì mục đích bảo mật. Lịch sử hiện tại bắt đầu từ bản phát hành v1.3.0.

---

## Giấy phép (License)
Dự án được phát hành dưới giấy phép mã nguồn mở MIT. Mọi đóng góp đều được hoan nghênh!
