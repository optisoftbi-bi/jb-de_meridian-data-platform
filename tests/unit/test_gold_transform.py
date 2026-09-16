from datetime import date

import pytest

import src.gold_transform as gold


class FakeCursor:
    def __init__(self, results):
        self.results = list(results)
        self.executions = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, parameters=None):
        self.executions.append((query, parameters))

    def fetchone(self):
        return self.results.pop(0)


class FakeConnection:
    def __init__(self, results):
        self.cursor_instance = FakeCursor(results)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def cursor(self):
        return self.cursor_instance


def test_transform_returns_loaded_event_count(monkeypatch):
    connection = FakeConnection([(7218,), (7218,)])
    monkeypatch.setattr(gold, "_connect", lambda: connection)

    result = gold.transform_to_gold("station-daily", "2026-06-02")

    assert result == {
        "layer": "gold",
        "job": "station-daily",
        "window": "2026-06-02",
        "events": 7218,
    }


def test_transform_fails_reconciliation(monkeypatch):
    connection = FakeConnection([(10,), (11,)])
    monkeypatch.setattr(gold, "_connect", lambda: connection)

    with pytest.raises(RuntimeError, match="reconciliation"):
        gold.transform_to_gold("station-daily", "2026-06-02")


def test_report_returns_required_shape(monkeypatch):
    connection = FakeConnection([(216, 209)])
    monkeypatch.setattr(gold, "_connect", lambda: connection)

    result = gold.report_daily_station_trips("jc", "JC115", "2026-06-02")

    assert result == {
        "market": "jc",
        "station": "JC115",
        "day": "2026-06-02",
        "departures": 216,
        "arrivals": 209,
    }
    assert connection.cursor_instance.executions[0][1] == (
        "jc",
        "JC115",
        date(2026, 6, 2),
    )
