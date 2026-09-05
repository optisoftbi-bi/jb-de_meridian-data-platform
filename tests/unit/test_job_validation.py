
from src.job_validation import validate_trips_job


def test_valid_jc_job():
    assert validate_trips_job("trips:jc") is True


def test_valid_nyc_job():
    assert validate_trips_job("trips:nyc") is True


def test_invalid_market():
    assert validate_trips_job("trips:la") is False


def test_missing_source_prefix():
    assert validate_trips_job("jc") is False


def test_missing_market():
    assert validate_trips_job("trips") is False


def test_empty_job():
    assert validate_trips_job("") is False