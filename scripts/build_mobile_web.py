"""Script đóng gói ứng dụng web tĩnh cho Mobile App (Capacitor www directory).

Mục tiêu kiến trúc:
- Bản mobile chạy HOÀN TOÀN OFFLINE, không gọi Supabase, không cần backend.
- Toàn bộ danh mục được đóng gói sẵn trong www/data/catalogue.json.
- Thiết lập window.CATALOGUE_SOURCE = "bundled".
- Thu hẹp CSP về 'self' (connect-src 'self').
- Không đăng ký service worker gọi mạng trong bản mobile.
- Kiểm tra tự động nghiêm ngặt: quét www/ không chứa supabase.co, SUPABASE, eyJ, service_role.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from starlette.requests import Request

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.export_catalogue import DEFAULT_OUTPUT as DEFAULT_CATALOGUE_PATH  # noqa: E402
from scripts.export_catalogue import export_catalogue  # noqa: E402

TEMPLATES_DIR = ROOT / "app" / "templates"
STATIC_DIR = ROOT / "app" / "static"
WWW_DIR = ROOT / "www"

PAGES = [
    {
        "template": "index.html",
        "output": "index.html",
        "path": "/",
        "title": "EasyMeals — Tủ Lạnh & Nguyên Liệu",
    },
    {
        "template": "planner.html",
        "output": "planner.html",
        "path": "/planner",
        "title": "EasyMeals — Kế Hoạch Bữa Ăn",
    },
    {
        "template": "recipes.html",
        "output": "recipes.html",
        "path": "/recipes",
        "title": "EasyMeals — Sổ Tay Món Ăn",
    },
    {
        "template": "shopping.html",
        "output": "shopping.html",
        "path": "/shopping-list",
        "title": "EasyMeals — Danh Sách Đi Chợ",
    },
    {
        "template": "settings.html",
        "output": "settings.html",
        "path": "/settings",
        "title": "EasyMeals — Dữ Liệu & Cài Đặt",
    },
]

NAV_MAPPING = {
    "/": "index.html",
    "/planner": "planner.html",
    "/recipes": "recipes.html",
    "/shopping-list": "shopping.html",
    "/settings": "settings.html",
}

FORBIDDEN_PATTERNS = ["supabase.co", "SUPABASE", "eyJ", "service_role"]


def verify_www_security(www_dir: Path) -> None:
    print("-> Kiểm tra bảo mật: Quét bí mật và URL Supabase trong www/...")
    violations = []
    text_extensions = {".html", ".js", ".json", ".css", ".svg", ".txt"}

    for p in www_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in text_extensions:
            try:
                content = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            for pattern in FORBIDDEN_PATTERNS:
                if pattern in content:
                    violations.append((p.relative_to(www_dir), pattern))

    if violations:
        print(f"LỖI BẢO MẬT: Phát hiện chuỗi cấm trong {len(violations)} vị trí:", file=sys.stderr)
        for rel_path, pat in violations:
            print(f"  - [{pat}] trong tệp: {rel_path}", file=sys.stderr)
        raise RuntimeError("Gói www chứa bí mật hoặc URL Supabase cấm!")

    print("-> [BẢO MẬT ĐẠT CHUẨN]: Thư mục www/ 100% sạch bí mật và không chứa Supabase!")


def build_mobile_web() -> None:
    print(f"-> Bắt đầu đóng gói web tĩnh cho Mobile App vào: {WWW_DIR}")

    # 1. Đảm bảo file catalogue.json đã được xuất
    if not DEFAULT_CATALOGUE_PATH.exists():
        print("-> Chưa có data/catalogue.json, đang tiến hành xuất tự động...")
        export_catalogue(DEFAULT_CATALOGUE_PATH)

    # 2. Dọn dẹp thư mục www/ cũ
    if WWW_DIR.exists():
        shutil.rmtree(WWW_DIR)
    WWW_DIR.mkdir(parents=True, exist_ok=True)

    # 3. Sao chép static assets (loại bỏ sw.js trong mobile build)
    shutil.copytree(STATIC_DIR, WWW_DIR / "static")
    sw_file = WWW_DIR / "static" / "sw.js"
    if sw_file.exists():
        sw_file.unlink()
        print("   + Đã loại bỏ Service Worker (sw.js) khỏi bản mobile.")

    # 4. Sao chép danh mục đóng gói catalogue.json vào www/data/catalogue.json
    data_dir = WWW_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(DEFAULT_CATALOGUE_PATH, data_dir / "catalogue.json")
    print("   + Đã sao chép catalogue.json đóng gói vào www/data/catalogue.json")

    # 5. Tạo file env.js cấu hình chế độ đóng gói offline cho Mobile App
    env_content = """// Cấu hình môi trường cho EasyMeals Mobile App (100% Offline Bundled Mode)
window.CATALOGUE_SOURCE = "bundled";
"""
    (WWW_DIR / "env.js").write_text(env_content, encoding="utf-8")

    # 6. Thiết lập Jinja2 render templates với CSP nghiêm ngặt
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    csp_meta = (
        '  <meta http-equiv="Content-Security-Policy" '
        "content=\"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; font-src 'self'; connect-src 'self';\">\n"
    )

    for page in PAGES:
        scope: dict[str, Any] = {
            "type": "http",
            "method": "GET",
            "path": page["path"],
            "headers": [],
        }
        req = Request(scope)
        template = env.get_template(page["template"])
        rendered = template.render(request=req, title=page["title"])

        # Chuyển đổi các link điều hướng tuyệt đối sang tên file HTML tĩnh tương ứng
        for orig_url, html_file in NAV_MAPPING.items():
            rendered = rendered.replace(f'href="{orig_url}"', f'href="{html_file}"')

        # Nhúng env.js và CSP meta tag vào <head>
        if "</head>" in rendered:
            head_inject = f'{csp_meta}  <script src="env.js"></script>\n</head>'
            rendered = rendered.replace("</head>", head_inject)

        # Đổi đường dẫn tuyệt đối /static/ thành static/ để WebView tải file local ổn định
        rendered = rendered.replace('href="/static/', 'href="static/')
        rendered = rendered.replace('src="/static/', 'src="static/')
        rendered = rendered.replace('href="/manifest.json"', 'href="manifest.json"')

        out_path = WWW_DIR / page["output"]
        out_path.write_text(rendered, encoding="utf-8")
        print(f"   + Đã tạo trang: {page['output']}")

    # 7. Tạo file manifest.json cho www/
    manifest_content = """{
  "name": "EasyMeals — Bữa Ăn Dễ Dàng",
  "short_name": "EasyMeals",
  "description": "Lên lịch bữa ăn theo nguyên liệu sẵn có, chống lãng phí thực phẩm.",
  "start_url": "index.html",
  "display": "standalone",
  "background_color": "#f6f1e7",
  "theme_color": "#3f6b3a",
  "icons": [
    {
      "src": "static/icon.svg",
      "sizes": "192x192",
      "type": "image/svg+xml"
    }
  ]
}"""
    (WWW_DIR / "manifest.json").write_text(manifest_content, encoding="utf-8")

    # 8. Quét kiểm tra bảo mật
    verify_www_security(WWW_DIR)

    print(f"-> Hoàn tất! Đã xuất bản giao diện di động offline tại {WWW_DIR}")


if __name__ == "__main__":
    try:
        build_mobile_web()
    except Exception as e:
        print(f"Lỗi build mobile web: {e}", file=sys.stderr)
        sys.exit(1)
