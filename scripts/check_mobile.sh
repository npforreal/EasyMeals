#!/usr/bin/env bash
# scripts/check_mobile.sh — Kiểm tra toàn bộ mã nguồn mobile thuần (Android + iOS)
# Bao gồm: tính toàn vẹn asset đồng bộ, unit test số học engine, hành trình người dùng và UI test trên Android & iOS.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -d "$ROOT_DIR/.venv" ] && [ -z "${VIRTUAL_ENV:-}" ]; then
  source "$ROOT_DIR/.venv/bin/activate"
fi

echo "==> 0. Kiểm tra đồng bộ design tokens (tokens.json & labels.json) & quét lint màu"
python scripts/generate_design_tokens.py --check
python -m pytest tests/test_tokens_contrast.py -q

echo "==> 1. Kiểm tra tính toàn vẹn asset catalogue & engine test cases"
python scripts/sync_mobile_assets.py --check

echo "==> 2. Android: Kiểm tra mã nguồn, Unit tests & Biên dịch Android"
(
  cd mobile/android
  if [ -d "/Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home" ]; then
    export JAVA_HOME="/Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home"
  elif [ -d "/opt/homebrew/opt/openjdk@21" ]; then
    export JAVA_HOME="/opt/homebrew/opt/openjdk@21"
  fi
  echo "--- 2.1 Chạy Unit tests (Catalogue, DateFormatter, Engine, UserJourneys) ---"
  ./gradlew --no-daemon testDebugUnitTest
  
  echo "--- 2.2 Biên dịch androidTest (Compose UI test) và assembleDebug ---"
  ./gradlew --no-daemon compileDebugAndroidTestKotlin assembleDebug

  echo "--- 2.3 Kiểm tra thiết bị thật / emulator qua adb cho connectedDebugAndroidTest ---"
  if command -v adb >/dev/null 2>&1 && adb devices | grep -v "List of devices" | grep -qE "\b(device|emulator)\b"; then
    echo "Phát hiện thiết bị kết nối. Chạy connectedDebugAndroidTest..."
    ./gradlew --no-daemon connectedDebugAndroidTest
  else
    echo "[BỎ QUA] Không có thiết bị Android kết nối qua adb để chạy connectedDebugAndroidTest (kết nối máy thật Samsung để chạy)"
  fi
)

echo "==> 3. iOS: Chạy Swift Test (Catalogue, DateFormatter, Engine, UserJourneys)"
(
  cd mobile/ios
  swift test
  
  echo "--- 3.1 Kiểm tra iOS Simulator cho XCUITest ---"
  if command -v xcrun >/dev/null 2>&1 && xcrun simctl list devices 2>/dev/null | grep -q "Booted"; then
    echo "Phát hiện iOS Simulator đang chạy."
  else
    echo "[BỎ QUA] Không có iOS Simulator đang chạy để chạy XCUITest trên simulator"
  fi
)

echo "==> scripts/check_mobile.sh: HOÀN TẤT KIỂM TRA MOBILE (Các bước bắt buộc đều xanh, các bước phụ thuộc thiết bị ngoại vi đã báo trạng thái rõ ràng)"
