from loaders.scenario_loader import load_scenario


def test_demo_scenario_contents():
    data = load_scenario("assets/scenarios/demo.json")
    assert data["name"] == "demo"
    assert len(data["players"]) == 1
    assert len(data["players"][0]["cities"]) == 1
    assert len(data["ai"]) == 1
    assert len(data["ai"][0]["cities"]) == 1
    assert len(data["mines"]) == 3
    assert len(data["encounters"]) == 2
    assert len(data["artifacts"]) == 1

