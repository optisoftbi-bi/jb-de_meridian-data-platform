from src.window_validation import validate_month_window


def test_valid_month_window():
    result = validate_month_window("2026-06")

    assert result is True


def test_day_is_not_valid_month_window():
    result = validate_month_window("2026-06-02")

    assert result is False

def test_invalid_month_number():
    result = validate_month_window("2026-13")

    assert result is False