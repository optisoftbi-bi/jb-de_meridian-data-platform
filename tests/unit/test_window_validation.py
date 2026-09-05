# tests/unit/test_window_validation.py

from src.window_validation import (
    validate_month_window,
    validate_day_window,
)


# -------------------------
# Monthly window tests
# -------------------------

def test_valid_month_window():
    assert validate_month_window("2026-06") is True


def test_day_is_not_valid_month_window():
    assert validate_month_window("2026-06-02") is False


def test_invalid_month_number():
    assert validate_month_window("2026-13") is False


def test_zero_month_is_invalid():
    assert validate_month_window("2026-00") is False


def test_invalid_year_format():
    assert validate_month_window("ABCD-06") is False


def test_invalid_month_format():
    assert validate_month_window("2026-AA") is False


def test_invalid_month_separator():
    assert validate_month_window("2026X06") is False


def test_single_digit_month_is_invalid():
    assert validate_month_window("2026-6") is False


def test_year_only_is_invalid_month_window():
    assert validate_month_window("2026") is False


# -------------------------
# Daily window tests
# -------------------------

def test_valid_day_window():
    assert validate_day_window("2026-06-02") is True


def test_month_is_not_valid_day_window():
    assert validate_day_window("2026-06") is False


def test_invalid_day_year_format():
    assert validate_day_window("ABCD-06-02") is False


def test_invalid_day_month():
    assert validate_day_window("2026-13-02") is False


def test_zero_day_month():
    assert validate_day_window("2026-00-02") is False


def test_invalid_day_number():
    assert validate_day_window("2026-06-32") is False


def test_zero_day_is_invalid():
    assert validate_day_window("2026-06-00") is False


def test_invalid_first_separator():
    assert validate_day_window("2026X06-02") is False


def test_invalid_second_separator():
    assert validate_day_window("2026-06X02") is False


def test_invalid_calendar_date():
    assert validate_day_window("2026-02-31") is False


def test_valid_leap_day():
    assert validate_day_window("2028-02-29") is True


def test_invalid_non_leap_day():
    assert validate_day_window("2026-02-29") is False