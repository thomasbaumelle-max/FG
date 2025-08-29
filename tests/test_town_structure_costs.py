import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import json
from core.buildings import Town


def test_all_town_structures_have_costs():
    path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'town_buildings.json')
    with open(path, 'r', encoding='utf-8') as fh:
        data = json.load(fh)
    town = Town()
    for entry in data:
        sid = entry['id']
        cost = entry.get('cost', {})
        assert cost and any(v > 0 for v in cost.values())
        assert town.structure_cost(sid) == cost

