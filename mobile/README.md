# EasyMeals — Ứng dụng Di động (Capacitor)

Tài liệu này dành cho việc đóng gói, build và vận hành phiên bản **Native Mobile** của EasyMeals trên Android và iOS.

---

## 1. Tổng quan

EasyMeals phiên bản mobile là ứng dụng **hybrid native** xây dựng với [Capacitor](https://capacitorjs.com/):

- **Hoàn toàn chạy offline**: Không gọi Supabase, không gọi backend FastAPI, không cần kết nối mạng sau khi cài đặt.
- **Danh mục đóng gói sẵn**: Toàn bộ nguyên liệu, công thức và định lượng được xuất ra file `catalogue.json` và đóng gói vào `www/data/catalogue.json` bên trong gói ứng dụng.
- **Tính toán trên thiết bị**: Thuật toán lập thực đơn, trừ kho FIFO, đổi đơn vị và hoàn tác bữa ăn chạy trực tiếp trên thiết bị bằng JavaScript Engine (`app/static/js/engine.js`) với số học Decimal chính xác.
- **Dữ liệu cá nhân ở máy người dùng**: Tủ lạnh, thực đơn, lịch sử biến động kho và cài đặt nằm trong **IndexedDB của WebView** trên thiết bị. Hỗ trợ xuất/nhập file JSON để sao lưu và chuyển máy.
- **Không có Supabase hay backend trong bản mobile**: Không chứa URL, API Key hay khoá Supabase nào trong thư mục `www/`.

---

## 2. Yêu cầu môi trường

- **Node.js**: 20 trở lên.
- **Python**: 3.12 trở lên (để chạy `scripts/export_catalogue.py` và `scripts/build_mobile_web.py`).
- **Android**: Android Studio, JDK 17, Android SDK (minSdk 23, compile/targetSdk 35).
- **iOS**: Xcode 15 trở lên, CocoaPods, iOS deployment target 15.0+.
- **Capacitor CLI**: `@capacitor/cli` (đã có trong `package.json`).

---

## 3. Chuẩn bị assets `www/`

Trước khi build native, phải xuất danh mục và đóng gói giao diện web tĩnh vào thư mục `www/`:

```bash
# 1. Xuất file catalogue.json chuẩn từ kho dữ liệu
python scripts/export_catalogue.py

# 2. Đóng gói HTML/CSS/JS tĩnh, nạp catalogue.json, thiết lập chế độ offline và quét bảo mật www/
python scripts/build_mobile_web.py

# 3. Đồng bộ assets vào các dự án native Android & iOS
npm run cap:sync
```

`npm run cap:sync` tương đương `python scripts/build_mobile_web.py && npx cap sync`.

Lưu ý: `www/` là artifact sinh ra từ bản build, **không được commit** vào kho lưu trữ.

---

## 4. Build & chạy Android

```bash
# Đồng bộ www/ vào dự án Android
npx cap sync android

# Biên dịch APK Debug để cài thử
cd android
./gradlew assembleDebug
# File xuất ra: android/app/build/outputs/apk/debug/app-debug.apk
cd ..
```

Cài APK vào thiết bị/máy ảo:

```bash
adb install android/app/build/outputs/apk/debug/app-debug.apk
```

Để mở dự án trong Android Studio (cấu hình ký số, build App Bundle `.aab` phát hành):

```bash
npx cap open android
```

Thông số native Android (xem `android/app/build.gradle`):

- `applicationId`: `com.easymeals.app`
- `minSdkVersion`: 23, `compileSdkVersion`: 35, `targetSdkVersion`: 35
- `versionCode`: 5, `versionName`: 1.4.0
- Quyền: `VIBRATE`; `usesCleartextTraffic="false"`, `allowBackup="false"`.

---

## 5. Build & chạy iOS

```bash
# Đồng bộ www/ vào dự án iOS
npx cap sync ios

# Mở Xcode workspace để chạy Simulator hoặc build lên iPhone thật
npx cap open ios
```

Yêu cầu: Xcode 15+, iOS deployment target 15.0+, CocoaPods đã cài (`pod install` trong `ios/App`).

---

## 6. Chạy kiểm thử

Kiểm thử toàn diện một lệnh (bao gồm build `www/` và quét bảo mật):

```bash
bash scripts/check.sh
```

Trong `scripts/check.sh`:

- **Bước 5**: `python scripts/build_mobile_web.py` — build `www/` và quét chuỗi cấm (`supabase.co`, `SUPABASE`, `eyJ`, `service_role`).
- **Bước 6**: `npx playwright test` — E2E hành trình người dùng trên Desktop, Mobile và static build `www/` offline.

Chạy chỉ kiểm thử unit JavaScript (IndexedDB storage, engine equivalence, atomic eat/undo):

```bash
npm run test:js
```

---

## 7. Lưu ý bảo mật & phát hành

- **Không có URL/khoá Supabase trong `www/`**: Script `build_mobile_web.py` tự quét và từ chối build nếu phát hiện `supabase.co`, `SUPABASE`, `eyJ` hoặc `service_role` trong `www/`.
- **Chưa ký AAB/IPA release**: việc ký App Bundle (`.aab`) cho Google Play và IPA cho App Store chưa được thực hiện; chủ dự án tự ký bằng keystore và chứng chỉ của mình.
- `www/` là artifact build, không commit vào kho lưu trữ.

---

> Xem thêm: `docs/deploy.md` §4 (Đóng Gói Ứng Dụng Di Động Offline), `INSTALL.md` §5, `README.md` §5.
