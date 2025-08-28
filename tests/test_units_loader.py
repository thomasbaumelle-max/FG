import json
from loaders.units_loader import load_units
from loaders.core import Context
from core.entities import UnitStats


def test_load_units_with_template(tmp_path):
    manifest = tmp_path / "units.json"
    data = {
        "templates": {
            "base": {
                "abilities": {"a": 1},
                "stats": {
                    "name": "Base",
                    "max_hp": 5,
                    "attack_min": 1,
                    "attack_max": 2,
                    "defence_melee": 1,
                    "defence_ranged": 1,
                    "speed": 3,
                    "attack_range": 1,
                    "initiative": 4,
                    "sheet": "s",
                    "hero_frames": [0, 0],
                    "enemy_frames": [0, 0],
                },
            }
        },
        "units": [
            {
                "id": "u1",
                "template": "base",
                "stats": {"attack_min": 2},
            }
        ],
    }
    manifest.write_text(json.dumps(data))
    ctx = Context(str(tmp_path), [""])
    stats, extras = load_units(ctx, manifest.name)
    st = stats["u1"]
    assert isinstance(st, UnitStats)
    assert st.attack_min == 2
    assert st.speed == 3
    assert st.defence_magic == 0
    assert st.abilities == ["a"]
    assert extras["u1"]["abilities"] == [{"name": "a", "args": []}]
    assert extras["u1"]["template"] == "base"


def test_load_creatures_defaults(tmp_path):
    manifest = tmp_path / "creatures.json"
    data = {
        "creatures": [
            {
                "id": "wolf",
                "stats": {
                    "name": "wolf",
                    "max_hp": 10,
                    "attack_min": 1,
                    "attack_max": 2,
                    "defence_melee": 1,
                    "defence_ranged": 1,
                    "speed": 3,
                    "attack_range": 1,
                },
            }
        ]
    }
    manifest.write_text(json.dumps(data))
    ctx = Context(str(tmp_path), [""])
    stats, extras = load_units(ctx, manifest.name)
    st = stats["wolf"]
    assert isinstance(st, UnitStats)
    assert st.defence_magic == 0
    assert st.sheet == ""
    assert extras["wolf"]["abilities"] == []
