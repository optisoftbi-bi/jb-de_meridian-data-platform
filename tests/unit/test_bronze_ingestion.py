from src.bronze_ingestion import build_bronze_path


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