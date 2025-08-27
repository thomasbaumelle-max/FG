import os

from core.buildings import Town
from loaders.core import Context
from loaders.town_building_loader import (
    FACTION_TOWN_BUILDING_MANIFESTS,
    load_faction_town_buildings,
)


def _ctx():
    repo = os.path.join(os.path.dirname(__file__), "..")
    repo = os.path.abspath(repo)
    search = [os.path.join(repo, "assets")]
    return Context(repo_root=repo, search_paths=search, asset_loader=None)


def test_faction_town_buildings_available():
    ctx = _ctx()
    for faction_id in FACTION_TOWN_BUILDING_MANIFESTS:
        town = Town(faction_id=faction_id)
        expected = load_faction_town_buildings(ctx, faction_id)
        for bid in expected:
            assert bid in town.structures


def test_faction_recruitment_buildings_present():
    ctx = _ctx()
    for faction_id in FACTION_TOWN_BUILDING_MANIFESTS:
        town = Town(faction_id=faction_id)
        expected = load_faction_town_buildings(ctx, faction_id)
        for bid, info in expected.items():
            if info.get("dwelling"):
                assert bid in town.structures
                assert town.structures[bid].get("dwelling") == info.get("dwelling")


def test_loader_returns_expected_dwellings():
    ctx = _ctx()
    rk = load_faction_town_buildings(ctx, "red_knights")
    assert rk["crimson_watch"]["dwelling"] == {"red_squire": 5}

    syl = load_faction_town_buildings(ctx, "sylvan")
    assert syl["grove_of_lirael"]["dwelling"] == {"moss_sprite": 1, "mist_nymph": 1}

    sol = load_faction_town_buildings(ctx, "solaceheim")
    assert sol["sanctuary_of_the_sun"]["dwelling"] == {"disciple_initie": 1}
