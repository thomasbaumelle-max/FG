from core.entities import Hero, HeroStats, SkillNode, Modifier


def test_modifiers_apply():
    hero = Hero(0, 0, base_stats=HeroStats(10, 5, 4, 3, 2, 1, 0, 0, 0))
    hero.skill_points = 1
    node = SkillNode(
        id="boost",
        name="Boost",
        desc="",
        cost=1,
        requires=[],
        effects=[
            Modifier("dmg", 2, "flat"),
            Modifier("pv", 50, "percent"),
        ],
    )
    assert hero.learn_skill(node)
    assert hero.base_stats.dmg == 7
    assert hero.base_stats.pv == 15
