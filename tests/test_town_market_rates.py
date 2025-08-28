import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

from core.buildings import Town
from core.economy import DEFAULT_MARKET_RATES

def test_town_uses_shared_market_rates():
    town = Town()
    assert town.market_rates is DEFAULT_MARKET_RATES

