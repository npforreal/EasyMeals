# Ma trận parity Web ↔ Android ↔ iOS

> G1 của Giai đoạn G (Vòng 13). Cập nhật: 2026-10-27.
>
> Mục đích: một chỗ duy nhất trả lời "chức năng này có ở đâu, được chứng minh bằng gì,
> và khác biệt nào là cố ý". Cột **Bằng chứng** chỉ ghi test/lệnh đã thực sự chạy trong
> repo; phần chưa chạy được ghi rõ ở cuối tài liệu.

## 1. Cách đọc bảng

- **Có** = có UI và logic trên nền tảng đó.
- **Khác** = có nhưng hành vi/giao diện khác có chủ ý (giải thích ở cột cuối hoặc mục 3).
- **Không** = không triển khai (không phải lỗi parity nếu đã ghi ở mục 3).
- Đường dẫn test tính từ gốc repo. Lệnh chạy đầy đủ ở mục 4.

## 2. Ma trận chức năng

| # | Nhóm | Chức năng | Web | Android | iOS | Bằng chứng | Khác biệt cố ý |
|---|---|---|---|---|---|---|---|
| 1 | Tủ lạnh | Thêm lô: gợi ý nguyên liệu chuẩn, đơn vị, hạn mặc định theo nhóm | Có | Có | Có | `tests/e2e/user_journey.spec.js`; `tests/js/storage.test.js` (A4); `PantrySaveButtonTest.kt` (instrumented, chạy trên SM-A176B 2026-10-27); `mobile/ios/EasyMealsUITests/NarrowLayoutUITests.swift` | UI: modal web / BottomSheet Compose / Sheet SwiftUI |
| 2 | Tủ lạnh | Sửa hạn +3 ngày, xoá lô, trạng thái tủ trống | Có | Có | Có | `tests/e2e/g2_journeys.spec.js`; `UserJourneysComposeTest.kt`; `UserJourneysTests.swift` | — |
| 3 | Tủ lạnh | Cảnh báo hạn dùng theo lô (hết hạn/sắp hết hạn, chỉ lô còn lượng) | Có | Có | Có | `tests/e2e/expiry_warning.spec.js`; `tests/js/engine_logic.test.js`; fixture `tests/fixtures/engine_logic_cases.json`; `EngineLogicTests.swift` | — |
| 4 | Thực đơn | Lập 1–7 ngày (mặc định 3), chip chọn ngày, nhớ lựa chọn | Có | Có | Có | `tests/e2e/planner_days.spec.js`; `PlanDaysSelectorTest.kt` (280–384 dp, chạy trên SM-A176B); `PlanDaysSelectorTest.kt` + `NarrowLayoutUITests.swift` | — |
| 5 | Thực đơn | Tạo lại an toàn: hỏi Giữ/Thay, bữa đã ăn luôn giữ, chống bấm lặp | Có | Có | Có | `tests/e2e/plan_regenerate.spec.js`; `PlanConflictDialogTest.kt` (instrumented); `UserJourneysLogicTest.kt`; `UserJourneysTests.swift` | — |
| 6 | Thực đơn | Sửa bữa: sinh lại một bữa, đổi/bỏ/thêm món thủ công, cảnh báo nguyên liệu cần tránh | Có | Có | Có | `tests/e2e/plan_edit_and_budget.spec.js`; `tests/e2e/avoided_ingredients.spec.js`; `RecipePickerDialogTest.kt` (5 test, **chưa chạy trên máy thật**); `EasyMealsUITests` 4/4 trên iPhone 17e (2026-10-27) | Android mới có UI chọn món từ 2026-10-27; xác nhận trên thiết bị còn mở (xem mục 5) |
| 7 | Thực đơn | Đồ dư dùng lại 2 ngày (cấu hình 1–3), không sinh phần dư ảo | Có | Có | Có | `tests/js/engine_logic.test.js`; fixture 4 engine; `EngineLogicTest.kt`; `EngineLogicTests.swift` | — |
| 8 | Nấu/ăn | Đánh dấu đã ăn: FIFO theo hạn, quy đổi gạo→cơm, trừ một phần, idempotent | Có | Có | Có | `tests/e2e/core_journey.spec.js`; `tests/js/storage.test.js`; `EngineEquivalenceTest.kt`; `EngineTests.swift` | — |
| 9 | Nấu/ăn | Hoàn tác khôi phục đúng lô đã trừ, không đè chỉnh sửa kho sau đó | Có | Có | Có | `tests/e2e/core_journey.spec.js`; `tests/js/storage.test.js`; `UserJourneysComposeTest.kt`; `UserJourneysTests.swift` | — |
| 10 | Nấu | Chế độ nấu toàn màn hình, checklist, tăng/giảm khẩu phần, quy đổi định lượng | Có | Có | Có | `tests/e2e/user_journey.spec.js`; `tests/js/engine.test.js`; `EngineLogicTest.kt`; `EngineLogicTests.swift` | — |
| 11 | Đi chợ | Sinh danh sách từ phần thiếu, gộp món/đơn vị, nhóm quầy, mục tự thêm được giữ | Có | Có | Có | `tests/e2e/plan_edit_and_budget.spec.js`; `tests/js/storage.test.js` (A3); `ShoppingDefaultsTest.kt`; `ShoppingDefaultsTests.swift` | — |
| 12 | Đi chợ | Giá người dùng nhập, dự toán/đã chi, không gửi giá lên API | Có | Có | Có | `tests/js/storage.test.js` (F1); `tests/e2e/plan_edit_and_budget.spec.js`; `ShoppingScreen.kt`; `ShoppingView.swift` | — |
| 13 | Đi chợ | Mua vào tủ một giao dịch: lượng thực mua, hạn theo nhóm, chống trùng | Có | Có | Có | `tests/e2e/shopping_purchase.spec.js`; `tests/js/storage.test.js` (A4); `PurchaseConfirmDialogTest.kt`; `UserJourneysTests.swift` | — |
| 14 | Dữ liệu | Sao lưu/phục hồi JSON schema 1–3, gồm tủ, thực đơn, biến động, đi chợ, cài đặt | Có | Có | Có | `tests/e2e/g2_journeys.spec.js`; `tests/e2e/shopping_backup.spec.js`; `tests/js/migration.test.js`; `tests/js/storage.test.js`; `BackupMigrationTest.kt`; `BackupMigrationTests.swift` | Cùng một định dạng file; đường dẫn lưu file do hệ điều hành quyết định |
| 15 | Dữ liệu | Nâng cấp IndexedDB v1→v3 không mất dữ liệu; danh sách đi chợ cũ trong localStorage được chuyển | Có | Có | Có | `tests/js/migration.test.js`; `tests/js/history.test.js`; `BackupMigrationTest.kt`; `BackupMigrationTests.swift` | Native lưu file JSON thay vì IndexedDB |
| 16 | Công thức | Tìm không dấu, lọc danh mục/nguyên liệu, lọc thời gian & độ khó, mẹo bảo quản | Có | Có | Có | `tests/e2e/recipe_metadata.spec.js`; `tests/js/recipe_metadata.test.js`; `RecipeMetadataTest.kt`; `RecipeMetadataTests.swift` | 27/133 món thiếu metadata → ẩn khi lọc, có ghi chú |
| 17 | Công thức | Dị ứng/chế độ ăn, danh sách nguyên liệu cần tránh, cảnh báo dữ liệu chưa xác minh | Có | Có | Có | `tests/e2e/avoided_ingredients.spec.js`; `tests/js/recipe_preferences.test.js`; `RecipePreferences` tests (Kotlin/Swift); fixture engine | Không thay thế việc đọc nhãn thực phẩm |
| 18 | Lịch sử | Tổng hợp 30 ngày tại máy: số bữa, biến động, đồ dư, lô quá hạn, chi tiêu | Có | Có | Có | `tests/js/history.test.js`; `HistorySummaryTest.kt`; `HistorySummary` tests (Swift) | Web tính khi mở Cài đặt; native tính từ file trạng thái |
| 19 | Nhắc việc | Nhắc hạn dùng/bữa hôm nay | Không | Có | Có | `ReminderPlannerTest.kt`; `ReminderPlannerTests.swift`; `tests/test_hardening_l.py::test_l4_android_manifest_minimal_permissions` | **Cố ý**: web không có thông báo nền; mobile chỉ xin `POST_NOTIFICATIONS`/quyền thông báo cục bộ, không `INTERNET` |
| 20 | Giao diện | 5 bảng màu × Sáng/Tối/Hệ thống | Có | Có | Có | `tests/test_tokens_contrast.py`; `tests/e2e/user_journey.spec.js`; `GeneratedTokens.kt`; `GeneratedTokens.swift` | Token sinh từ `design-tokens/tokens.json` |
| 21 | Offline | Dùng đầy đủ khi không có mạng | Có (PWA + IndexedDB) | Có (đóng gói, không quyền mạng) | Có (đóng gói, không quyền mạng) | `tests/e2e/offline_conversion.spec.js`; `tests/e2e/user_journey.spec.js` (route abort); `tests/test_hardening_l.py`; Android manifest test | Web có thể gọi API khi online; native luôn offline |
| 22 | Accessibility | Tên truy cập cho điều khiển, focus/Escape trong hộp thoại, vùng chạm ≥44 px | Có | Có | Có | `tests/e2e/accessibility.spec.js` (6 test); nhãn `contentDescription`/`accessibilityLabel` trong `PantryScreen.kt`, `ShoppingScreen.kt`, `PantryView.swift`, `ShoppingView.swift` | Kiểm tra native mới ở mức mã + build, chưa có thiết bị (mục 5) |
| 23 | Định dạng | Ngày `dd/MM/yyyy`, "Hôm nay"/"Ngày mai", số lượng thập phân, nhãn tiếng Việt | Có | Có | Có | `tests/test_date_formatter.py`; `tests/js/formatters.test.js`; `DateFormatterTest.kt`; `DateFormatterTests.swift` | — |

## 3. Khác biệt có chủ ý (tóm tắt)

Chi tiết kỹ thuật nằm ở `docs/architecture.md` §6.4. Các khác biệt không phải lỗi parity:

1. **Lưu trữ**: web dùng IndexedDB; Android/iOS dùng file JSON trong sandbox ứng dụng. Cùng một schema backup và cùng quy tắc nhập file.
2. **Nhắc việc**: chỉ mobile. Web không có thông báo nền đáng tin cậy và giữ nguyên nguyên tắc không xin quyền.
3. **Mạng**: native không có quyền `INTERNET`; web online gọi API stateless, offline dùng `engine.js`.
4. **Điều hướng**: BackHandler Android, NavigationStack iOS, History API + modal web.
5. **Cài đặt giao diện**: localStorage (web) / SharedPreferences (Android) / `@AppStorage` (iOS) — không nằm trong backup dữ liệu cá nhân.
6. **Thành phần UI**: modal web / BottomSheet Compose / Sheet SwiftUI cho cùng một luồng.

## 4. Lệnh tái tạo bằng chứng

```bash
# Web + API + JS
bash scripts/check.sh

# Mobile (unit + build; thêm connectedDebugAndroidTest nếu có máy)
bash scripts/check_mobile.sh

# Riêng ma trận/accessibility/hành trình G
npx playwright test tests/e2e/accessibility.spec.js tests/e2e/g2_journeys.spec.js
node --test tests/js/migration.test.js
```

## 5. Phần chưa chứng minh được (tính đến 2026-10-27)

- **Ảnh so sánh trên thiết bị thật**: `adb devices -l` trống sau khi `adb kill-server && adb start-server` (thử lúc bắt đầu Giai đoạn G). Không có ảnh chụp màn hình so sánh Web ↔ Android ↔ iOS; **không đánh dấu hoàn tất** phần ảnh của G1.
  - Ảnh web có thể chụp lại bằng Playwright; ảnh Android cần máy thật/emulator; ảnh iOS cần Simulator đang chạy.
- **Compose UI chọn món thủ công (D2b)**: 5 test mới đã biên dịch nhưng chưa chạy `connectedDebugAndroidTest` trên máy thật.
- **VoiceOver/TalkBack thủ công**: chưa bật trình đọc màn hình để kiểm tra thứ tự đọc và phát âm tiếng Việt.
- **Bàn phím ảo trên iOS/Android thật**: đã có test Compose/XCUITest trước đó nhưng chưa kiểm tra lại sau thay đổi nhãn accessibility.
