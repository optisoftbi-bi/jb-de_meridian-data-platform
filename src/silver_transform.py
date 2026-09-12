import csv
import hashlib
import os
import re
import sys
from datetime import datetime
from io import TextIOWrapper
from zipfile import ZipFile

import psycopg
from psycopg.types.json import Jsonb

from src.bronze_manifest import load_manifest


TRIP_COLUMNS = (
    "ride_sk", "source_ride_id", "market", "source_window",
    "started_at", "ended_at", "start_station_id", "end_station_id",
    "start_station_name", "end_station_name", "start_lat", "start_lng",
    "end_lat", "end_lng", "rideable_type", "member_casual",
    "trip_duration_seconds", "bike_id", "birth_year", "gender",
    "source_file", "source_member", "source_row_number",
)

TRIP_INSERT = f"""
    INSERT INTO silver.trips ({", ".join(TRIP_COLUMNS)})
    VALUES ({", ".join(["%s"] * len(TRIP_COLUMNS))})
    ON CONFLICT (ride_sk) DO NOTHING
"""

QUARANTINE_INSERT = """
    INSERT INTO silver.quarantine (
        market, source_window, source_file, source_member,
        source_row_number, raw_record, rejection_reasons
    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
"""


def _load_active_version(market: str, window: str) -> dict:
    manifest = load_manifest(market, window)
    if manifest is None:
        raise FileNotFoundError(
            f"Bronze data not found for market={market}, window={window}"
        )

    active_version = manifest["active_version"]
    return manifest["versions"][active_version]


def _read_csv_member(archive, member_name: str, source_file: str):
    with archive.open(member_name) as raw_file:
        with TextIOWrapper(
            raw_file,
            encoding="utf-8-sig",
            errors="replace",
            newline="",
        ) as text_file:
            reader = csv.DictReader(text_file)
            for row_number, row in enumerate(reader, start=2):
                row["_source_file"] = source_file
                row["_source_member"] = member_name
                row["_source_row_number"] = row_number
                yield row


def read_bronze_rows(market: str, window: str):
    version = _load_active_version(market, window)

    with ZipFile(version["local_path"]) as archive:
        for selected_member in version["selected_members"]:
            yield from _read_csv_member(
                archive,
                selected_member["name"],
                version["source_key"],
            )


def _clean_headers(row: dict) -> dict:
    clean = {}
    for key, value in row.items():
        if key is None or key.startswith("_source_"):
            continue
        name = re.sub(r"[^a-z0-9]+", "_", key.lstrip("\ufeff").lower()).strip("_")
        clean[name] = value.strip() if isinstance(value, str) else value
    return clean


def _value(row: dict, *names):
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return value
    return None


def _timestamp(value):
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        for pattern in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M"):
            try:
                return datetime.strptime(value, pattern)
            except ValueError:
                pass
    return None


def _number(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _integer(value):
    number = _number(value)
    if number is None or not number.is_integer():
        return None
    return int(number)


def _normalize_row(row: dict, market: str, window: str):
    source = _clean_headers(row)
    started_at = _timestamp(_value(source, "started_at", "starttime", "start_time"))
    ended_at = _timestamp(_value(source, "ended_at", "stoptime", "stop_time"))
    start_station_id = _value(source, "start_station_id")
    end_station_id = _value(source, "end_station_id")

    raw_record = {
        key: value for key, value in row.items()
        if key is not None and not key.startswith("_source_")
    }

    if not all((started_at, ended_at, start_station_id, end_station_id)):
        return None, (
            market,
            window,
            row["_source_file"],
            row["_source_member"],
            row["_source_row_number"],
            Jsonb(raw_record),
            ["never docked"],
        )

    source_ride_id = _value(source, "ride_id")
    if source_ride_id:
        identity = f"{market}|ride_id|{source_ride_id}"
    else:
        identity = "|".join(
            [
                market,
                row["_source_file"],
                row["_source_member"],
                str(row["_source_row_number"]),
            ]
        )

    member_casual = _value(source, "member_casual", "usertype", "user_type")
    if member_casual:
        member_casual = {
            "subscriber": "member",
            "customer": "casual",
        }.get(member_casual.lower(), member_casual.lower())

    duration = _number(_value(source, "tripduration", "trip_duration"))
    if duration is None:
        duration = (ended_at - started_at).total_seconds()

    trip = {
        "ride_sk": hashlib.sha256(identity.encode("utf-8")).hexdigest(),
        "source_ride_id": source_ride_id,
        "market": market,
        "source_window": window,
        "started_at": started_at,
        "ended_at": ended_at,
        "start_station_id": start_station_id,
        "end_station_id": end_station_id,
        "start_station_name": _value(source, "start_station_name"),
        "end_station_name": _value(source, "end_station_name"),
        "start_lat": _number(_value(source, "start_lat", "start_station_latitude")),
        "start_lng": _number(_value(source, "start_lng", "start_station_longitude")),
        "end_lat": _number(_value(source, "end_lat", "end_station_latitude")),
        "end_lng": _number(_value(source, "end_lng", "end_station_longitude")),
        "rideable_type": _value(source, "rideable_type"),
        "member_casual": member_casual,
        "trip_duration_seconds": duration,
        "bike_id": _value(source, "bikeid", "bike_id"),
        "birth_year": _integer(_value(source, "birth_year")),
        "gender": _value(source, "gender"),
        "source_file": row["_source_file"],
        "source_member": row["_source_member"],
        "source_row_number": row["_source_row_number"],
    }
    return tuple(trip[column] for column in TRIP_COLUMNS), None


def _connect():
    return psycopg.connect(
        dbname=os.environ.get("POSTGRES_DB", "meridian"),
        user=os.environ.get("POSTGRES_USER", "meridian"),
        password=os.environ.get("POSTGRES_PASSWORD", "change_me"),
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
    )


def _write_batches(cursor, trips: list, rejects: list):
    if trips:
        cursor.executemany(TRIP_INSERT, trips)
        trips.clear()
    if rejects:
        cursor.executemany(QUARANTINE_INSERT, rejects)
        rejects.clear()


def transform_to_silver(job: str, market: str, window: str) -> dict:
    trips = []
    rejects = []
    processed = 0

    with _connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM silver.trips WHERE market = %s AND source_window = %s",
                (market, window),
            )
            cursor.execute(
                "DELETE FROM silver.quarantine WHERE market = %s AND source_window = %s",
                (market, window),
            )

            for row in read_bronze_rows(market, window):
                trip, reject = _normalize_row(row, market, window)
                if trip is not None:
                    trips.append(trip)
                else:
                    rejects.append(reject)

                processed += 1
                if len(trips) + len(rejects) >= 5000:
                    _write_batches(cursor, trips, rejects)
                if processed % 100000 == 0:
                    print(f"Processed {processed:,} rows", file=sys.stderr)

            _write_batches(cursor, trips, rejects)

            cursor.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM silver.trips
                     WHERE market = %s AND source_window = %s)
                    +
                    (SELECT COUNT(*) FROM silver.quarantine
                     WHERE market = %s AND source_window = %s)
                """,
                (market, window, market, window),
            )
            if cursor.fetchone()[0] != processed:
                raise RuntimeError("Silver row reconciliation failed")

    return inspect_silver(job, market, window)


def inspect_silver(job: str, market: str, window: str) -> dict:
    with _connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM silver.trips WHERE market = %s AND source_window = %s",
                (market, window),
            )
            rows = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT reason, COUNT(*)
                FROM silver.quarantine
                CROSS JOIN LATERAL unnest(rejection_reasons) AS reason
                WHERE market = %s AND source_window = %s
                GROUP BY reason
                ORDER BY reason
                """,
                (market, window),
            )
            reasons = dict(cursor.fetchall())

            cursor.execute(
                "SELECT COUNT(*) FROM silver.quarantine WHERE market = %s AND source_window = %s",
                (market, window),
            )
            rejects = cursor.fetchone()[0]

    return {
        "layer": "silver",
        "job": job,
        "window": window,
        "rows": rows,
        "rejects": rejects,
        "reasons": reasons,
    }
