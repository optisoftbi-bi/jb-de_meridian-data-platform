from pathlib import Path
from zipfile import ZipFile, ZipInfo

from src.bronze_inspection import (
    count_selected_rows,
    inspect_bronze,
    select_csv_members,
)
from src.bronze_manifest import save_manifest


def _add_csv(archive, name, content, date_time):
    info = ZipInfo(name, date_time=date_time)
    archive.writestr(info, content)


def test_monthly_archive_selects_requested_csv(tmp_path):
    archive_path = tmp_path / "jc.zip"
    with ZipFile(archive_path, "w") as archive:
        _add_csv(
            archive,
            "JC-202606-citibike-tripdata.csv",
            "a,b\n1,2\n",
            (2026, 7, 1, 10, 0, 0),
        )

    selected = select_csv_members(archive_path, "2026-06")

    assert [item["name"] for item in selected] == [
        "JC-202606-citibike-tripdata.csv"
    ]
    assert count_selected_rows(archive_path, selected) == 1


def test_2018_april_selects_latest_folder_export(tmp_path):
    archive_path = tmp_path / "2018.zip"
    with ZipFile(archive_path, "w") as archive:
        _add_csv(
            archive,
            "2018-citibike-tripdata/201804-citibike-tripdata.csv",
            "id\nold\n",
            (2018, 9, 6, 10, 0, 0),
        )
        for prefix in (
            "2018-citibike-tripdata",
            "2018-citibike-tripdata/4_April",
        ):
            _add_csv(
                archive,
                f"{prefix}/201804-citibike-tripdata_1.csv",
                "id\na\nb\n",
                (2024, 2, 21, 10, 0, 0),
            )
            _add_csv(
                archive,
                f"{prefix}/201804-citibike-tripdata_2.csv",
                "id\nc\n",
                (2024, 2, 21, 10, 1, 0),
            )

    selected = select_csv_members(archive_path, "2018-04")

    assert [item["name"] for item in selected] == [
        "2018-citibike-tripdata/4_April/201804-citibike-tripdata_1.csv",
        "2018-citibike-tripdata/4_April/201804-citibike-tripdata_2.csv",
    ]
    assert count_selected_rows(archive_path, selected) == 3


def test_inspect_returns_exact_contract(tmp_path, monkeypatch):
    monkeypatch.setenv("BRONZE_PATH", str(tmp_path))
    manifest = {
        "active_version": "v1",
        "versions": {"v1": {"rows": 109897}},
    }
    save_manifest("jc", "2026-06", manifest)

    assert inspect_bronze("trips:jc", "jc", "2026-06") == {
        "layer": "bronze",
        "job": "trips:jc",
        "window": "2026-06",
        "objects": 1,
        "rows": 109897,
    }


def test_inspect_missing_coordinate_returns_zero(tmp_path, monkeypatch):
    monkeypatch.setenv("BRONZE_PATH", str(tmp_path))
    assert inspect_bronze("trips:jc", "jc", "2026-06") == {
        "layer": "bronze",
        "job": "trips:jc",
        "window": "2026-06",
        "objects": 0,
        "rows": 0,
    }
