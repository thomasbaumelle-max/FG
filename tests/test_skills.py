from core.entities import Hero, HeroStats, SkillNode, Modifier


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
