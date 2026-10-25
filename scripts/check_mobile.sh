#!/usr/bin/env bash
# scripts/check_mobile.sh — Kiểm tra toàn bộ mã nguồn mobile thuần (Android + iOS)
# Bao gồm: tính toàn vẹn asset đồng bộ, unit test số học engine, hành trình người dùng và UI test trên Android & iOS.
#
# Mặc định chạy YÊN LẶNG (để tiết kiệm token/log): mỗi bước thành công chỉ in một dòng, bước lỗi
# in 80 dòng cuối của log. Dùng --verbose (hoặc CHECK_VERBOSE=1) để xem toàn bộ output.
set -euo pipefail

VERBOSE="${CHECK_VERBOSE:-0}"
for arg in "$@"; do
  [ "$arg" = "--verbose" ] && VERBOSE=1
done
LOG_FILE="$(mktemp -t easymeals-check-mobile.XXXXXX)"
trap 'rm -f "$LOG_FILE"' EXIT

run_step() {
  local label="$1"; shift
  if [ "$VERBOSE" = "1" ]; then
    echo "==> $label"
    "$@"
    return
  fi
  if "$@" >"$LOG_FILE" 2>&1; then
    echo "OK  $label"
  else
    echo "LOI $label" >&2
    tail -n 80 "$LOG_FILE" >&2
    exit 1
  fi
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -d "$ROOT_DIR/.venv" ] && [ -z "${VIRTUAL_ENV:-}" ]; then
  source "$ROOT_DIR/.venv/bin/activate"
fi

run_step "0. Kiểm tra đồng bộ design tokens & lint màu" bash -c "python scripts/generate_design_tokens.py --check && python -m pytest tests/test_tokens_contrast.py -q"

run_step "1. Kiểm tra tính toàn vẹn asset catalogue & engine test cases" python scripts/sync_mobile_assets.py --check

# 2. Android
(
  cd mobile/android
  if [ -d "/Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home" ]; then
    export JAVA_HOME="/Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home"
  elif [ -d "/opt/homebrew/opt/openjdk@21" ]; then
    export JAVA_HOME="/opt/homebrew/opt/openjdk@21"
  fi

  run_step "2.1 Android Unit tests (Catalogue, DateFormatter, Engine, UserJourneys)" ./gradlew --no-daemon testDebugUnitTest
  run_step "2.2 Biên dịch androidTest và assembleDebug" ./gradlew --no-daemon compileDebugAndroidTestKotlin assembleDebug

  if command -v adb >/dev/null 2>&1 && adb devices | grep -v "List of devices" | grep -qE "\b(device|emulator)\b"; then
    echo "Phát hiện thiết bị kết nối. Cài đặt và chạy kiểm tra UI nút Lưu bằng adb..."
    adb install -r app/build/outputs/apk/debug/app-debug.apk || true
    run_step "2.3 adb UI test nút Lưu" python3 "$ROOT_DIR/scripts/test_pantry_save_adb.py"
    run_step "2.4 connectedDebugAndroidTest" ./gradlew --no-daemon connectedDebugAndroidTest
  else
    echo "SKIP 2.3 Không có thiết bị Android qua adb để chạy connectedDebugAndroidTest"
  fi
)

# 3. iOS
(
  cd mobile/ios
  run_step "3.0 iOS Swift Test (Catalogue, DateFormatter, Engine, UserJourneys)" swift test

  if command -v xcrun >/dev/null 2>&1 && xcrun simctl list devices 2>/dev/null | grep -q "Booted"; then
    echo "Phát hiện iOS Simulator đang chạy."
  else
    echo "SKIP 3.1 Không có iOS Simulator đang chạy để chạy XCUITest"
  fi
)

echo "==> scripts/check_mobile.sh: TAT CA XANH (Bắt buộc OK, ngoại vi đã ghi nhận)"
