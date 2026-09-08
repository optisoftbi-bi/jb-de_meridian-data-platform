from pathlib import Path
from requests import request

from src.s3_client import fetch_s3_listing
from src.source_discovery import parse_s3_listing, select_source_object



S3_OBJECT_BASE_URL = "https://s3.amazonaws.com/tripdata"


def build_bronze_path(source_key: str, window: str, market: str) -> str:
   year = window[0:4]
   filename = Path(source_key).name
   destination = Path("/data/bronze") / market / year / filename
   
   return str(destination)


def download_object(source_key: str) -> bytes:
    object_url = f"{S3_OBJECT_BASE_URL}/{source_key}"

    response = request("GET", object_url)
    response.raise_for_status()

    return response.content


from pathlib import Path


def write_bronze_file(destination_path: str, content: bytes) -> None:
    destination = Path(destination_path)

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination.write_bytes(content)


def ingest_to_bronze(market: str, window: str) -> str:
    xml_text = fetch_s3_listing()

    objects = parse_s3_listing(xml_text)

    selected_object = select_source_object(
        objects,
        market,
        window,
    )

    if selected_object is None:
        raise ValueError(
            f"No source object found for market={market}, window={window}"
        )

    source_key = selected_object["key"]

    destination = build_bronze_path(
        source_key,
        window,
        market,
    )

    content = download_object(source_key)

    write_bronze_file(
        destination,
        content,
    )

    return destination