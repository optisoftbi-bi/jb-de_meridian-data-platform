# src/window_validation.py

from datetime import datetime


def validate_month_window(name: str) -> bool:
    if len(name) != 7:
        return False

    if name[4] != "-":
        return False

    year_text = name[0:4]
    month_text = name[5:7]

    if not year_text.isdigit():
        return False

    if not month_text.isdigit():
        return False

    month = int(month_text)

    if month < 1 or month > 12:
        return False

    return True


def validate_day_window(name: str) -> bool:
    if len(name) != 10:
        return False

    if name[4] != "-" or name[7] != "-":
        return False

    try:
        datetime.strptime(name, "%Y-%m-%d")
    except ValueError:
        return False

    return True