import json
from pathlib import Path


def test_icon_manifest_contains_paths():
    base = Path("assets/icons")
    with open(base / "icons.json", "r", encoding="utf8") as fh:
        manifest = json.load(fh)
    missing = [
        name
        for name, filename in manifest.items()
        if not isinstance(filename, str) or not filename.startswith("assets/icons/")
    ]
    assert not missing, f"Entries not pointing to assets/icons/: {missing}"
