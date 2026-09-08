from unittest.mock import patch

from requests import RequestException

from src.bronze_sync import (
    build_sync_path,
    sync_bronze,
)


def test_sync_bronze_downloads_new_object():
    manifest = {}

    s3_objects = [
        {
            "key": "JC-202606-citibike-tripdata.zip",
            "last_modified": "2026-07-01T10:00:00Z",
            "size": 100,
        }
    ]

    comparison = {
        "new": s3_objects,
        "changed": [],
        "same": [],
        "deleted": [],
    }

    with patch(
        "src.bronze_sync.load_manifest",
        return_value=manifest,
    ), patch(
        "src.bronze_sync.fetch_s3_listing",
        return_value="<xml></xml>",
    ), patch(
        "src.bronze_sync.parse_s3_listing",
        return_value=s3_objects,
    ), patch(
        "src.bronze_sync.compare_objects",
        return_value=comparison,
    ), patch(
        "src.bronze_sync.build_sync_path",
        return_value="/data/bronze/jc/2026/file.zip",
    ), patch(
        "src.bronze_sync.download_object",
        return_value=b"zip-data",
    ) as mock_download, patch(
        "src.bronze_sync.write_bronze_file"
    ) as mock_write, patch(
        "src.bronze_sync.save_manifest"
    ) as mock_save:

        result = sync_bronze()

    mock_download.assert_called_once_with(
        "JC-202606-citibike-tripdata.zip"
    )

    mock_write.assert_called_once_with(
        "/data/bronze/jc/2026/file.zip",
        b"zip-data",
    )

    mock_save.assert_called_once()

    assert result["status"] == "synced"
    assert result["new"] == 1
    assert result["changed"] == 0
    assert result["deleted"] == 0


def test_sync_bronze_replaces_changed_object():
    key = "202606-citibike-tripdata.zip"

    manifest = {
        key: {
            "last_modified": "2026-01-01T10:00:00Z",
            "size": 100,
            "local_path": (
                "/data/bronze/nyc/2026/"
                "202606-citibike-tripdata.zip"
            ),
        }
    }

    changed_object = {
        "key": key,
        "last_modified": "2026-02-01T10:00:00Z",
        "size": 120,
    }

    comparison = {
        "new": [],
        "changed": [changed_object],
        "same": [],
        "deleted": [],
    }

    with patch(
        "src.bronze_sync.load_manifest",
        return_value=manifest,
    ), patch(
        "src.bronze_sync.fetch_s3_listing",
        return_value="<xml></xml>",
    ), patch(
        "src.bronze_sync.parse_s3_listing",
        return_value=[changed_object],
    ), patch(
        "src.bronze_sync.compare_objects",
        return_value=comparison,
    ), patch(
        "src.bronze_sync.build_sync_path",
        return_value=(
            "/data/bronze/nyc/2026/"
            "202606-citibike-tripdata.zip"
        ),
    ), patch(
        "src.bronze_sync.download_object",
        return_value=b"new-data",
    ) as mock_download, patch(
        "src.bronze_sync.write_bronze_file"
    ) as mock_write, patch(
        "src.bronze_sync.save_manifest"
    ) as mock_save:

        result = sync_bronze()

    mock_download.assert_called_once_with(key)

    mock_write.assert_called_once_with(
        "/data/bronze/nyc/2026/"
        "202606-citibike-tripdata.zip",
        b"new-data",
    )

    mock_save.assert_called_once()

    assert result["status"] == "synced"
    assert result["changed"] == 1


def test_sync_bronze_skips_same_object():
    key = "202606-citibike-tripdata.zip"

    manifest = {
        key: {
            "last_modified": "2026-01-01T10:00:00Z",
            "size": 100,
            "local_path": (
                "/data/bronze/nyc/2026/"
                "202606-citibike-tripdata.zip"
            ),
        }
    }

    same_object = {
        "key": key,
        "last_modified": "2026-01-01T10:00:00Z",
        "size": 100,
    }

    comparison = {
        "new": [],
        "changed": [],
        "same": [same_object],
        "deleted": [],
    }

    with patch(
        "src.bronze_sync.load_manifest",
        return_value=manifest,
    ), patch(
        "src.bronze_sync.fetch_s3_listing",
        return_value="<xml></xml>",
    ), patch(
        "src.bronze_sync.parse_s3_listing",
        return_value=[same_object],
    ), patch(
        "src.bronze_sync.compare_objects",
        return_value=comparison,
    ), patch(
        "src.bronze_sync.download_object"
    ) as mock_download, patch(
        "src.bronze_sync.write_bronze_file"
    ) as mock_write, patch(
        "src.bronze_sync.save_manifest"
    ) as mock_save:

        result = sync_bronze()

    mock_download.assert_not_called()
    mock_write.assert_not_called()

    mock_save.assert_called_once()

    assert result["status"] == "synced"
    assert result["same"] == 1
    assert result["new"] == 0
    assert result["changed"] == 0


def test_sync_bronze_removes_deleted_object(tmp_path):
    local_file = tmp_path / "A.zip"
    local_file.write_bytes(b"old-data")

    manifest = {
        "A.zip": {
            "last_modified": "2026-01-01T10:00:00Z",
            "size": 100,
            "local_path": str(local_file),
        }
    }

    comparison = {
        "new": [],
        "changed": [],
        "same": [],
        "deleted": [
            {
                "key": "A.zip",
                **manifest["A.zip"],
            }
        ],
    }

    with patch(
        "src.bronze_sync.load_manifest",
        return_value=manifest,
    ), patch(
        "src.bronze_sync.fetch_s3_listing",
        return_value="<xml></xml>",
    ), patch(
        "src.bronze_sync.parse_s3_listing",
        return_value=[],
    ), patch(
        "src.bronze_sync.compare_objects",
        return_value=comparison,
    ), patch(
        "src.bronze_sync.save_manifest"
    ) as mock_save:

        result = sync_bronze()

    assert local_file.exists() is False

    mock_save.assert_called_once()

    assert result["status"] == "synced"
    assert result["deleted"] == 1


def test_sync_bronze_uses_existing_manifest_when_s3_offline():
    manifest = {
        "A.zip": {
            "last_modified": "2026-01-01T10:00:00Z",
            "size": 100,
            "local_path": "/data/bronze/A.zip",
        }
    }

    with patch(
        "src.bronze_sync.load_manifest",
        return_value=manifest,
    ), patch(
        "src.bronze_sync.fetch_s3_listing",
        side_effect=RequestException("offline"),
    ), patch(
        "src.bronze_sync.save_manifest"
    ) as mock_save:

        result = sync_bronze()

    mock_save.assert_not_called()

    assert result["status"] == "offline"
    assert result["new"] == 0
    assert result["changed"] == 0
    assert result["same"] == 1
    assert result["deleted"] == 0


def test_build_sync_path_for_jc():
    result = build_sync_path(
        "JC-202606-citibike-tripdata.csv.zip"
    )

    assert result == (
        "/data/bronze/jc/2026/"
        "JC-202606-citibike-tripdata.csv.zip"
    )


def test_build_sync_path_for_nyc_yearly_archive():
    result = build_sync_path(
        "2018-citibike-tripdata.zip"
    )

    assert result == (
        "/data/bronze/nyc/2018/"
        "2018-citibike-tripdata.zip"
    )


def test_build_sync_path_for_nyc_monthly_archive():
    result = build_sync_path(
        "202406-citibike-tripdata.zip"
    )

    assert result == (
        "/data/bronze/nyc/2024/"
        "202406-citibike-tripdata.zip"
    )


def test_build_sync_path_uses_filename_from_nested_key():
    result = build_sync_path(
        "archive/JC-202606-citibike-tripdata.csv.zip"
    )

    assert result == (
        "/data/bronze/jc/2026/"
        "JC-202606-citibike-tripdata.csv.zip"
    )