from __future__ import annotations

from datetime import date

from app.utils.date_formatter import (
    format_date_vn,
    format_expiry_status,
    format_relative_date,
)


def test_format_date_vn():
    assert format_date_vn("2026-10-25") == "25/10/2026"
    assert format_date_vn(date(2026, 1, 5)) == "05/01/2026"


def test_format_relative_date():
    today = date(2026, 10, 25)  # Sunday
    assert format_relative_date("2026-10-25", today=today) == "Hôm nay, 25/10"
    assert format_relative_date("2026-10-26", today=today) == "Ngày mai, 26/10"
    assert format_relative_date("2026-10-24", today=today) == "Hôm qua, 24/10"
    # 2026-10-27 is Tuesday -> T3
    assert format_relative_date("2026-10-27", today=today) == "T3 27/10"


def test_format_expiry_status():
    today = date(2026, 10, 25)

    expired = format_expiry_status("2026-10-23", today=today)
    assert expired["is_warning"] is True
    assert expired["is_expired"] is True
    assert "Quá hạn 2 ngày" in expired["text"]

    today_exp = format_expiry_status("2026-10-25", today=today)
    assert today_exp["is_warning"] is True
    assert today_exp["is_expired"] is True
    assert "Hết hạn hôm nay" in today_exp["text"]

    tomorrow_exp = format_expiry_status("2026-10-26", today=today)
    assert tomorrow_exp["is_warning"] is True
    assert tomorrow_exp["is_expired"] is False
    assert "Hết hạn ngày mai" in tomorrow_exp["text"]

    two_days_exp = format_expiry_status("2026-10-27", today=today)
    assert two_days_exp["is_warning"] is True
    assert two_days_exp["is_expired"] is False
    assert "Còn 2 ngày" in two_days_exp["text"]

    safe_exp = format_expiry_status("2026-10-30", today=today)
    assert safe_exp["is_warning"] is False
    assert safe_exp["is_expired"] is False
    assert "Còn 5 ngày" in safe_exp["text"]
