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
    bar_h = 24
    margin = 8
    expected_w = 1280 - side_w - 2 * margin
    expected_h = 720 - 3 * bar_h - 3 * margin
    assert ms.widgets["1"].width == expected_w
    assert ms.widgets["1"].height == expected_h
    # hero list and buttons are the same height and directly adjacent
    hero_rect = ms.widgets["5"]
    buttons_rect = ms.widgets["6"]
    assert hero_rect.height == buttons_rect.height
    assert hero_rect.x + hero_rect.width + margin == buttons_rect.x
    assert hero_rect.y == buttons_rect.y
    # Recompute for 16:10
    ms.compute_layout(1280, 800)
    expected_h = 800 - 3 * bar_h - 3 * margin
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
