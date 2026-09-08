from src.bronze_ingestion import build_bronze_path
from unittest.mock import patch, Mock
from src.bronze_ingestion import ingest_to_bronze

from src.bronze_ingestion import (
    build_bronze_path,
    download_object,
)

from src.bronze_ingestion import (
    build_bronze_path,
    download_object,
    write_bronze_file,
)


def test_build_bronze_path_for_jc():
    result = build_bronze_path(
        source_key="JC-202606-citibike-tripdata.zip",
        window="2026-06",
        market="jc",
    )

    assert result == (
        "/data/bronze/jc/2026/"
        "JC-202606-citibike-tripdata.zip"
    )


def test_build_bronze_path_for_nyc():
    result = build_bronze_path(
        source_key="202406-citibike-tripdata.zip",
        window="2024-06",
        market="nyc",
    )

    assert result == (
        "/data/bronze/nyc/2024/"
        "202406-citibike-tripdata.zip"
    )


def test_build_bronze_path_uses_only_filename_from_source_key():
    result = build_bronze_path(
        source_key="archive/files/JC-202606-citibike-tripdata.zip",
        window="2026-06",
        market="jc",
    )

    assert result == (
        "/data/bronze/jc/2026/"
        "JC-202606-citibike-tripdata.zip"
    )


def test_build_bronze_path_uses_year_from_window():
    result = build_bronze_path(
        source_key="JC-201906-citibike-tripdata.zip",
        window="2019-06",
        market="jc",
    )

    assert "/jc/2019/" in result


def test_download_object_returns_bytes():
    fake_bytes = b"fake-zip-content"

    fake_response = Mock()
    fake_response.content = fake_bytes
    fake_response.raise_for_status.return_value = None

    with patch(
        "src.bronze_ingestion.request",
        return_value=fake_response,
    ):
        result = download_object(
            "JC-202606-citibike-tripdata.zip"
        )

    assert result == fake_bytes


def test_download_object_calls_correct_url():
    fake_response = Mock()
    fake_response.content = b"data"
    fake_response.raise_for_status.return_value = None

    with patch(
        "src.bronze_ingestion.request",
        return_value=fake_response,
    ) as mock_request:
        download_object(
            "JC-202606-citibike-tripdata.zip"
        )

    mock_request.assert_called_once_with(
        "GET",
        "https://s3.amazonaws.com/tripdata/"
        "JC-202606-citibike-tripdata.zip",
    )


def test_download_object_checks_http_status():
    fake_response = Mock()
    fake_response.content = b"data"

    with patch(
        "src.bronze_ingestion.request",
        return_value=fake_response,
    ):
        download_object(
            "JC-202606-citibike-tripdata.zip"
        )

    fake_response.raise_for_status.assert_called_once()


def test_write_bronze_file_creates_file(tmp_path):
    destination = tmp_path / "jc" / "2026" / "file.zip"
    content = b"fake-zip-data"

    write_bronze_file(
        str(destination),
        content,
    )

    assert destination.exists()
    assert destination.read_bytes() == content


def test_write_bronze_file_creates_parent_directories(tmp_path):
    destination = (
        tmp_path
        / "nyc"
        / "2018"
        / "archive.zip"
    )

    write_bronze_file(
        str(destination),
        b"data",
    )

    assert destination.parent.exists()


def test_ingest_to_bronze_happy_path():
    fake_xml = "<xml></xml>"

    fake_objects = [
        {
            "key": "JC-202606-citibike-tripdata.zip",
            "last_modified": "2026-07-01T10:00:00Z",
            "size": 123,
        }
    ]

    fake_selected_object = {
        "key": "JC-202606-citibike-tripdata.zip",
        "last_modified": "2026-07-01T10:00:00Z",
        "size": 123,
    }

    with patch(
        "src.bronze_ingestion.fetch_s3_listing",
        return_value=fake_xml,
    ), patch(
        "src.bronze_ingestion.parse_s3_listing",
        return_value=fake_objects,
    ), patch(
        "src.bronze_ingestion.select_source_object",
        return_value=fake_selected_object,
    ), patch(
        "src.bronze_ingestion.build_bronze_path",
        return_value="/data/bronze/jc/2026/JC-202606-citibike-tripdata.zip",
    ), patch(
        "src.bronze_ingestion.download_object",
        return_value=b"fake-zip",
    ), patch(
        "src.bronze_ingestion.write_bronze_file",
    ) as mock_write:

        result = ingest_to_bronze(
            market="jc",
            window="2026-06",
        )

    assert result == (
        "/data/bronze/jc/2026/"
        "JC-202606-citibike-tripdata.zip"
    )

    mock_write.assert_called_once_with(
        "/data/bronze/jc/2026/"
        "JC-202606-citibike-tripdata.zip",
        b"fake-zip",
    )


def test_ingest_to_bronze_raises_when_source_not_found():
    with patch(
        "src.bronze_ingestion.fetch_s3_listing",
        return_value="<xml></xml>",
    ), patch(
        "src.bronze_ingestion.parse_s3_listing",
        return_value=[],
    ), patch(
        "src.bronze_ingestion.select_source_object",
        return_value=None,
    ):

        try:
            ingest_to_bronze(
                market="jc",
                window="2026-06",
            )
        except ValueError:
            assert True
        else:
            assert False