"""Kiểm tra cấu hình Supabase mà KHÔNG in khoá hay URL.

Dùng thay cho việc mở/`cat` tệp `.env`: script đọc cấu hình bằng `app.supabase_config.load_env()`
và chỉ in tên biến đang dùng, vai trò của khoá (anon/service_role), số dòng danh mục và cảnh báo.

    python scripts/check_supabase_config.py            # có thử đọc danh mục qua mạng (chỉ đọc)
    python scripts/check_supabase_config.py --offline  # chỉ xem cấu hình, không gọi mạng

Thoát mã 0 khi cấu hình đủ (và đọc được danh mục nếu không dùng --offline), 1 nếu thiếu/lỗi,
2 nếu phát hiện khoá service_role (không được dùng ở máy chạy app/CI).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.supabase_config import check_supabase, key_role, load_env, resolve_env  # noqa: E402


def run(env: Mapping[str, str], offline: bool = False, client_factory=None) -> tuple[dict, int]:
    """Trả về (báo cáo không chứa bí mật, mã thoát)."""
    if offline:
        resolved = resolve_env(env)
        if resolved is None:
            report = {"configured": False, "ok": False, "problem": "Thiếu SUPABASE_URL hoặc khoá."}
            return report, 1
        role = key_role(resolved.key)
        report = {"configured": True, "key_var": resolved.key_var, "key_role": role, "ok": True}
    else:
        report = check_supabase(env, client_factory)
        role = report.get("key_role")
    if role == "service_role":
        report["ok"] = False
        report["problem"] = "Đang dùng khoá service_role; chỉ dùng khoá anon cho app và kiểm tra."
        return report, 2
    return report, 0 if report.get("ok") else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--offline", action="store_true", help="không gọi mạng")
    args = parser.parse_args(argv)
    report, code = run(load_env(), offline=args.offline)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
