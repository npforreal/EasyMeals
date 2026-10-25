#!/usr/bin/env bash
# scripts/check_mobile.sh — Kiểm tra toàn bộ mã nguồn mobile thuần (Android + iOS)
# Bao gồm: tính toàn vẹn asset đồng bộ, unit test số học engine trên Android & iOS.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -d "$ROOT_DIR/.venv" ] && [ -z "${VIRTUAL_ENV:-}" ]; then
  source "$ROOT_DIR/.venv/bin/activate"
fi

echo "==> 1. Kiểm tra tính toàn vẹn asset catalogue & engine test cases"
python scripts/sync_mobile_assets.py --check

echo "==> 2. Android: Chạy EngineEquivalenceTest trên máy ảo JVM (OpenJDK 21)"
(
  cd mobile/android
  if [ -d "/Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home" ]; then
    export JAVA_HOME="/Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home"
  elif [ -d "/opt/homebrew/opt/openjdk@21" ]; then
    export JAVA_HOME="/opt/homebrew/opt/openjdk@21"
  fi
  ./gradlew --no-daemon testDebugUnitTest
)

echo "==> 3. iOS: Chạy EngineTests với Swift Test (macOS/iOS ExactDecimal & FIFO Engine)"
(
  cd mobile/ios
  swift test
)

echo "==> scripts/check_mobile.sh: TẤT CẢ XANH (Android & iOS hoàn toàn vượt qua kiểm thử số học tương đương)"
