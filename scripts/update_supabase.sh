#!/usr/bin/env bash
# Cập nhật danh mục dùng chung (catalogue) lên Supabase. DO CHỦ DỰ ÁN TỰ CHẠY — agent/CI không chạy.
#
#   bash scripts/update_supabase.sh            # DRY-RUN: kiểm tra + thống kê, không ghi DB
#   bash scripts/update_supabase.sh --apply    # ghi lên Supabase (hỏi service_role key, không hiển thị/không lưu)
#   bash scripts/update_supabase.sh --apply --clean   # xoá sạch danh mục cũ rồi nạp lại
#   bash scripts/update_supabase.sh --migrations      # liệt kê migration SQL cần chạy trong SQL Editor
#
# Thứ tự khi phát hành bản mới có đổi schema:
#   1) --migrations  -> chạy các file SQL mới trong Supabase SQL Editor (hoặc `supabase db push`)
#   2) --apply       -> nạp lại dữ liệu danh mục
#   3) script tự chạy verify_rls.py bằng anon key để chắc client chỉ đọc được
#
# Yêu cầu: .env có SUPABASE_URL và SUPABASE_ANON_KEY (KHÔNG chứa service_role).
# service_role key chỉ nhập khi được hỏi, sống trong biến môi trường của tiến trình con.
set -euo pipefail
cd "$(dirname "$0")/.."

APPLY=0; CLEAN=0; MIGRATIONS=0
for a in "$@"; do
  case "$a" in
    --apply) APPLY=1 ;;
    --clean) CLEAN=1 ;;
    --migrations) MIGRATIONS=1 ;;
    -h|--help) sed -n 2,16p "$0"; exit 0 ;;
    *) echo "Tuỳ chọn không hợp lệ: $a" >&2; exit 2 ;;
  esac
done

# Dùng .venv của dự án nếu có (giống scripts/check.sh)
if [ -d ".venv" ] && [ -z "${VIRTUAL_ENV:-}" ]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi
PY="${PYTHON:-python}"
command -v "$PY" >/dev/null 2>&1 || PY=python3

if [ "$MIGRATIONS" = 1 ]; then
  echo "Migration SQL (chạy theo thứ tự tên file trong Supabase SQL Editor; dự án mới dùng full_schema.sql):"
  ls -1 supabase/migrations/*.sql | sed 's/^/  /'
  echo "  (dự án mới: supabase/full_schema.sql)"
  exit 0
fi

echo "==> 1/4 Kiểm tra cấu hình (không in khoá)"
"$PY" scripts/check_supabase_config.py --offline || echo "(cảnh báo: chưa đủ cấu hình trong .env; bước --apply sẽ hỏi URL và service_role key)"

echo "==> 2/4 Xuất và kiểm tra tính toàn vẹn data/catalogue.json (fixture, không ghi DB)"
"$PY" scripts/export_catalogue.py --fixture-only --output /tmp/easymeals_catalogue_check.json >/dev/null
rm -f /tmp/easymeals_catalogue_check.json

if [ "$APPLY" = 0 ]; then
  echo "==> 3/4 DRY-RUN upload (không ghi DB)"
  "$PY" scripts/upload_catalogue_to_supabase.py
  echo "Dry-run xong. Thêm --apply để ghi thật."
  exit 0
fi

echo "==> 3/4 Ghi lên Supabase"
# Nếu đã đặt sẵn 2 biến trước lệnh thì dùng luôn, không hỏi lại:
#   SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... bash scripts/update_supabase.sh --apply
# (hoặc chạy thẳng: SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... python scripts/upload_catalogue_to_supabase.py)
if [ -n "${SUPABASE_URL:-}" ] && [ -n "${SUPABASE_SERVICE_ROLE_KEY:-}" ]; then
  if [ "$CLEAN" = 1 ]; then
    "$PY" scripts/upload_catalogue_to_supabase.py --apply --clean
  else
    "$PY" scripts/upload_catalogue_to_supabase.py --apply
  fi
  echo "==> 4/4 Kiểm chứng RLS bằng anon key (cần SUPABASE_ANON_KEY trong .env)"
  env -u SUPABASE_SERVICE_ROLE_KEY "$PY" scripts/verify_rls.py
  exit 0
fi
if [ -z "${SUPABASE_URL:-}" ]; then
  read -r -p "SUPABASE_URL (https://<id>.supabase.co) — Enter để dùng .env: " SUPABASE_URL_IN || true
  [ -n "${SUPABASE_URL_IN:-}" ] && export SUPABASE_URL="$SUPABASE_URL_IN"
fi
read -r -s -p "SUPABASE_SERVICE_ROLE_KEY (ẩn, không lưu): " SRK; echo
[ -n "$SRK" ] || { echo "Thiếu service_role key." >&2; exit 1; }
read -r -p "Ghi lên Supabase thật${CLEAN:+ (XOÁ SẠCH danh mục cũ trước)}? gõ 'yes': " OK
[ "$OK" = "yes" ] || { echo "Đã huỷ."; exit 1; }
if [ "$CLEAN" = 1 ]; then
  SUPABASE_SERVICE_ROLE_KEY="$SRK" "$PY" scripts/upload_catalogue_to_supabase.py --apply --clean
else
  SUPABASE_SERVICE_ROLE_KEY="$SRK" "$PY" scripts/upload_catalogue_to_supabase.py --apply
fi
unset SRK

echo "==> 4/4 Kiểm chứng RLS bằng anon key (INSERT/UPDATE/DELETE phải bị từ chối)"
env -u SUPABASE_SERVICE_ROLE_KEY "$PY" scripts/verify_rls.py
echo "Xong. Nhớ: không để service_role key trong .env hay Vercel."
