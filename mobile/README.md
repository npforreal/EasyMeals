# EasyMeals — Ứng dụng Di động Thuần Native (Android & iOS)

Tài liệu này hướng dẫn cách cấu hình, biên dịch, kiểm thử và vận hành ứng dụng di động thuần native (**Pure Native Mobile App**) của EasyMeals trên Android và iOS.

---

## 1. Tổng quan Kiến trúc Native Mới (`mobile/`)

EasyMeals cung cấp 2 ứng dụng thuần native 100% không phụ thuộc framework hybrid:

1. **Android (`mobile/android/`)**:
   - **Ngôn ngữ & Framework**: Kotlin 2.0.21, Jetpack Compose, Material 3, Android Gradle Plugin 8.7.2.
   - **Yêu cầu môi trường**: JDK 21 (OpenJDK 21 khuyến nghị trên macOS), Android SDK (minSdk 26, targetSdk 35).
   - **Bảo mật tuyệt đối**: **KHÔNG CÓ QUYỀN INTERNET** (`android.permission.INTERNET` bị loại bỏ hoàn toàn trong `AndroidManifest.xml`), `allowBackup="false"`, `usesCleartextTraffic="false"`.
   - **Số học chính xác**: `ExactDecimal` bọc `java.math.BigDecimal` với chuẩn hoá số không dư (`stripTrailingZeros()`), đảm bảo khớp 100% với Python `Decimal` và JavaScript `Decimal`.

2. **iOS (`mobile/ios/`)**:
   - **Ngôn ngữ & Framework**: Swift 5.9 / 6.0, SwiftUI, Foundation Decimal, Swift Package Manager.
   - **Yêu cầu môi trường**: macOS 14+, Xcode 15+ (iOS 17+ deployment target).
   - **Bảo mật tuyệt đối**: **KHÔNG CÓ ATS EXCEPTION** (`NSAppTransportSecurity` / `NSAllowsArbitraryLoads`), không theo dõi, chạy hoàn toàn offline trên sandbox của máy.
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

# Chạy bộ test trên máy Mac
swift test

# Hoặc mở trong Xcode:
open Package.swift
# Chọn target EasyMeals và chạy trên iOS Simulator / iPhone thật
```

---

## 6. Phiên bản Hybrid Cũ (Capacitor)

Dự án vẫn duy trì mã nguồn hybrid cũ trong `android/`, `ios/`, và `www/` cho mục đích tham chiếu và kiểm thử E2E Playwright qua `bash scripts/check.sh`.
