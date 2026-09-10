import json
import os
from pathlib import Path


def bronze_root() -> Path:
    return Path(os.environ.get("BRONZE_PATH", "/data/bronze"))


def coordinate_directory(market: str, window: str) -> Path:
    year, month = window.split("-")
    return bronze_root() / "trips" / market / year / month


def manifest_path(market: str, window: str) -> Path:
    return coordinate_directory(market, window) / "manifest.json"


def load_manifest(market: str, window: str) -> dict | None:
    path = manifest_path(market, window)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_manifest(market: str, window: str, manifest: dict) -> None:
    path = manifest_path(market, window)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(".json.part")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2, sort_keys=True)
        file.write("\n")

    temporary_path.replace(path)
