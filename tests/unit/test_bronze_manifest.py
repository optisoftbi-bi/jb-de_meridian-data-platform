from src.bronze_manifest import load_manifest, manifest_path, save_manifest


def test_missing_coordinate_has_no_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("BRONZE_PATH", str(tmp_path))
    assert load_manifest("jc", "2026-06") is None


def test_manifest_is_saved_per_market_and_month(tmp_path, monkeypatch):
    monkeypatch.setenv("BRONZE_PATH", str(tmp_path))
    manifest = {"active_version": "abc", "versions": {}}

    save_manifest("jc", "2026-06", manifest)

    assert load_manifest("jc", "2026-06") == manifest
    assert load_manifest("jc", "2026-07") is None
    assert manifest_path("jc", "2026-06") == (
        tmp_path / "trips" / "jc" / "2026" / "06" / "manifest.json"
    )
    assert not manifest_path("jc", "2026-06").with_suffix(".json.part").exists()
