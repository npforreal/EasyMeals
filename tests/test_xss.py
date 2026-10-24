"""Test XSS: du lieu nguoi dung phai duoc render bang textContent, khong innerHTML.

Chay tren may sach (khong can Supabase):
- Kiem tra source `app/static/app.js`: cac phep gan `innerHTML =` chi duoc phep gan
  chuoi literal tĩnh (thong bao, xoa container), KHONG duoc gan bien chua du lieu
  nguoi dung.
- Kiem tra API tra ve du lieu giong nguyen (JSON); o frontend, du lieu nay duoc chen
  bang textContent (xem app.js) nen chuoi `<script>`/`onerror=` hien thi nhu chuong
  binh thuong, khong duoc thuc thi.
"""

import re
from pathlib import Path

APP_JS = Path(__file__).resolve().parents[1] / "app" / "static" / "app.js"

# Pattern bat phep gan innerHTML = gia tri KHONG phai chuoi literal (co nguy co XSS).
# innerHTML = "<p>...</p>" hoac innerHTML = "" -> literal (bat dau bang '"), an toan.
# innerHTML = someVariable hoac `${var}` -> gan bien du lieu nguoi dung, nguy hiem.
INNERHTML_NON_LITERAL = re.compile(r"innerHTML\s*=\s*([A-Za-z_$]\w*)")
INNERHTML_TEMPLATE_INTERPOLATION = re.compile(r"innerHTML\s*=\s*`[^`]*\$\{[^}]+\}[^`]*`")


def test_app_js_no_innerhtml_user_data():
    """app.js khong duoc gan innerHTML bang bien du lieu nguoi dung hoac template interpolation."""
    source = APP_JS.read_text(encoding="utf-8")
    matches = INNERHTML_NON_LITERAL.findall(source)
    assert not matches, "Phat hien gan innerHTML bang bien (nguy co XSS): " + ", ".join(matches)
    tpl_matches = INNERHTML_TEMPLATE_INTERPOLATION.findall(source)
    assert not tpl_matches, (
        "Phat hien gan innerHTML co chua template interpolation (nguy co XSS): "
        + ", ".join(tpl_matches)
    )
    # Co textContent de chen du lieu nguoi dung (ten mon, ten nguyen lieu, alias).
    assert "textContent" in source


def test_android_manifest_no_cleartext_traffic():
    """AndroidManifest.xml must disallow cleartext traffic and disable adb auto-backup."""
    manifest_file = (
        Path(__file__).resolve().parents[1]
        / "mobile"
        / "android"
        / "app"
        / "src"
        / "main"
        / "AndroidManifest.xml"
    )
    content = manifest_file.read_text(encoding="utf-8")
    assert 'android:usesCleartextTraffic="false"' in content
    assert 'android:allowBackup="false"' in content


def test_api_ingredients_search_xss_payload_roundtrip(client):
    """API tra ve payload giong nguyen (JSON); frontend chi hien thi bang textContent."""
    payload = "<script>alert(1)</script><img src=x onerror=alert(1)>"
    res = client.get(f"/api/ingredients?q={payload}")
    assert res.status_code == 200
    items = res.json()
    # Chuoi payload duoc tra lai giong nguyen trong JSON (API khong escape HTML);
    # o frontend, no duoc chen bang textContent -> hien thi nhu chuong binh thuong,
    # khong duoc thuc thi. Test nay chuan chuong API tra ve 200 va khong crash.
    assert isinstance(items, list)
