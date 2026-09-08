from pathlib import Path
from unittest.mock import patch

from src.bronze_manifest import (
    load_manifest,
    save_manifest,
    compare_objects,
)


def test_load_manifest_returns_empty_when_file_missing(tmp_path):
    manifest_path = tmp_path / "manifest.json"

    with patch(
        "src.bronze_manifest.MANIFEST_PATH",
        manifest_path,
    ):
        result = load_manifest()

    assert result == {}


def test_save_and_load_manifest(tmp_path):
    manifest_path = tmp_path / "manifest.json"

    manifest = {
        "A.zip": {
            "last_modified": "2026-01-01T10:00:00Z",
            "size": 100,
            "local_path": "/data/bronze/A.zip",
        }
    }

    with patch(
        "src.bronze_manifest.MANIFEST_PATH",
        manifest_path,
    ):
        save_manifest(manifest)
        result = load_manifest()

    assert result == manifest


def test_compare_detects_new_object():
    s3_objects = [
        {
            "key": "A.zip",
            "last_modified": "2026-01-01T10:00:00Z",
            "size": 100,
        }
    ]

    result = compare_objects(
        s3_objects,
        manifest={},
    )

    assert len(result["new"]) == 1
    assert result["new"][0]["key"] == "A.zip"


def test_compare_detects_same_object():
    s3_objects = [
        {
            "key": "A.zip",
            "last_modified": "2026-01-01T10:00:00Z",
            "size": 100,
        }
    ]

    manifest = {
        "A.zip": {
            "last_modified": "2026-01-01T10:00:00Z",
            "size": 100,
            "local_path": "/data/bronze/A.zip",
        }
    }

    result = compare_objects(
        s3_objects,
        manifest,
    )

    assert len(result["same"]) == 1
    assert len(result["changed"]) == 0


def test_compare_detects_changed_last_modified():
    s3_objects = [
        {
            "key": "A.zip",
            "last_modified": "2026-02-01T10:00:00Z",
            "size": 100,
        }
    ]

    manifest = {
        "A.zip": {
            "last_modified": "2026-01-01T10:00:00Z",
            "size": 100,
            "local_path": "/data/bronze/A.zip",
        }
    }

    result = compare_objects(
        s3_objects,
        manifest,
    )

    assert len(result["changed"]) == 1
    assert result["changed"][0]["key"] == "A.zip"


def test_compare_detects_changed_size():
    s3_objects = [
        {
            "key": "A.zip",
            "last_modified": "2026-01-01T10:00:00Z",
            "size": 200,
        }
    ]

    manifest = {
        "A.zip": {
            "last_modified": "2026-01-01T10:00:00Z",
            "size": 100,
            "local_path": "/data/bronze/A.zip",
        }
    }

    result = compare_objects(
        s3_objects,
        manifest,
    )

    assert len(result["changed"]) == 1


def test_compare_detects_deleted_object():
    manifest = {
        "A.zip": {
            "last_modified": "2026-01-01T10:00:00Z",
            "size": 100,
            "local_path": "/data/bronze/A.zip",
        }
    }

    result = compare_objects(
        s3_objects=[],
        manifest=manifest,
    )

    assert len(result["deleted"]) == 1
    assert result["deleted"][0]["key"] == "A.zip"