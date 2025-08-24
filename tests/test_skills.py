import os

from core.entities import Hero, HeroStats, SkillNode, Modifier, SKILL_CATALOG
from tools.skill_manifest import load_skill_manifest
from tools.icon import get_icon


def test_learn_skill_modifies_stats_and_points():
    hero = Hero(0, 0, base_stats=HeroStats(1, 1, 1, 1, 1, 1, 1, 0, 0))
    hero.skill_points = 2
    node = SkillNode(
        id="s1",
        name="Test",
        desc="",
        cost=1,
        requires=[],
        effects=[Modifier("dmg", 2, "flat")],
    )
    assert hero.learn_skill(node)
    assert hero.skill_points == 1
    assert hero.base_stats.dmg == 3
    assert "s1" in hero.learned_skills.get("combat", set())


def test_learn_skill_requires_prereqs():
    hero = Hero(0, 0)
    hero.skill_points = 2
    a = SkillNode("a", "A", "", 1, [], [])
    b = SkillNode("b", "B", "", 1, ["a"], [])
    assert not hero.learn_skill(b)
    assert hero.learn_skill(a)
    assert hero.learn_skill(b)


def test_learn_skill_adds_tag():
    hero = Hero(0, 0)
    hero.skill_points = 1
    node = SkillNode("t1", "Tag", "", 1, [], ["swift"])
    assert hero.learn_skill(node)
    assert "swift" in hero.tags


def test_red_knights_manifest_and_icons():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    manifest = load_skill_manifest(repo_root)
    branches = ["logistics", "tactics", "marksmanship", "weaponsmithing"]
    ranks = ["N", "A", "E", "M"]
    sheet = os.path.join(repo_root, "assets", "red_knights_skills.png")
    for branch in branches:
        entries = [e for e in manifest if e.get("branch") == branch]
        prev_id = None
        for rank in ranks:
            entry = next(e for e in entries if e["rank"] == rank)
            if prev_id:
                assert prev_id in entry["requires"]
            icon = get_icon(sheet, tuple(entry["coords"]))
            assert hasattr(icon, "get_width") and icon.get_width() > 0
            prev_id = entry["id"]


def test_red_knights_unlock_order():
    hero = Hero(0, 0)
    hero.skill_points = 4
    assert not hero.learn_skill(SKILL_CATALOG["logistics_A"], "logistics")
    assert hero.learn_skill(SKILL_CATALOG["logistics_N"], "logistics")
    assert hero.learn_skill(SKILL_CATALOG["logistics_A"], "logistics")
