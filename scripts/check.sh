#!/usr/bin/env bash
# scripts/check.sh — một lệnh chạy tat ca kiem tra EasyMeals.
# Dung tai giai đoạn D : ruff check + format check + pytest.
# Thoat ngay khi mot buoc loi; khong bat buoc co mang, khong can DB thuc.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -d "$ROOT_DIR/.venv" ] && [ -z "${VIRTUAL_ENV:-}" ]; then
  source "$ROOT_DIR/.venv/bin/activate"
fi

if ! python -m ruff --version >/dev/null 2>&1; then
  echo "Loi: ruff chua cai dat. Chay: pip install ruff" >&2
  exit 1
fi

echo "==> 0. Kiểm tra đồng bộ design tokens (tokens.json & labels.json)"
python scripts/generate_design_tokens.py --check

echo "==> 1. ruff check (app, tests, scripts)"
python -m ruff check app tests scripts

echo "==> 2. ruff format --check (app, tests, scripts)"
python -m ruff format --check app tests scripts

echo "==> 3. pytest (unit, inventory, planner, api, security, catalogue schema)"
python -m pytest tests/ -q

echo "==> 4. npm run test:js (IndexedDB storage, engine equivalence, & atomic operations)"
npm run test:js

echo "==> 5. build_mobile_web.py (Build mobile assets & verify www/ is clean)"
python scripts/build_mobile_web.py

echo "==> 6. npx playwright test (Desktop, Mobile, & Offline www/ E2E Journeys)"
npx playwright test

echo "==> scripts/check.sh: TAT CA XANH"
