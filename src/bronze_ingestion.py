import hashlib
import sys
from pathlib import Path
from urllib.parse import quote

from requests import request


S3_OBJECT_BASE_URL = "https://s3.amazonaws.com/tripdata"


def download_object_to_file(
    source_key: str,
    destination_path: str,
    expected_size: int,
) -> str:
    object_url = f"{S3_OBJECT_BASE_URL}/{quote(source_key, safe='/')}"
    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    part_path = destination.with_name(destination.name + ".part")

    response = request(
        "GET",
        object_url,
        stream=True,
        timeout=(10, 120),
    )
    response.raise_for_status()

    downloaded = 0
    digest = hashlib.sha256()

    try:
        with part_path.open("wb") as file:
            for chunk in response.iter_content(chunk_size=8 * 1024 * 1024):
                if not chunk:
                    continue
                file.write(chunk)
                digest.update(chunk)
                downloaded += len(chunk)

                if expected_size:
                    percent = downloaded / expected_size * 100
                    print(
                        f"\rDownloading {percent:6.2f}%",
                        end="",
                        flush=True,
                        file=sys.stderr,
                    )

        if downloaded != expected_size:
            raise IOError(
                f"Downloaded {downloaded} bytes; expected {expected_size}"
            )

        part_path.replace(destination)
    except Exception:
        part_path.unlink(missing_ok=True)
        raise
    finally:
        response.close()

    print(file=sys.stderr)
    return digest.hexdigest()
