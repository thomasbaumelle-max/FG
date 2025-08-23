from types import SimpleNamespace

import pytest

from ui.main_screen import MainScreen


def make_game(size=(800, 600)):
    width, height = size
    screen = SimpleNamespace(get_width=lambda: width, get_height=lambda: height)

    class Game:
        def __init__(self):
            self.screen = screen
            self.offset_x = 0
            self.offset_y = 0
            self.zoom = 1.0
            self.hover_probe = lambda x, y: None
            self.state = SimpleNamespace(heroes=[])

        def _adjust_zoom(self, delta, pos):
            pass

    return Game()


@pytest.mark.parametrize("size", [(800, 600), (1024, 768), (1280, 720)])
def test_hero_and_button_rects_aligned(size):
    game = make_game(size=size)
    ms = MainScreen(game)
    hero_rect = ms.widgets["5"]
    buttons_rect = ms.widgets["6"]
    mini_rect = ms.widgets["4"]
    army_rect = ms.widgets["7"]


    assert hero_rect.width == buttons_rect.width
    assert hero_rect.height == buttons_rect.height
    assert buttons_rect.x == hero_rect.x + hero_rect.width + 8
    assert hero_rect.y == buttons_rect.y
    assert hero_rect.bottom == buttons_rect.bottom
    assert hero_rect.bottom + 8 == army_rect.y
    assert hero_rect.y == mini_rect.bottom + 8
