"""Màu thương hiệu dùng ở chỗ cần chuỗi màu thực (CSS var() không dùng được).

`<meta name="theme-color">` và `manifest.json` bắt buộc là giá trị literal. Các giá trị này
trùng với token `--primary` và `--bg` trong `app/static/styles.css`; web (FastAPI) và bản
đóng gói tĩnh (`scripts/build_mobile_web.py`) cùng đọc từ đây để không lệch nhau.
"""

THEME_COLOR = "#3f6b3a"  # --primary (xanh lá chính)
BACKGROUND_COLOR = "#f6f1e7"  # --bg (nền kem giấy)
