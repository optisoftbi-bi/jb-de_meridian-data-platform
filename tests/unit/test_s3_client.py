from unittest.mock import patch, Mock

from src.s3_client import fetch_s3_listing


def test_fetch_s3_listing_returns_xml_text():
    fake_xml = "<ListBucketResult></ListBucketResult>"

    fake_response = Mock()
    fake_response.text = fake_xml
    fake_response.raise_for_status.return_value = None

    with patch(
        "src.s3_client.request",
        return_value=fake_response
    ):
        result = fetch_s3_listing()

    assert result == fake_xml


def test_fetch_s3_listing_calls_expected_url():
    fake_response = Mock()
    fake_response.text = "<xml></xml>"
    fake_response.raise_for_status.return_value = None

    with patch(
        "src.s3_client.request",
        return_value=fake_response
    ) as mock_request:
        fetch_s3_listing()

    mock_request.assert_called_once_with(
        "GET",
        "https://s3.amazonaws.com/tripdata"
    )


def test_fetch_s3_listing_checks_http_status():
    fake_response = Mock()
    fake_response.text = "<xml></xml>"

    with patch(
        "src.s3_client.request",
        return_value=fake_response
    ):
        fetch_s3_listing()

    fake_response.raise_for_status.assert_called_once()