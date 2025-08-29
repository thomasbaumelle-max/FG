import pygame
from types import SimpleNamespace

import pytest

from ui.main_screen import MainScreen


def _dummy_game(width, height):
    surface = SimpleNamespace(get_width=lambda: width, get_height=lambda: height)
    return SimpleNamespace(
        screen=surface,
        offset_x=0,
        offset_y=0,
        zoom=1.0,
        hover_probe=lambda x, y: None,
        _adjust_zoom=lambda delta, pos: None,
    )


@pytest.mark.serial
def test_layout_16_9_and_16_10():
    game = _dummy_game(1280, 720)
    ms = MainScreen(game)
    assert len(ms.widgets) == 8
    side_w = max(260, int(0.23 * 1280))
    bar_h = int(24 * 1.5)
    margin = 8
    expected_w = 1280 - side_w - 2 * margin
    expected_h = 720 - 2 * bar_h - 3 * margin
    assert ms.widgets["1"].width == expected_w
    assert ms.widgets["1"].height == expected_h
    assert ms.widgets["1"].y == ms.widgets["4"].y == margin
    # hero list and buttons are the same height and directly adjacent
    hero_rect = ms.widgets["5"]
    buttons_rect = ms.widgets["6"]
    assert hero_rect.height == buttons_rect.height
    assert hero_rect.x + hero_rect.width + margin == buttons_rect.x
    assert hero_rect.y == buttons_rect.y
    # Recompute for 16:10
    ms.compute_layout(1280, 800)
    expected_h = 800 - 2 * bar_h - 3 * margin
    assert ms.widgets["1"].height == expected_h


@pytest.mark.serial
def test_buttons_remain_adjacent_with_short_height():
    game = _dummy_game(1280, 600)
    ms = MainScreen(game)
    hero_rect = ms.widgets["5"]
    buttons_rect = ms.widgets["6"]
    margin = 8
    assert buttons_rect.y == hero_rect.y
    assert buttons_rect.x == hero_rect.x + hero_rect.width + margin
    assert buttons_rect.width == hero_rect.width


@pytest.mark.serial
@pytest.mark.parametrize("size", [(1024, 768), (1600, 900), (1920, 1080)])
def test_resource_turn_ratio(size):
    game = _dummy_game(*size)
    ms = MainScreen(game)
    res = ms.widgets["3"]
    turn = ms.widgets["3b"]
    total = res.width + turn.width + 8
    ratio = res.width / total
    assert abs(ratio - 0.7) < 0.02
