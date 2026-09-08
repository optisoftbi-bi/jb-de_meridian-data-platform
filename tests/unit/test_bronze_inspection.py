from pathlib import Path
from unittest.mock import patch
from src.bronze_inspection import find_csv_members
from zipfile import ZipFile

from src.bronze_inspection import count_csv_rows

import pytest

from src.bronze_inspection import find_bronze_archive

from src.bronze_inspection import (
    find_bronze_archive,
    list_zip_members,
    find_csv_members,
    select_csv_member,
    count_csv_rows,
)


def test_find_bronze_archive_returns_zip(tmp_path):
    archive = tmp_path / "JC-202606-citibike-tripdata.csv.zip"
    archive.write_bytes(b"fake-zip")

    with patch(
        "src.bronze_inspection.BRONZE_ROOT",
        tmp_path,
    ):
        # Our function expects:
        # root / market / year
        directory = tmp_path / "jc" / "2026"
        directory.mkdir(parents=True)

        archive.rename(
            directory / "JC-202606-citibike-tripdata.csv.zip"
        )

        result = find_bronze_archive(
            market="jc",
            window="2026-06",
        )

    assert result.name == "JC-202606-citibike-tripdata.csv.zip"


def test_find_bronze_archive_raises_when_missing(tmp_path):
    with patch(
        "src.bronze_inspection.BRONZE_ROOT",
        tmp_path,
    ):
        with pytest.raises(FileNotFoundError):
            find_bronze_archive(
                market="jc",
                window="2026-06",
            )



def test_find_csv_members_ignores_macos_metadata():
    members = [
        "JC-202606-citibike-tripdata.csv",
        "__MACOSX/._JC-202606-citibike-tripdata.csv",
        ".DS_Store",
        "notes.txt",
    ]

    result = find_csv_members(members)

    assert result == [
        "JC-202606-citibike-tripdata.csv"
    ]


def test_count_csv_rows_excludes_header(tmp_path):
    archive_path = tmp_path / "test.zip"

    csv_content = (
        "ride_id,start_station_id\n"
        "1,JC001\n"
        "2,JC002\n"
        "3,JC003\n"
    )

    with ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "trips.csv",
            csv_content,
        )

    result = count_csv_rows(
        archive_path,
        "trips.csv",
    )

    assert result == 3


def test_select_csv_member_for_requested_month():
    members = [
        "201803-citibike-tripdata.csv",
        "201804-citibike-tripdata.csv",
        "201805-citibike-tripdata.csv",
    ]

    result = select_csv_member(
        members,
        market="nyc",
        window="2018-04",
    )

    assert result == "201804-citibike-tripdata.csv"


def test_select_csv_member_raises_when_month_missing():
    members = [
        "201803-citibike-tripdata.csv",
        "201805-citibike-tripdata.csv",
    ]

    with pytest.raises(FileNotFoundError):
        select_csv_member(
            members,
            market="nyc",
            window="2018-04",
        )