from datetime import datetime, timezone
from pathlib import Path

from requests import RequestException

from src.s3_client import fetch_s3_listing
from src.source_discovery import parse_s3_listing
from src.bronze_manifest import (
    load_manifest,
    save_manifest,
    compare_objects,
)
from src.bronze_ingestion import (
    download_object_to_file,
)


def build_manifest_entry(
    obj: dict,
    local_path: str,
) -> dict:
    return {
        "last_modified": obj["last_modified"],
        "size": obj["size"],
        "local_path": local_path,
        "synced_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }


def build_sync_path(
    source_key: str,
) -> str:
    filename = Path(source_key).name

    if filename.startswith("JC-"):
        market = "jc"
        year = filename[3:7]
    else:
        market = "nyc"
        year = filename[0:4]

    destination = (
        Path("/data/bronze")
        / market
        / year
        / filename
    )

    return str(destination)


def sync_bronze() -> dict:
    manifest = load_manifest()

    # --------------------------------
    # Read current S3 state
    # --------------------------------
    try:
        xml_text = fetch_s3_listing()
        s3_objects = parse_s3_listing(
            xml_text
        )

    except RequestException:
        print(
            "S3 is unavailable. "
            "Using existing Bronze data."
        )

        return {
            "status": "offline",
            "new": 0,
            "changed": 0,
            "same": len(manifest),
            "deleted": 0,
        }

    # --------------------------------
    # Compare S3 vs local Manifest
    # --------------------------------
    comparison = compare_objects(
        s3_objects,
        manifest,
    )

    print(
        f"S3 objects: {len(s3_objects)} | "
        f"NEW: {len(comparison['new'])} | "
        f"CHANGED: {len(comparison['changed'])} | "
        f"SAME: {len(comparison['same'])} | "
        f"DELETED: {len(comparison['deleted'])}"
    )

    total_downloads = (
        len(comparison["new"])
        + len(comparison["changed"])
    )

    download_number = 0

    updated_manifest = dict(manifest)

    # =================================
    # NEW
    # =================================
    for obj in comparison["new"]:
        key = obj["key"]

        download_number += 1

        print()
        print(
            f"[{download_number}/{total_downloads}] "
            f"Downloading NEW:"
        )
        print(key)

        local_path = build_sync_path(
            key
        )

        download_object_to_file(
            source_key=key,
            destination_path=local_path,
            expected_size=obj["size"],
        )

        # Important:
        # we reach here only after the
        # complete file has been downloaded.
        updated_manifest[key] = (
            build_manifest_entry(
                obj,
                local_path,
            )
        )

        # Save progress immediately.
        save_manifest(
            updated_manifest
        )

        print(
            f"[{download_number}/{total_downloads}] "
            f"Saved successfully."
        )

    # =================================
    # CHANGED
    # =================================
    for obj in comparison["changed"]:
        key = obj["key"]

        download_number += 1

        print()
        print(
            f"[{download_number}/{total_downloads}] "
            f"Downloading CHANGED:"
        )
        print(key)

        old_entry = manifest[key]

        old_local_path = (
            old_entry["local_path"]
        )

        new_local_path = (
            build_sync_path(key)
        )

        download_object_to_file(
            source_key=key,
            destination_path=new_local_path,
            expected_size=obj["size"],
        )

        # If the new source now belongs
        # at a different local path,
        # remove the previous file.
        if (
            old_local_path
            != new_local_path
        ):
            old_file = Path(
                old_local_path
            )

            if old_file.exists():
                old_file.unlink()

        updated_manifest[key] = (
            build_manifest_entry(
                obj,
                new_local_path,
            )
        )

        # Save after every successful file.
        save_manifest(
            updated_manifest
        )

        print(
            f"[{download_number}/{total_downloads}] "
            f"Saved successfully."
        )

    # =================================
    # SAME
    # =================================
    # Nothing to download.
    # Existing Bronze file stays as-is.

    # =================================
    # DELETED
    # =================================
    for obj in comparison["deleted"]:
        key = obj["key"]

        local_path = Path(
            obj["local_path"]
        )

        print(
            f"Deleting removed object: "
            f"{key}"
        )

        if local_path.exists():
            local_path.unlink()

        # Also clean an unfinished
        # .part file if one exists.
        part_path = Path(
            str(local_path) + ".part"
        )

        if part_path.exists():
            part_path.unlink()

        updated_manifest.pop(
            key,
            None,
        )

        save_manifest(
            updated_manifest
        )

    print()
    print("Bronze sync completed.")

    return {
        "status": "synced",
        "new": len(
            comparison["new"]
        ),
        "changed": len(
            comparison["changed"]
        ),
        "same": len(
            comparison["same"]
        ),
        "deleted": len(
            comparison["deleted"]
        ),
    }