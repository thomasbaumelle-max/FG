"""Check that all icons referenced in icons.json exist."""
from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    base = Path(__file__).resolve().parents[1] / 'assets' / 'icons'
    manifest_file = base / 'icons.json'
    with manifest_file.open('r', encoding='utf-8') as fh:
        data = json.load(fh)
    missing = []
    for icon_id, filename in data.items():
        if not (base / filename).is_file():
            missing.append(f"{icon_id}: {filename}")
    if missing:
        print('Missing icons:')
        for item in missing:
            print(' -', item)
        return 1
    print('All icon files exist.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
