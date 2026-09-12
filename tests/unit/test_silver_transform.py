from datetime import datetime
from zipfile import ZipFile

import pytest

import src.silver_transform as silver
from src.silver_transform import _normalize_row


def provenance():
    return {
        "_source_file": "source.zip",
        "_source_member": "trips.csv",
        "_source_row_number": 2,
    }


def test_normalizes_old_schema():
    row = {
        "tripduration": "120.0",
        "starttime": "2019-06-01 10:00:00",
        "stoptime": "2019-06-01 10:02:00",
        "start station id": "3186",
        "end station id": "3203",
        "usertype": "Subscriber",
        **provenance(),
    }

    trip, reject = _normalize_row(row, "jc", "2019-06")

    assert reject is None
    assert datetime(2019, 6, 1, 10, 0) in trip
    assert "3186" in trip
    assert "member" in trip


def test_normalizes_new_schema():
    row = {
        "ride_id": "ride-1",
        "started_at": "2026-06-01 10:00:00.123",
        "ended_at": "2026-06-01 10:05:00.123",
        "start_station_id": "JC115",
        "end_station_id": "JC116",
        "member_casual": "casual",
        **provenance(),
    }

    trip, reject = _normalize_row(row, "jc", "2026-06")

    assert reject is None
    assert "ride-1" in trip
    assert 300.0 in trip


def test_quarantines_missing_required_value():
    row = {
        "started_at": "2026-06-01 10:00:00",
        "ended_at": "2026-06-01 10:05:00",
        "start_station_id": "JC115",
        "end_station_id": "",
        **provenance(),
    }

    trip, reject = _normalize_row(row, "jc", "2026-06")

    assert trip is None
    assert reject[-1] == ["never docked"]


def test_key_is_deterministic():
    row = {
        "ride_id": "ride-1",
        "started_at": "2026-06-01 10:00:00",
        "ended_at": "2026-06-01 10:05:00",
        "start_station_id": "JC115",
        "end_station_id": "JC116",
        **provenance(),
    }

    first, _ = _normalize_row(row, "jc", "2026-06")
    second, _ = _normalize_row(row, "jc", "2026-06")

    assert first[0] == second[0]


def test_reads_only_selected_csv_members(tmp_path, monkeypatch):
    archive_path = tmp_path / "source.zip"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("selected.csv", "ride_id,start_station_id\n1,JC115\n")
        archive.writestr("ignored.csv", "ride_id,start_station_id\n2,JC116\n")

    manifest = {
        "active_version": "v1",
        "versions": {
            "v1": {
                "local_path": str(archive_path),
                "source_key": "source.zip",
                "selected_members": [{"name": "selected.csv"}],
            }
        },
    }
    monkeypatch.setattr(silver, "load_manifest", lambda market, window: manifest)

    rows = list(silver.read_bronze_rows("jc", "2026-06"))

    assert len(rows) == 1
    assert rows[0]["ride_id"] == "1"
    assert rows[0]["_source_member"] == "selected.csv"
    assert rows[0]["_source_row_number"] == 2


def test_missing_bronze_fails(monkeypatch):
    monkeypatch.setattr(silver, "load_manifest", lambda market, window: None)

    with pytest.raises(FileNotFoundError):
        list(silver.read_bronze_rows("jc", "2020-01"))
