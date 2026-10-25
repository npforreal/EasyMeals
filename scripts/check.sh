#!/usr/bin/env bash
# scripts/check.sh — một lệnh chạy tat ca kiem tra EasyMeals.
# Dung tai giai đoạn D : ruff check + format check + pytest.
# Thoat ngay khi mot buoc loi; khong bat buoc co mang, khong can DB thuc.
#
# Mac dinh chay YEN LANG (de tiet kiem token/log): moi buoc thanh cong chi in mot dong, buoc loi
# in 80 dong cuoi cua log. Dung --verbose (hoac CHECK_VERBOSE=1) de xem toan bo output.
# Dung --fast hoac --skip-e2e (hoac CHECK_FAST=1) de bo qua Playwright E2E trong sandbox/vong lap dev.
set -euo pipefail

VERBOSE="${CHECK_VERBOSE:-0}"
FAST="${CHECK_FAST:-0}"
for arg in "$@"; do
  [ "$arg" = "--verbose" ] && VERBOSE=1
  { [ "$arg" = "--fast" ] || [ "$arg" = "--skip-e2e" ]; } && FAST=1
done
LOG_FILE="$(mktemp -t easymeals-check.XXXXXX)"
trap 'rm -f "$LOG_FILE"' EXIT

# run_step "nhan" lenh... : chay mot buoc, giu nguyen set -e (thoat khi loi).
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

if ! python -m ruff --version >/dev/null 2>&1; then
  echo "Loi: ruff chua cai dat. Chay: pip install ruff" >&2
  exit 1
fi

run_step "0. design tokens dong bo (tokens.json & labels.json)" python scripts/generate_design_tokens.py --check
run_step "1. ruff check (app, tests, scripts)" python -m ruff check app tests scripts
run_step "2. ruff format --check (app, tests, scripts)" python -m ruff format --check app tests scripts
run_step "3. pytest (unit, inventory, planner, api, security, catalogue schema)" python -m pytest tests/ -q
run_step "4. npm run test:js (IndexedDB storage, engine equivalence, atomic operations)" npm run test:js
run_step "5. build_mobile_web.py (build mobile assets, www/ sach)" python scripts/build_mobile_web.py
if [ "$FAST" = "1" ]; then
  echo "SKIP 6. playwright (bo qua vi chay voi --fast)"
  echo "==> scripts/check.sh: TAT CA XANH (--fast)"
else
  run_step "6. playwright (Desktop, Mobile, Offline www/ E2E)" npx playwright test --reporter="${PW_REPORTER:-dot}"
  echo "==> scripts/check.sh: TAT CA XANH"
fi
