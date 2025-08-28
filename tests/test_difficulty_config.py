import json

import pytest

from core import exploration_ai


def test_difficulty_config_levels():
    params = exploration_ai.DIFFICULTY_PARAMS
    assert {"Novice", "Intermédiaire", "Avancé"} <= params.keys()
    for p in params.values():
        assert set(p.keys()) == {"hero_weight", "resource_weight", "building_weight", "avoid_enemies"}


def test_invalid_difficulty_config(tmp_path):
    bad_cfg = tmp_path / "bad.json"
    bad_cfg.write_text(json.dumps({"Novice": {"hero_weight": 1}}), encoding="utf-8")
    with pytest.raises(ValueError):
        exploration_ai._load_difficulty_params(bad_cfg)
