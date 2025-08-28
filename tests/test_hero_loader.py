import os
from loaders.core import Context
from loaders.hero_loader import load_heroes


def test_hero_loader_parses_manifest():
    repo_root = os.path.dirname(os.path.dirname(__file__))
    ctx = Context(repo_root=repo_root, search_paths=[os.path.join(repo_root, "assets")])
    heroes = load_heroes(ctx, "units/heroes.json")
    assert "scarletia_aurianne" in heroes
    aurianne = heroes["scarletia_aurianne"]
    assert aurianne.faction == "red_knights"
    assert any(u == "swordsman" for u, _ in aurianne.starting_army)
