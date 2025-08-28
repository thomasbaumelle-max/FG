import os
from functools import lru_cache
from loaders.units_loader import load_units
from loaders.core import Context

@lru_cache(maxsize=None)
def _load_units():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))
    ctx = Context(base, [''])
    stats, _ = load_units(ctx, 'units/units.json', section='units')
    return stats

def get_unit_stats(name: str):
    units = _load_units()
    if name in units:
        return units[name]
    for st in units.values():
        if st.name == name:
            return st
    raise KeyError(name)
