#!/usr/bin/env python3
"""scripts/test_pantry_save_adb.py

Kịch bản kiểm thử tự động trên thiết bị thật Samsung (hoặc emulator) qua adb:
1. Mở app EasyMeals debug.
2. Chuyển sang tab Tủ lạnh -> Mở bảng "Thêm đồ vào tủ".
3. Chọn "Gạo".
4. Dùng `uiautomator dump` để khẳng định node "Lưu một chạm":
   - Có mặt trong cây giao diện ngay lập tức mà KHÔNG CẦN VUỐT
   - `clickable="true"`
   - `bounds` nằm trọn trong kích thước màn hình
5. Nhập số lượng -> Nhấn nút "Lưu một chạm" -> Xác nhận "Gạo" xuất hiện trong tủ.
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

PACKAGE_NAME = "com.easymeals.app.debug"
ACTIVITY_NAME = "com.easymeals.app.MainActivity"


def run_adb(cmd: list[str]) -> str:
    res = subprocess.run(["adb", *cmd], capture_output=True, text=True, check=False)
    return res.stdout.strip()


def get_screen_size() -> tuple[int, int]:
    out = run_adb(["shell", "wm", "size"])
    m = re.search(r"(\d+)x(\d+)", out)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 1080, 2340


def dump_ui_hierarchy() -> ET.Element:
    run_adb(["shell", "uiautomator", "dump", "/data/local/tmp/dump.xml"])
    xml_str = run_adb(["shell", "cat", "/data/local/tmp/dump.xml"])
    if not xml_str.strip().startswith("<?xml"):
        # Thử lại nếu dump chậm
        time.sleep(1)
        run_adb(["shell", "uiautomator", "dump", "/data/local/tmp/dump.xml"])
        xml_str = run_adb(["shell", "cat", "/data/local/tmp/dump.xml"])
    return ET.fromstring(xml_str)


def parse_bounds(bounds_str: str) -> tuple[int, int, int, int]:
    # e.g. "[64,1950][1016,2094]"
    m = re.findall(r"\[(\d+),(\d+)\]", bounds_str)
    if len(m) == 2:
        return int(m[0][0]), int(m[0][1]), int(m[1][0]), int(m[1][1])
    return 0, 0, 0, 0


def main():
    devices = run_adb(["devices"]).splitlines()
    active_devices = [
        line.split()[0]
        for line in devices[1:]
        if line.strip() and not line.startswith("*") and "\tdevice" in line
    ]
    if not active_devices:
        print("[ADB TEST] Không tìm thấy thiết bị Android kết nối. Bỏ qua.")
        return 0

    device_serial = active_devices[0]
    print(f"==> [ADB TEST] Thiết bị đang kết nối: {device_serial}")
    width, height = get_screen_size()
    print(f"==> Kích thước màn hình: {width}x{height}")

    # Khởi động app
    print("==> Khởi động ứng dụng EasyMeals...")
    run_adb(["shell", "am", "start", "-n", f"{PACKAGE_NAME}/{ACTIVITY_NAME}"])
    time.sleep(2)

    root = dump_ui_hierarchy()

    # Tìm và click tab "Tủ lạnh"
    tab_pantry = None
    for node in root.iter("node"):
        if node.get("text") == "Tủ lạnh" or node.get("content-desc") == "Tủ lạnh":
            tab_pantry = node
            break

    if tab_pantry is not None:
        x1, y1, x2, y2 = parse_bounds(tab_pantry.get("bounds", ""))
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        print(f"--> Chuyển sang tab Tủ lạnh tại ({cx}, {cy})...")
        run_adb(["shell", "input", "tap", str(cx), str(cy)])
        time.sleep(1.5)

    # Tìm và click nút FAB "Thêm đồ vào tủ"
    root = dump_ui_hierarchy()
    fab_add = None
    for node in root.iter("node"):
        if "Thêm đồ vào tủ" in (node.get("content-desc") or ""):
            fab_add = node
            break

    if fab_add is not None:
        x1, y1, x2, y2 = parse_bounds(fab_add.get("bounds", ""))
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        print(f"--> Bấm nút Thêm đồ vào tủ tại ({cx}, {cy})...")
        run_adb(["shell", "input", "tap", str(cx), str(cy)])
        time.sleep(1.5)

    # Chọn Gạo
    root = dump_ui_hierarchy()
    gao_node = None
    for node in root.iter("node"):
        if node.get("text") == "Gạo":
            gao_node = node
            break

    if gao_node is not None:
        x1, y1, x2, y2 = parse_bounds(gao_node.get("bounds", ""))
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        print(f"--> Chọn nguyên liệu 'Gạo' tại ({cx}, {cy})...")
        run_adb(["shell", "input", "tap", str(cx), str(cy)])
        time.sleep(1.5)

    # DUMP kiểm tra nút "Lưu một chạm" NGAY LẬP TỨC (KHÔNG VUỐT)
    root = dump_ui_hierarchy()
    save_btn = None
    for node in root.iter("node"):
        if "Lưu một chạm" in (node.get("text") or "") or "Lưu một chạm" in (
            node.get("content-desc") or ""
        ):
            save_btn = node
            break

    if save_btn is None:
        print(
            "❌ THẤT BẠI: Nút 'Lưu một chạm' KHÔNG xuất hiện trong cây giao diện ngay khi mở bảng!",
            file=sys.stderr,
        )
        return 1

    bounds_str = save_btn.get("bounds", "")
    x1, y1, x2, y2 = parse_bounds(bounds_str)
    clickable = save_btn.get("clickable") == "true"

    if not clickable:
        # Nếu node là Text bên trong Button, duyệt lên cha để lấy Button clickable
        parent_map = {c: p for p in root.iter() for c in p}
        curr = save_btn
        while curr in parent_map:
            curr = parent_map[curr]
            if curr.get("clickable") == "true":
                clickable = True
                save_btn = curr
                bounds_str = curr.get("bounds", bounds_str)
                x1, y1, x2, y2 = parse_bounds(bounds_str)
                break

    print(f"--> Tìm thấy nút 'Lưu một chạm': bounds={bounds_str}, clickable={clickable}")

    # Khẳng định nút nằm trọn trong màn hình
    if x1 < 0 or y1 < 0 or x2 > width or y2 > height:
        print(
            f"❌ THẤT BẠI: Nút 'Lưu một chạm' bị tràn ngoài màn hình: "
            f"bounds={bounds_str}, screen={width}x{height}",
            file=sys.stderr,
        )
        return 1

    if not clickable:
        print(
            "❌ THẤT BẠI: Nút 'Lưu một chạm' không có thuộc tính clickable=true!",
            file=sys.stderr,
        )
        return 1

    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    print(f"--> Bấm 'Lưu một chạm' tại ({cx}, {cy})...")
    run_adb(["shell", "input", "tap", str(cx), str(cy)])
    time.sleep(2)

    # Xác nhận Gạo đã có trong danh sách Tủ lạnh
    root = dump_ui_hierarchy()
    found_gao = False
    for node in root.iter("node"):
        if node.get("text") == "Gạo":
            found_gao = True
            break

    if not found_gao:
        print("❌ THẤT BẠI: Không thấy 'Gạo' trong danh sách tủ lạnh sau khi lưu!", file=sys.stderr)
        return 1

    print("✅ THÀNH CÔNG: Hành trình thêm gạo và nút Lưu hiển thị chuẩn xác trên máy thật!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
