from pathlib import Path
from unittest.mock import patch

import pytest
from requests import RequestException

from src.bronze_sync import _version_id, sync_bronze


def _object(key, modified="2026-07-01T10:00:00Z", size=100):
    return {"key": key, "last_modified": modified, "size": size}


def test_ingestion_downloads_only_requested_window():
    objects = [
        _object("JC-202605-citibike-tripdata.csv.zip"),
        _object("JC-202606-citibike-tripdata.csv.zip"),
        _object("202606-citibike-tripdata.zip"),
        _object("JC-202607-citibike-tripdata.csv.zip"),
    ]

    with patch("src.bronze_sync.fetch_s3_listing", return_value="xml"), patch(
        "src.bronze_sync.parse_s3_listing", return_value=objects
    ), patch("src.bronze_sync.load_manifest", return_value=None), patch(
        "src.bronze_sync.download_object_to_file", return_value="sha"
    ) as download, patch(
        "src.bronze_sync.select_csv_members", return_value=[{"name": "data.csv"}]
    ), patch("src.bronze_sync.count_selected_rows", return_value=109897), patch(
        "src.bronze_sync.save_manifest"
    ):
        result = sync_bronze("jc", "2026-06")

    assert download.call_count == 1
    assert download.call_args.kwargs["source_key"] == (
        "JC-202606-citibike-tripdata.csv.zip"
    )
    assert result["rows"] == 109897


def test_same_version_is_idempotent(tmp_path):
    selected = _object("JC-202606-citibike-tripdata.csv.zip")
    version_id = _version_id(selected)
    local_file = tmp_path / "source.zip"
    local_file.write_bytes(b"existing")
    manifest = {
        "active_version": version_id,
        "versions": {version_id: {"local_path": str(local_file)}},
    }

    with patch("src.bronze_sync.fetch_s3_listing", return_value="xml"), patch(
        "src.bronze_sync.parse_s3_listing", return_value=[selected]
    ), patch("src.bronze_sync.load_manifest", return_value=manifest), patch(
        "src.bronze_sync.download_object_to_file"
    ) as download, patch("src.bronze_sync.save_manifest") as save:
        result = sync_bronze("jc", "2026-06")

    download.assert_not_called()
    save.assert_not_called()
    assert result["status"] == "same"


def test_changed_source_preserves_previous_manifest_version():
    old = _object("JC-202606-citibike-tripdata.zip", size=90)
    new = _object("JC-202606-citibike-tripdata.csv.zip", size=100)
    old_id = _version_id(old)
    manifest = {
        "active_version": old_id,
        "versions": {old_id: {"local_path": "/old/source.zip"}},
    }

    with patch("src.bronze_sync.fetch_s3_listing", return_value="xml"), patch(
        "src.bronze_sync.parse_s3_listing", return_value=[new]
    ), patch("src.bronze_sync.load_manifest", return_value=manifest), patch(
        "src.bronze_sync.download_object_to_file", return_value="sha"
    ), patch(
        "src.bronze_sync.select_csv_members", return_value=[{"name": "data.csv"}]
    ), patch("src.bronze_sync.count_selected_rows", return_value=10), patch(
        "src.bronze_sync.save_manifest"
    ) as save:
        sync_bronze("jc", "2026-06")

    saved = save.call_args.args[2]
    assert old_id in saved["versions"]
    assert _version_id(new) in saved["versions"]
    assert saved["active_version"] == _version_id(new)


def test_missing_window_fails_without_download():
    with patch("src.bronze_sync.fetch_s3_listing", return_value="xml"), patch(
        "src.bronze_sync.parse_s3_listing", return_value=[]
    ), patch("src.bronze_sync.download_object_to_file") as download:
        with pytest.raises(ValueError, match="No source object found"):
            sync_bronze("jc", "2026-06")

    download.assert_not_called()


def test_ingestion_fails_when_s3_is_offline():
    with patch(
        "src.bronze_sync.fetch_s3_listing",
        side_effect=RequestException("offline"),
    ):
        with pytest.raises(RuntimeError, match="Unable to read"):
            sync_bronze("jc", "2026-06")
