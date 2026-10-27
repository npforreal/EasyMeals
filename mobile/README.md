# EasyMeals — Ứng dụng Di động Thuần Native (Android & iOS)

Tài liệu này hướng dẫn cách cấu hình, biên dịch, kiểm thử và vận hành ứng dụng di động thuần native (**Pure Native Mobile App**) của EasyMeals trên Android và iOS.

---

## 1. Tổng quan Kiến trúc Native Mới (`mobile/`)

EasyMeals cung cấp 2 ứng dụng thuần native 100% không phụ thuộc framework hybrid:

1. **Android (`mobile/android/`)**:
   - **Ngôn ngữ & Framework**: Kotlin 2.0.21, Jetpack Compose, Material 3, Android Gradle Plugin 8.7.2.
   - **Yêu cầu môi trường**: JDK 21 (OpenJDK 21 khuyến nghị trên macOS), Android SDK (minSdk 26, targetSdk 35).
   - **Bảo mật tuyệt đối**: **KHÔNG CÓ QUYỀN INTERNET** (`android.permission.INTERNET` bị loại bỏ hoàn toàn trong `AndroidManifest.xml`), `allowBackup="false"`, `usesCleartextTraffic="false"`. Manifest chỉ khai báo `VIBRATE` và `POST_NOTIFICATIONS`; quyền thông báo chỉ được xin khi người dùng bật "Nhắc việc" trong Cài đặt (receiver `exported="false"`, không push server).
   - **Số học chính xác**: `ExactDecimal` bọc `java.math.BigDecimal` với chuẩn hoá số không dư (`stripTrailingZeros()`), đảm bảo khớp 100% với Python `Decimal` và JavaScript `Decimal`.

2. **iOS (`mobile/ios/`)**:
   - **Ngôn ngữ & Framework**: Swift 5.9 / 6.0, SwiftUI, Foundation Decimal, Swift Package Manager.
   - **Yêu cầu môi trường**: macOS 14+, Xcode 15+ (iOS 17+ deployment target).
   - **Bảo mật tuyệt đối**: **KHÔNG CÓ ATS EXCEPTION** (`NSAppTransportSecurity` / `NSAllowsArbitraryLoads`), không theo dõi, chạy hoàn toàn offline trên sandbox của máy. Chỉ xin quyền thông báo hệ thống khi người dùng bật "Nhắc việc"; thông báo được tạo cục bộ, không có push server.
   - **Số học chính xác**: `ExactDecimal` bọc `Foundation.Decimal` với quy tắc làm tròn `bankers` / `plainString`, đảm bảo kết quả trùng khớp chính xác bộ dữ liệu mẫu `engine_test_cases.json`.

---

## 2. Đồng bộ Assets & Dữ liệu Danh mục

Toàn bộ dữ liệu món ăn Việt Nam (`catalogue.json`) và bộ ca kiểm thử quy chuẩn (`engine_test_cases.json`) được đồng bộ tự động từ thư mục gốc dự án vào các ứng dụng native thông qua script:

```bash
# Đồng bộ assets vào Android & iOS
python scripts/sync_mobile_assets.py

# Kiểm tra tính toàn vẹn (SHA256) của assets đã đồng bộ
python scripts/sync_mobile_assets.py --check
```

Assets đích:
- **Android**: `mobile/android/app/src/main/assets/catalogue.json` & `mobile/android/app/src/test/resources/engine_test_cases.json`
- **iOS**: `mobile/ios/EasyMeals/Resources/catalogue.json` & `mobile/ios/EasyMealsTests/Resources/engine_test_cases.json`

---

## 3. Kiểm thử Tương đương Một Lệnh (`scripts/check_mobile.sh`)

Script chạy tự động kiểm tra toàn diện 3 phần:
1. Kiểm tra mã SHA256 assets catalogue & engine test cases.
2. Android: Chạy JUnit `EngineEquivalenceTest` trên JVM OpenJDK 21.
3. iOS: Chạy `EngineTests` qua `swift test` (XCTest).

```bash
bash scripts/check_mobile.sh
```

Kết quả:
- **Android**: 7/7 ca kiểm thử tương đương đạt chuẩn (`testUnitConversions`, `testFifoStockDeduction`, `testUndoConsumption`, `testMealPlannerGeneration`, `testFifoSameExpiryTiebreak`, `testStockInsufficient`, `testIncompatibleUnitThrows`).
- **iOS**: 7/7 ca kiểm thử tương đương đạt chuẩn (0 thất bại).

---

## 4. Biên dịch & Cài đặt Ứng dụng Android

```bash
cd mobile/android
export JAVA_HOME="/opt/homebrew/opt/openjdk@21"

# Biên dịch APK gỡ lỗi
./gradlew --no-daemon assembleDebug

# File APK xuất xưởng:
# mobile/android/app/build/outputs/apk/debug/app-debug.apk
```

Cài đặt lên máy Android thực tế hoặc máy ảo qua ADB:
```bash
adb install -r mobile/android/app/build/outputs/apk/debug/app-debug.apk
```

---

## 5. Biên dịch & Chạy Ứng dụng iOS

```bash
cd mobile/ios

# Chạy bộ test trên máy Mac (XCTest/Swift Test)
swift test

# Hoặc mở trong Xcode:
open Package.swift
# Chọn target EasyMeals và chạy trên iOS Simulator / iPhone thật
```

---

## 6. Giao diện & Chủ đề Màu (Design Tokens & Theming)

Cả hai ứng dụng Android và iOS được đồng bộ trực tiếp từ `design-tokens/tokens.json`:
- **5 bộ màu sắc**: Xanh lá (Mặc định), Cam đất, Xanh biển, Tím mận, Hồng đào.
- **3 chế độ**: Sáng / Tối / Theo hệ thống (lưu trữ độc lập trên thiết bị qua DataStore/UserDefaults).
- **Phông chữ Fraunces**: Nhúng sẵn offline (`fraunces.ttf` trong Android `res/font` và iOS `Resources/Fonts`), giấy phép OFL (ghi nhận tại `NOTICE`).
- **Nút "Xem công thức" trong Thực đơn**: Cho phép xem nguyên liệu (tô màu theo tình trạng tủ lạnh), các bước thực hiện, tuỳ chỉnh khẩu phần và bật chế độ nấu toàn màn hình.

---

## 7. Kiểm thử Bốn Hành trình Người dùng (User Journeys)

Kiểm thử tự động trên Android và iOS bao phủ toàn bộ 4 hành trình cốt lõi:
1. **Thêm đồ vào tủ (Pantry addition)**: Nhập nguyên liệu, đơn vị mặc định hợp lý, gợi ý không dấu, cảnh báo hạn dùng.
2. **Lập thực đơn -> Đã ăn -> Hoàn tác**: Trừ kho FIFO (có hỗ trợ quy đổi Gạo ↔ Cơm) và hoàn tác nguyên tử.
3. **Đi chợ -> Mua hàng -> Cho vào tủ**: Đồng bộ phần thiếu vào danh sách mua sắm, chuyển hàng đã mua sang tủ.
4. **Duyệt công thức & Chế độ nấu**: Duyệt 133 món ăn, điều chỉnh khẩu phần, xem bước nấu.

---

## 8. Bản Hybrid cũ (Capacitor) — đã gỡ

Các vỏ Capacitor (`android/`, `ios/` ở thư mục gốc, `capacitor.config.json`, gói `@capacitor/*`) đã được gỡ khỏi dự án ở v2.0.0. Thư mục `www/` chỉ còn là bản web tĩnh sinh ra khi chạy `scripts/check.sh` để kiểm thử E2E Offline.

Quy trình phát hành: xem [`docs/release.md`](../docs/release.md).
