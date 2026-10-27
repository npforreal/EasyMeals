# Quy trình và chính sách phiên bản

## 1. Đánh số phiên bản (SemVer `MAJOR.MINOR.PATCH`)

- **MAJOR**: đổi kiến trúc hoặc phá tương thích (ví dụ bỏ Capacitor, thay bằng app native; đổi schema backup không nhập ngược được).
- **MINOR**: thêm tính năng tương thích ngược (nhắc việc, lọc công thức...).
- **PATCH**: sửa lỗi, không đổi hành vi công khai.
- Một số phiên bản duy nhất cho cả Web, API, Android, iOS. Tag Git dạng `vX.Y.Z`, tên release `EasyMeals vX.Y.Z`.
- `schema_version` của backup tăng riêng, độc lập với phiên bản app (xem `docs/architecture.md` mục sao lưu). Ứng dụng chỉ từ chối tệp có `schema_version` mới hơn mình.
- `CATALOGUE_VERSION` (`app/storage/repository.py`) là phiên bản dữ liệu danh mục, tăng khi đổi dữ liệu; không phải phiên bản app.
- `CACHE_NAME` trong `app/static/sw.js` tăng khi đổi tài nguyên web được cache (PWA) để client bỏ cache cũ.
- Hỗ trợ bảo mật: chỉ phiên bản mới nhất trên `main` (xem `SECURITY.md`); khi nâng MAJOR hãy cập nhật hàng `< X.0.0` trong bảng đó.

## 2. Nơi phải đổi khi nâng phiên bản

`python scripts/check_version.py` (chạy trong `scripts/check.sh`) kiểm tra các nơi sau luôn trùng nhau:

| Nơi | Trường |
|---|---|
| `package.json`, `package-lock.json` | `version` |
| `pyproject.toml` | `version` |
| `app/main.py` | `version=` của FastAPI |
| `app/static/js/storage.js` | `APP_VERSION` (ghi vào backup) |
| `mobile/android/app/build.gradle.kts` | `versionName`; **tự tăng `versionCode` mỗi lần phát hành** |
| `mobile/android/.../data/backup/BackupManager.kt` | `APP_VERSION` |
| `mobile/ios/project.yml` | `MARKETING_VERSION`; tăng `CURRENT_PROJECT_VERSION` |
| `mobile/ios/EasyMeals/Data/Backup/BackupManager.swift` | `appVersion` |

Không được kiểm tự động (đổi tay khi cần): hàng `< X.0.0` trong `SECURITY.md`, ví dụ trong `.github/ISSUE_TEMPLATE/bug_report.md`, `SettingsScreen.kt` (placeholder), fixture test backup.

## 3. Các bước phát hành

1. Cập nhật `PLAN.md`/`PROGRESS.md`, chạy `python scripts/archive_logs.py` nếu vừa đóng một vòng.
2. Nâng phiên bản ở các nơi trên, chạy `python scripts/check_version.py`.
3. Kiểm tra: `bash scripts/check.sh` (đầy đủ) và `bash scripts/check_mobile.sh` (có máy Android thật nếu được).
4. Build artifact vào `release-artifacts/vX.Y.Z/` (thư mục này bị `.gitignore`):
   - Android: `cd mobile/android && ./gradlew clean assembleDebug` → `app/build/outputs/apk/debug/app-debug.apk`.
   - iOS: `cd mobile/ios && xcodegen generate`, rồi `xcodebuild -scheme EasyMeals -configuration Release -sdk iphoneos CODE_SIGNING_ALLOWED=NO build` (gói `Payload/EasyMeals.app` thành `.ipa` chưa ký) và `-sdk iphonesimulator` (nén `.app` thành zip).
   - APK debug và IPA chưa ký chỉ để thử nghiệm. Chưa có artifact ký cho cửa hàng ứng dụng (chủ dự án tự ký).
5. Commit `release: vX.Y.Z — ...`, tag, rồi `gh release create vX.Y.Z --notes-file ...` kèm artifact; ghi rõ phần chưa kiểm chứng.
6. Nếu đổi schema/dữ liệu danh mục: chạy migration SQL rồi `bash scripts/update_supabase.sh` (xem `docs/deploy.md`).
7. Dọn thư mục build (`mobile/ios/.build`, `mobile/android/{build,app/build,.gradle}`, `www/`, cache) khi không còn dùng.

## 4. Quy ước push và phát hành

Mặc định agent chỉ commit cục bộ (xem `AGENTS.md`). Chỉ push, tạo tag và release khi chủ dự án yêu cầu rõ ràng cho đợt phát hành đó. Không đưa khoá `service_role` hay `.env` vào commit, release hoặc log.
