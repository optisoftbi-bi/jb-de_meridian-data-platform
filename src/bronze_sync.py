import hashlib
from datetime import datetime, timezone
from pathlib import Path

from requests import RequestException

from src.bronze_ingestion import download_object_to_file
from src.bronze_inspection import count_selected_rows, select_csv_members
from src.bronze_manifest import coordinate_directory, load_manifest, save_manifest
from src.s3_client import fetch_s3_listing
from src.source_discovery import parse_s3_listing, select_source_object


def _version_id(source: dict) -> str:
    identity = "|".join(
        [source["key"], source["last_modified"], str(source["size"])]
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def _archive_path(
    market: str,
    window: str,
    version_id: str,
    source_key: str,
) -> Path:
    filename = Path(source_key).name
    return (
        coordinate_directory(market, window)
        / "versions"
        / version_id
        / filename
    )


def sync_bronze(market: str, window: str) -> dict:
    try:
        objects = parse_s3_listing(fetch_s3_listing())
    except RequestException as exc:
        raise RuntimeError("Unable to read the S3 source listing") from exc

    selected = select_source_object(objects, market, window)
    if selected is None:
        raise ValueError(
            f"No source object found for market={market}, window={window}"
        )

    version_id = _version_id(selected)
    manifest = load_manifest(market, window)

    if manifest is not None and version_id in manifest["versions"]:
        version = manifest["versions"][version_id]
        if Path(version["local_path"]).exists():
            return {
                "status": "same",
                "market": market,
                "window": window,
                "source_key": selected["key"],
            }

    destination = _archive_path(
        market,
        window,
        version_id,
        selected["key"],
    )
    sha256 = download_object_to_file(
        source_key=selected["key"],
        destination_path=str(destination),
        expected_size=selected["size"],
    )
    selected_members = select_csv_members(destination, window)
    rows = count_selected_rows(destination, selected_members)

    if manifest is None:
        manifest = {
            "layer": "bronze",
            "job": f"trips:{market}",
            "market": market,
            "window": window,
            "active_version": version_id,
            "versions": {},
        }

    manifest["active_version"] = version_id
    manifest["versions"][version_id] = {
        "source_key": selected["key"],
        "source_last_modified": selected["last_modified"],
        "source_size": selected["size"],
        "local_path": str(destination),
        "sha256": sha256,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "selected_members": selected_members,
        "rows": rows,
    }
    save_manifest(market, window, manifest)

    return {
        "status": "downloaded",
        "market": market,
        "window": window,
        "source_key": selected["key"],
        "rows": rows,
    }
