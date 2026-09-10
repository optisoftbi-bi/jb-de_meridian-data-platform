import hashlib
from unittest.mock import Mock, patch

import pytest

from src.bronze_ingestion import download_object_to_file


def _response(chunks):
    response = Mock()
    response.iter_content.return_value = chunks
    response.raise_for_status.return_value = None
    return response


def test_download_streams_to_final_file(tmp_path):
    destination = tmp_path / "source.zip"
    response = _response([b"zip-", b"data"])

    with patch("src.bronze_ingestion.request", return_value=response):
        digest = download_object_to_file("source.zip", str(destination), 8)

    assert destination.read_bytes() == b"zip-data"
    assert not (tmp_path / "source.zip.part").exists()
    assert digest == hashlib.sha256(b"zip-data").hexdigest()


def test_incomplete_download_is_not_published(tmp_path):
    destination = tmp_path / "source.zip"
    response = _response([b"short"])

    with patch("src.bronze_ingestion.request", return_value=response):
        with pytest.raises(IOError):
            download_object_to_file("source.zip", str(destination), 10)

    assert not destination.exists()
    assert not (tmp_path / "source.zip.part").exists()
