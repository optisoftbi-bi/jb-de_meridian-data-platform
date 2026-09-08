import json
from pathlib import Path


MANIFEST_PATH = Path("/data/bronze/manifest.json")


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {}

    with MANIFEST_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with MANIFEST_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            manifest,
            file,
            indent=2,
        )


def compare_objects(
    s3_objects: list[dict],
    manifest: dict,
) -> dict:
    current_by_key = {
        obj["key"]: obj
        for obj in s3_objects
    }

    new_objects = []
    changed_objects = []
    same_objects = []
    deleted_objects = []

    for key, s3_object in current_by_key.items():
        manifest_object = manifest.get(key)

        if manifest_object is None:
            new_objects.append(s3_object)
            continue

        same_last_modified = (
            manifest_object["last_modified"]
            == s3_object["last_modified"]
        )

        same_size = (
            manifest_object["size"]
            == s3_object["size"]
        )

        if same_last_modified and same_size:
            same_objects.append(s3_object)
        else:
            changed_objects.append(s3_object)

    for key, manifest_object in manifest.items():
        if key not in current_by_key:
            deleted_objects.append({
                "key": key,
                **manifest_object,
            })

    return {
        "new": new_objects,
        "changed": changed_objects,
        "same": same_objects,
        "deleted": deleted_objects,
    }