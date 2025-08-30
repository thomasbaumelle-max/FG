from core.buildings import Town
from loaders.town_scene_loader import load_town_scene


def test_faction_town_buildings_available():
    town = Town(faction_id="red_knights")
    scene = load_town_scene("assets/towns/red_knights/town.json")
    expected = {b.id for b in scene.buildings}
    for bid in expected:
        assert bid in town.structures


def test_faction_recruitment_buildings_present():
    town = Town(faction_id="red_knights")
    scene = load_town_scene("assets/towns/red_knights/town.json")
    expected = {b.id: b.dwelling for b in scene.buildings if b.dwelling}
    for bid, info in expected.items():
        assert bid in town.structures
        assert town.structures[bid].get("dwelling") == info


def test_loader_returns_expected_dwellings():
    scene = load_town_scene("assets/towns/red_knights/town.json")
    mapping = {b.id: b.dwelling for b in scene.buildings}
    assert mapping["barracks"] == {"Swordsman": 5, "Spearman": 3}
    assert mapping["archery_range"] == {"Archer": 5}
