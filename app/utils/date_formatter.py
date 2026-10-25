"""Bộ định dạng ngày tiếng Việt dùng chung (L5).

Hỗ trợ:
- Định dạng dd/MM/yyyy
- Ngày tương đối: Hôm nay, Ngày mai, T7 24/10
- Hạn sử dụng: "Còn 3 ngày", cảnh báo khi <= 2 ngày hoặc quá hạn.
"""

from __future__ import annotations

from datetime import date, datetime

WEEKDAY_LABELS = {
    0: "T2",
    1: "T3",
    2: "T4",
    3: "T5",
    4: "T6",
    5: "T7",
    6: "CN",
}


def parse_date(date_val: str | date) -> date:
    if isinstance(date_val, date):
        return date_val
    return datetime.strptime(date_val.strip()[:10], "%Y-%m-%d").date()


def format_date_vn(date_val: str | date) -> str:
    d = parse_date(date_val)
    return d.strftime("%d/%m/%Y")


def format_relative_date(date_val: str | date, today: date | None = None) -> str:
    if today is None:
        today = date.today()
    d = parse_date(date_val)
    diff = (d - today).days

    short_date = d.strftime("%d/%m")
    dow = WEEKDAY_LABELS.get(d.weekday(), "")

    if diff == 0:
        return f"Hôm nay, {short_date}"
    if diff == 1:
        return f"Ngày mai, {short_date}"
    if diff == -1:
        return f"Hôm qua, {short_date}"
    return f"{dow} {short_date}"


def format_expiry_status(
    expiry_val: str | date, today: date | None = None
) -> dict[str, str | bool | int]:
    if today is None:
        today = date.today()
    d = parse_date(expiry_val)
    diff = (d - today).days
    date_formatted = d.strftime("%d/%m/%Y")

    if diff < 0:
        return {
            "text": f"Quá hạn {abs(diff)} ngày ({date_formatted})",
            "is_warning": True,
            "is_expired": True,
            "days_remaining": diff,
        }
    if diff == 0:
        return {
            "text": f"Hết hạn hôm nay ({date_formatted})",
            "is_warning": True,
            "is_expired": True,
            "days_remaining": 0,
        }
    if diff == 1:
        return {
            "text": f"Hết hạn ngày mai ({date_formatted})",
            "is_warning": True,
            "is_expired": False,
            "days_remaining": 1,
        }
    if diff == 2:
        return {
            "text": f"Còn 2 ngày ({date_formatted})",
            "is_warning": True,
            "is_expired": False,
            "days_remaining": 2,
        }
    return {
        "text": f"Còn {diff} ngày ({date_formatted})",
        "is_warning": False,
        "is_expired": False,
        "days_remaining": diff,
    }
