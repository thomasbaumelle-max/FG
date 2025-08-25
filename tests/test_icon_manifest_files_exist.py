import json
from pathlib import Path

def test_icon_files_exist():
    base = Path('assets/icons')
    with open(base / 'icons.json', 'r', encoding='utf8') as fh:
        manifest = json.load(fh)
    missing = [name for name, filename in manifest.items() if not (base / filename).is_file()]
    assert not missing, f"Missing icon files: {missing}"
