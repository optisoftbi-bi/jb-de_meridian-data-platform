from pathlib import Path
from zipfile import ZipFile
import json



BRONZE_ROOT = Path("/data/bronze")


def find_bronze_archive(market: str, window: str) -> Path:
    year = window[0:4]

    bronze_directory = BRONZE_ROOT / market / year

    archives = list(bronze_directory.glob("*.zip"))

    if not archives:
        raise FileNotFoundError(
            f"No Bronze archive found for market={market}, window={window}"
        )

    return archives[0]


def list_zip_members(archive_path: Path) -> list[str]:
    with ZipFile(archive_path, "r") as archive:
        return archive.namelist()


def find_csv_members(members: list[str]) -> list[str]:
    csv_members = []

    for member in members:
        filename = Path(member).name

        if "__MACOSX" in member:
            continue

        if filename.startswith("."):
            continue

        if not filename.lower().endswith(".csv"):
            continue

        csv_members.append(member)

    return csv_members



def count_csv_rows(archive_path: Path, csv_member: str) -> int:
    with ZipFile(archive_path, "r") as archive:
        with archive.open(csv_member) as csv_file:
            row_count = sum(1 for _ in csv_file)

    return max(row_count - 1, 0)


import json


def inspect_bronze(market: str, window: str) -> dict:
    archive_path = find_bronze_archive(market, window)

    members = list_zip_members(archive_path)
    csv_members = find_csv_members(members)

    if not csv_members:
        raise ValueError(
            f"No CSV members found for market={market}, window={window}"
        )

    rows = count_csv_rows(
        archive_path,
        csv_members[0],
    )

    return {
        "market": market,
        "window": window,
        "objects": 1,
        "rows": rows,
    }