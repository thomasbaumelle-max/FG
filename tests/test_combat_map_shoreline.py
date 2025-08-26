from core.world import WorldMap, generate_combat_map
import pytest
pytestmark = pytest.mark.combat


def test_shoreline_combat_map_has_no_ocean():
    world = WorldMap(map_data=["G.W."])
    grid, _ = generate_combat_map(world, 0, 0)
    assert "ocean" not in {cell for row in grid for cell in row}
