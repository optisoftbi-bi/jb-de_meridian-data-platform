from src.source_discovery import (
    classify_market,
    parse_s3_listing,
    is_yearly_archive,
    object_matches_window,
    filter_objects_for_window,
    select_latest_object,
    select_source_object,
)


SAMPLE_XML = """
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
    <Contents>
        <Key>202406-citibike-tripdata.zip</Key>
        <LastModified>2025-07-03T17:01:20.000Z</LastModified>
        <Size>981467136</Size>
    </Contents>
</ListBucketResult>
"""


def test_jc_object_is_classified_as_jc():
    assert (
        classify_market(
            "JC-202606-citibike-tripdata.csv.zip"
        )
        == "jc"
    )


def test_nyc_monthly_object_is_classified_as_nyc():
    assert (
        classify_market(
            "202406-citibike-tripdata.zip"
        )
        == "nyc"
    )


def test_nyc_yearly_object_is_classified_as_nyc():
    assert (
        classify_market(
            "2018-citibike-tripdata.zip"
        )
        == "nyc"
    )


def test_parse_single_s3_object():
    objects = parse_s3_listing(SAMPLE_XML)

    assert len(objects) == 1

    assert (
        objects[0]["key"]
        == "202406-citibike-tripdata.zip"
    )

    assert (
        objects[0]["last_modified"]
        == "2025-07-03T17:01:20.000Z"
    )

    assert objects[0]["size"] == 981467136


def test_detect_yearly_archive():
    assert (
        is_yearly_archive(
            "2018-citibike-tripdata.zip"
        )
        is True
    )


def test_monthly_archive_is_not_yearly():
    assert (
        is_yearly_archive(
            "202406-citibike-tripdata.zip"
        )
        is False
    )


def test_jc_object_matches_requested_window():
    key = "JC-202606-citibike-tripdata.csv.zip"

    assert (
        object_matches_window(
            key,
            "jc",
            "2026-06",
        )
        is True
    )


def test_jc_object_does_not_match_other_month():
    key = "JC-202605-citibike-tripdata.csv.zip"

    assert (
        object_matches_window(
            key,
            "jc",
            "2026-06",
        )
        is False
    )


def test_jc_object_does_not_match_nyc_request():
    key = "JC-202606-citibike-tripdata.csv.zip"

    assert (
        object_matches_window(
            key,
            "nyc",
            "2026-06",
        )
        is False
    )


def test_nyc_monthly_object_matches_window():
    key = "202406-citibike-tripdata.zip"

    assert (
        object_matches_window(
            key,
            "nyc",
            "2024-06",
        )
        is True
    )


def test_nyc_yearly_archive_matches_month_in_same_year():
    key = "2018-citibike-tripdata.zip"

    assert (
        object_matches_window(
            key,
            "nyc",
            "2018-04",
        )
        is True
    )


def test_nyc_yearly_archive_does_not_match_other_year():
    key = "2019-citibike-tripdata.zip"

    assert (
        object_matches_window(
            key,
            "nyc",
            "2018-04",
        )
        is False
    )


def test_filter_objects_for_requested_window():
    objects = [
        {
            "key": "JC-202605-citibike-tripdata.zip",
            "last_modified": "2026-06-01T10:00:00Z",
            "size": 100,
        },
        {
            "key": "JC-202606-citibike-tripdata.zip",
            "last_modified": "2026-07-01T10:00:00Z",
            "size": 200,
        },
        {
            "key": "202606-citibike-tripdata.zip",
            "last_modified": "2026-07-01T10:00:00Z",
            "size": 300,
        },
    ]

    result = filter_objects_for_window(
        objects,
        "jc",
        "2026-06",
    )

    assert len(result) == 1

    assert (
        result[0]["key"]
        == "JC-202606-citibike-tripdata.zip"
    )


def test_latest_object_is_selected():
    objects = [
        {
            "key": "JC-202606-old.zip",
            "last_modified": "2026-07-01T10:00:00Z",
            "size": 100,
        },
        {
            "key": "JC-202606-new.zip",
            "last_modified": "2026-08-01T10:00:00Z",
            "size": 110,
        },
    ]

    result = select_latest_object(objects)

    assert result["key"] == "JC-202606-new.zip"


def test_latest_object_returns_none_when_empty():
    assert select_latest_object([]) is None


def test_select_source_object_returns_latest_matching_source():
    objects = [
        {
            "key": "JC-202605-citibike-tripdata.zip",
            "last_modified": "2026-08-20T10:00:00Z",
            "size": 100,
        },
        {
            "key": "JC-202606-citibike-tripdata.zip",
            "last_modified": "2026-07-01T10:00:00Z",
            "size": 200,
        },
        {
            "key": "JC-202606-citibike-tripdata.csv.zip",
            "last_modified": "2026-08-01T10:00:00Z",
            "size": 210,
        },
        {
            "key": "202606-citibike-tripdata.zip",
            "last_modified": "2026-09-01T10:00:00Z",
            "size": 500,
        },
    ]

    result = select_source_object(
        objects,
        "jc",
        "2026-06",
    )

    assert result is not None

    assert (
        result["key"]
        == "JC-202606-citibike-tripdata.csv.zip"
    )


def test_source_object_returns_none_when_window_missing():
    objects = [
        {
            "key": "JC-202605-citibike-tripdata.zip",
            "last_modified": "2026-06-01T10:00:00Z",
            "size": 100,
        }
    ]

    result = select_source_object(
        objects,
        "jc",
        "2026-06",
    )

    assert result is None