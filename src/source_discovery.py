import re
import xml.etree.ElementTree as ET
from datetime import datetime


S3_NAMESPACE = {
    "s3": "http://s3.amazonaws.com/doc/2006-03-01/"
}


def classify_market(key: str) -> str:
    """
    Classify an S3 object as Jersey City or NYC.

    JC objects are identified by the JC- prefix.
    All other trip-data objects are considered NYC.
    """
    if key.startswith("JC-"):
        return "jc"

    return "nyc"


def parse_s3_listing(xml_string: str) -> list[dict]:
    """
    Parse an S3 ListBucket XML response into Python dictionaries.

    Each returned object contains:
    - key
    - last_modified
    - size
    """
    root = ET.fromstring(xml_string)

    objects = []

    for contents in root.findall("s3:Contents", S3_NAMESPACE):
        key = contents.findtext(
            "s3:Key",
            namespaces=S3_NAMESPACE,
        )

        last_modified = contents.findtext(
            "s3:LastModified",
            namespaces=S3_NAMESPACE,
        )

        size_text = contents.findtext(
            "s3:Size",
            namespaces=S3_NAMESPACE,
        )

        objects.append(
            {
                "key": key,
                "last_modified": last_modified,
                "size": int(size_text),
            }
        )

    return objects


def is_yearly_archive(key: str) -> bool:
    """
    Detect old NYC yearly archives.

    Example:
    2018-citibike-tripdata.zip
    """
    filename = key.split("/")[-1]

    pattern = r"^\d{4}-citibike-tripdata(?:\.csv)?\.zip$"

    return re.match(pattern, filename) is not None


def object_matches_window(
    key: str,
    market: str,
    window: str,
) -> bool:
    """
    Check whether an object can contain the requested monthly window.

    Monthly example:
        202406-citibike-tripdata.zip
        window=2024-06

    Yearly NYC example:
        2018-citibike-tripdata.zip
        window=2018-04
    """
    object_market = classify_market(key)

    if object_market != market:
        return False

    year = window[0:4]
    month = window[5:7]

    monthly_code = year + month

    if market == "nyc" and is_yearly_archive(key):
        filename = key.split("/")[-1]
        return filename.startswith(year + "-")

    return monthly_code in key


def filter_objects_for_window(
    objects: list[dict],
    market: str,
    window: str,
) -> list[dict]:
    """
    Return only S3 objects that match the requested market and window.
    """
    matching_objects = []

    for obj in objects:
        if object_matches_window(
            obj["key"],
            market,
            window,
        ):
            matching_objects.append(obj)

    return matching_objects


def parse_last_modified(value: str) -> datetime:
    """
    Convert an S3 LastModified string to a datetime.

    Example:
    2025-07-03T17:01:20.000Z
    """
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def select_latest_object(
    objects: list[dict],
) -> dict | None:
    """
    From multiple candidate objects, choose the one with the latest
    last_modified value.
    """
    if not objects:
        return None

    return max(
        objects,
        key=lambda obj: parse_last_modified(
            obj["last_modified"]
        ),
    )


def select_source_object(
    objects: list[dict],
    market: str,
    window: str,
) -> dict | None:
    """
    Main source-selection function.

    1. Filter by market + requested window.
    2. If multiple candidates remain, take the latest occurrence.
    """
    candidates = filter_objects_for_window(
        objects,
        market,
        window,
    )

    return select_latest_object(candidates)