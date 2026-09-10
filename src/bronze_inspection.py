import csv
from datetime import datetime
from io import TextIOWrapper
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZipInfo

from src.bronze_manifest import load_manifest


def _csv_infos(archive: ZipFile) -> list[ZipInfo]:
    result = []
    for info in archive.infolist():
        path = PurePosixPath(info.filename)
        if info.is_dir() or "__MACOSX" in path.parts:
            continue
        if path.name.startswith(".") or path.suffix.lower() != ".csv":
            continue
        result.append(info)
    return result


def select_csv_members(archive_path: Path, window: str) -> list[dict]:
    window_code = window.replace("-", "")

    with ZipFile(archive_path) as archive:
        candidates = [
            info
            for info in _csv_infos(archive)
            if window_code in PurePosixPath(info.filename).name
        ]

        if not candidates:
            all_csv = _csv_infos(archive)
            if len(all_csv) == 1:
                candidates = all_csv
            else:
                raise ValueError(
                    f"No unambiguous CSV members found for window={window}"
                )

        newest_date = max(info.date_time[:3] for info in candidates)
        newest = [
            info for info in candidates if info.date_time[:3] == newest_date
        ]
        deepest = max(
            len(PurePosixPath(info.filename).parent.parts)
            for info in newest
        )
        selected = [
            info
            for info in newest
            if len(PurePosixPath(info.filename).parent.parts) == deepest
        ]

        parents = {
            str(PurePosixPath(info.filename).parent) for info in selected
        }
        if len(parents) != 1:
            raise ValueError(
                f"Ambiguous export groups for window={window}: {sorted(parents)}"
            )

        return [
            {
                "name": info.filename,
                "modified_at": datetime(*info.date_time).isoformat(),
            }
            for info in sorted(selected, key=lambda item: item.filename)
        ]


def count_selected_rows(
    archive_path: Path,
    selected_members: list[dict],
) -> int:
    total = 0
    with ZipFile(archive_path) as archive:
        for member in selected_members:
            with archive.open(member["name"]) as raw_file:
                with TextIOWrapper(
                    raw_file,
                    encoding="utf-8-sig",
                    errors="replace",
                    newline="",
                ) as text_file:
                    rows = sum(1 for _ in csv.reader(text_file))
                    total += max(rows - 1, 0)
    return total


def inspect_bronze(job: str, market: str, window: str) -> dict:
    manifest = load_manifest(market, window)
    if manifest is None:
        objects = 0
        rows = 0
    else:
        active = manifest["versions"][manifest["active_version"]]
        objects = 1
        rows = active["rows"]

    return {
        "layer": "bronze",
        "job": job,
        "window": window,
        "objects": objects,
        "rows": rows,
    }
