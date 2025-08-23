"""Graphical main menu for starting or loading a game.

This module contains a simple Pygame driven menu used by ``main.py`` to
allow the player to start a new game, load a saved one or quit.  When
starting a new game the player may select a map file from the ``maps``
directory or choose to generate a random map procedurally.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional, Tuple

import pygame

import constants, audio, settings
from core.game import Game, SAVE_SLOT_FILES
from core.faction import Faction
from ui.options_menu import options_menu
from ui.menu_utils import simple_menu

# Backwards compatibility: expose helper under old name
_menu = simple_menu


def _load_menu_texts(language: str) -> dict[str, str]:
    """Load translated menu strings from ``assets/i18n/menu.json``."""
    default = "en"
    path = Path(__file__).resolve().parents[1] / "assets" / "i18n" / "menu.json"
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    texts = data.get(default, {})
    if language != default:
        texts.update(data.get(language, {}))
    return texts


MENU_TEXTS = _load_menu_texts(settings.LANGUAGE)



def _slot_menu(screen: pygame.Surface, title: str) -> Tuple[Optional[int], pygame.Surface]:
    base_dir = os.path.dirname(__file__)
    options = []
    for idx, name in enumerate(SAVE_SLOT_FILES, 1):
        path = os.path.join(base_dir, name)
        label = MENU_TEXTS["slot"].format(index=idx)
        if not os.path.exists(path):
            label += MENU_TEXTS["slot_empty"]
        options.append(label)
    return simple_menu(screen, options, title=title)


def _choose_new_game_mode(screen: pygame.Surface) -> Tuple[Optional[str], pygame.Surface]:
    """Return "scenario" when the scenario option is chosen."""

    options = [MENU_TEXTS["scenario"], MENU_TEXTS["campaign_soon"]]
    sel, screen = simple_menu(screen, options, title=MENU_TEXTS["new_game"])
    if sel is None or sel != 0:
        return None, screen
    return "scenario", screen


def _choose_scenario(screen: pygame.Surface) -> Tuple[Optional[str], pygame.Surface]:
    """Let the player pick a scenario JSON file from the ``scenarios`` directory."""

    scen_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scenarios")
    scen_files = []
    if os.path.isdir(scen_dir):
        scen_files = [f for f in os.listdir(scen_dir) if f.endswith(".json")]
        scen_files.sort()
    options = [os.path.splitext(f)[0] for f in scen_files]
    options.append(MENU_TEXTS["cancel"])
    sel, screen = simple_menu(screen, options, title=MENU_TEXTS["choose_scenario"])
    if sel is None or sel == len(options) - 1:
        return None, screen
    return scen_files[sel], screen


def _cycle_menu(
    screen: pygame.Surface, options: list[str], title: str
) -> Tuple[Optional[int], pygame.Surface]:
    """Select from ``options`` using left/right arrow keys."""

    if not pygame.font.get_init():
        pygame.font.init()
    font = pygame.font.SysFont(None, 36)
    title_font = pygame.font.SysFont(None, 48)
    idx = 0
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None, screen
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    idx = (idx - 1) % len(options)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    idx = (idx + 1) % len(options)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return idx, screen
                elif event.key == pygame.K_ESCAPE:
                    return None, screen
                elif event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                    screen = pygame.display.get_surface()
        screen.fill(constants.BLACK)
        if title:
            text = title_font.render(title, True, constants.WHITE)
            rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 4))
            screen.blit(text, rect)
        label = f"< {options[idx]} >"
        text = font.render(label, True, constants.WHITE)
        rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
        screen.blit(text, rect)
        pygame.display.flip()
        clock.tick(constants.FPS)


def _text_input(
    screen: pygame.Surface, prompt: str, default: str = ""
) -> Tuple[Optional[str], pygame.Surface]:
    """Simple text entry using keyboard."""

    if not pygame.font.get_init():
        pygame.font.init()
    font = pygame.font.SysFont(None, 36)
    title_font = pygame.font.SysFont(None, 48)
    text = default
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None, screen
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return text, screen
                if event.key == pygame.K_ESCAPE:
                    return None, screen
                if event.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                elif event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                    screen = pygame.display.get_surface()
                else:
                    ch = getattr(event, "unicode", "")
                    if ch.isprintable():
                        text += ch
        screen.fill(constants.BLACK)
        prompt_surf = title_font.render(prompt, True, constants.WHITE)
        prect = prompt_surf.get_rect(center=(screen.get_width() // 2, screen.get_height() // 4))
        screen.blit(prompt_surf, prect)
        txt_surf = font.render(text, True, constants.YELLOW)
        trect = txt_surf.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
        screen.blit(txt_surf, trect)
        pygame.display.flip()
        clock.tick(constants.FPS)


def _scenario_config(screen: pygame.Surface, scenario: str) -> Tuple[Optional[dict], pygame.Surface]:
    """Single screen gathering all scenario settings.

    The previous implementation prompted for each value individually.  The new
    layout shows all options at once allowing the player to move between the
    different fields before confirming the configuration.  ``Annuler`` aborts
    the process and ``Confirmer`` accepts all currently selected values.
    """

    # Precompute option lists for the various fields displayed on the screen.
    sizes = list(constants.MAP_SIZE_PRESETS.items())
    size_labels = [f"{k} ({w}x{h})" for k, (w, h) in sizes]
    ai_labels = list(constants.AI_DIFFICULTIES)
    colour_labels = [MENU_TEXTS["blue"], MENU_TEXTS["red"]]
    colour_values = [constants.BLUE, constants.RED]
    faction_opts = [Faction.RED_KNIGHTS, None]
    faction_labels = [
        MENU_TEXTS.get(f.value, f.value) if isinstance(f, Faction) else MENU_TEXTS["random"]
        for f in faction_opts
    ]
    total_players_opts = [2, 3, 4]
    human_players_opts = [1, 2, 3, 4]

    # Current selection indices for each option group.
    idx_size = idx_diff = idx_total = idx_human = idx_colour = idx_faction = 0
    player_name = MENU_TEXTS["default_player_name"]

    rows = [
        MENU_TEXTS["map_size"],
        MENU_TEXTS["ai_difficulty"],
        MENU_TEXTS["total_players"],
        MENU_TEXTS["human_players"],
        MENU_TEXTS["colour"],
        MENU_TEXTS["faction"],
        MENU_TEXTS["name"],
        MENU_TEXTS["confirm"],
        MENU_TEXTS["cancel"],
    ]
    row_idx = 0

    if not pygame.font.get_init():
        pygame.font.init()
    font = pygame.font.SysFont(None, 30)
    title_font = pygame.font.SysFont(None, 48)
    clock = pygame.time.Clock()

    def _clamp_humans() -> None:
        nonlocal idx_human
        if human_players_opts[idx_human] > total_players_opts[idx_total]:
            idx_human = idx_total

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None, screen
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    row_idx = (row_idx - 1) % len(rows)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    row_idx = (row_idx + 1) % len(rows)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    if row_idx == 0:
                        idx_size = (idx_size - 1) % len(size_labels)
                    elif row_idx == 1:
                        idx_diff = (idx_diff - 1) % len(ai_labels)
                    elif row_idx == 2:
                        idx_total = max(0, idx_total - 1)
                        _clamp_humans()
                    elif row_idx == 3:
                        idx_human = max(0, idx_human - 1)
                        _clamp_humans()
                    elif row_idx == 4:
                        idx_colour = (idx_colour - 1) % len(colour_labels)
                    elif row_idx == 5:
                        idx_faction = (idx_faction - 1) % len(faction_labels)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    if row_idx == 0:
                        idx_size = (idx_size + 1) % len(size_labels)
                    elif row_idx == 1:
                        idx_diff = (idx_diff + 1) % len(ai_labels)
                    elif row_idx == 2:
                        idx_total = min(len(total_players_opts) - 1, idx_total + 1)
                        _clamp_humans()
                    elif row_idx == 3:
                        idx_human = min(len(human_players_opts) - 1, idx_human + 1)
                        _clamp_humans()
                    elif row_idx == 4:
                        idx_colour = (idx_colour + 1) % len(colour_labels)
                    elif row_idx == 5:
                        idx_faction = (idx_faction + 1) % len(faction_labels)
                elif event.key == pygame.K_RETURN:
                    if row_idx == 6:  # Name field
                        player_name, screen = _text_input(
                            screen, MENU_TEXTS["player_name_prompt"], default=player_name
                        )
                        if player_name is None:
                            player_name = MENU_TEXTS["default_player_name"]
                    elif row_idx == 7:  # Confirm
                        _clamp_humans()
                        total_players = total_players_opts[idx_total]
                        human_players = min(
                            human_players_opts[idx_human], total_players
                        )
                        ai_count = max(0, total_players - human_players)
                        prefix = MENU_TEXTS.get("ai_name_prefix", "computer")
                        ai_names = [f"{prefix}{i+1}" for i in range(ai_count)]
                        return (
                            {
                                "map_size": sizes[idx_size][0],
                                "difficulty": ai_labels[idx_diff],
                                "scenario": scenario,
                                "total_players": total_players,
                                "human_players": human_players,
                                "player_colour": colour_values[idx_colour],
                                "faction": faction_opts[idx_faction]
                                or Faction.RED_KNIGHTS,
                                "player_name": player_name,
                                "ai_names": ai_names,
                            },
                            screen,
                        )
                    elif row_idx == 8:  # Cancel
                        return None, screen
                elif event.key == pygame.K_ESCAPE:
                    return None, screen
                elif event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                    screen = pygame.display.get_surface()

        _clamp_humans()

        # Rendering
        screen.fill(constants.BLACK)
        title = title_font.render(MENU_TEXTS["configuration"], True, constants.WHITE)
        trect = title.get_rect(
            center=(screen.get_width() // 2, screen.get_height() // 8)
        )
        screen.blit(title, trect)

        values = [
            size_labels[idx_size],
            ai_labels[idx_diff],
            str(total_players_opts[idx_total]),
            str(human_players_opts[idx_human]),
            colour_labels[idx_colour],
            faction_labels[idx_faction],
            player_name,
            "",
            "",
        ]

        for i, (label, value) in enumerate(zip(rows, values)):
            colour = constants.YELLOW if i == row_idx else constants.WHITE
            txt = font.render(f"{label}: {value}", True, colour)
            rect = txt.get_rect(
                center=(screen.get_width() // 2, screen.get_height() // 4 + i * 30)
            )
            screen.blit(txt, rect)

        pygame.display.flip()
        clock.tick(constants.FPS)


def _new_game_flow(screen: pygame.Surface) -> Tuple[Optional[dict], pygame.Surface]:
    """Run the new game configuration flow using consolidated screens."""

    mode, screen = _choose_new_game_mode(screen)
    if mode != "scenario":
        return None, screen
    scen, screen = _choose_scenario(screen)
    if scen is None:
        return None, screen
    config, screen = _scenario_config(screen, scen)
    if config is None:
        return None, screen
    return config, screen


def main_menu(screen: pygame.Surface, can_resume: bool = False) -> pygame.Surface:
    """Display the main menu and act on the player's choice.

    Returns the (possibly new) screen surface.  When ``can_resume`` is True a
    "Retour au jeu" option is added which exits the menu immediately.
    """

    audio.play_music(constants.MUSIC_TITLE)

    while True:
        options = [
            MENU_TEXTS["new_game"],
            MENU_TEXTS["load"],
            MENU_TEXTS["options"],
            MENU_TEXTS["quit"],
        ]
        if can_resume:
            options.insert(0, MENU_TEXTS["resume_game"])
        choice, screen = simple_menu(screen, options)
        if choice is None:
            audio.stop_music()
            return screen
        if can_resume and choice == 0:
            audio.stop_music()
            return screen
            
        offset = 1 if can_resume else 0
        if choice == 0 + offset:  # New game
            config, screen = _new_game_flow(screen)
            if config is None:
                continue
            slot, screen = _slot_menu(screen, title=MENU_TEXTS["choose_save"])
            if slot is None:
                continue
            audio.stop_music()
            game = Game(
                screen,
                use_default_map=False,
                slot=slot,
                map_size=config["map_size"],
                difficulty=config["difficulty"],
                scenario=config["scenario"],
                player_name=config["player_name"],
                player_colour=config["player_colour"],
                faction=config["faction"],
                ai_names=config.get("ai_names"),
            )
            game.run()
            screen = pygame.display.get_surface()
            audio.play_music(constants.MUSIC_TITLE)

        elif choice == 1 + offset:  # Load game
            slot, screen = _slot_menu(screen, title=MENU_TEXTS["choose_save"])
            if slot is None:
                continue
            save_dir = os.path.dirname(__file__)
            save_path = os.path.join(save_dir, SAVE_SLOT_FILES[slot])
            if not os.path.exists(save_path):
                _, screen = simple_menu(
                    screen,
                    [MENU_TEXTS["file_not_found"], MENU_TEXTS["back"]],
                    title=MENU_TEXTS["error"],
                )
                continue
            audio.stop_music()
            game = Game(screen, slot=slot)
            try:
                game.load_game(save_path)
            except FileNotFoundError:
                audio.play_music(constants.MUSIC_TITLE)
                _, screen = simple_menu(
                    screen,
                    [MENU_TEXTS["file_not_found"], MENU_TEXTS["back"]],
                    title=MENU_TEXTS["error"],
                )
                continue
            game.run()
            screen = pygame.display.get_surface()
            audio.play_music(constants.MUSIC_TITLE)

        elif choice == 2 + offset:  # Options
            screen = options_menu(screen)

        else:  # Quit
            audio.stop_music()
            return screen


def pause_menu(screen: pygame.Surface, game: Game) -> Tuple[bool, pygame.Surface]:
    """Display the in-game pause menu.

    Returns ``(quit_to_menu, screen)`` where ``quit_to_menu`` is ``True`` when
    the player chooses to exit to the main menu.  Selecting "Retour au jeu" or
    pressing Escape resumes play.
    """

    while True:
        options = [
            MENU_TEXTS["resume_game"],
            MENU_TEXTS["save"],
            MENU_TEXTS["options"],
            MENU_TEXTS["quit"],
        ]
        choice, screen = simple_menu(screen, options, title=MENU_TEXTS["pause"])
        if choice is None or choice == 0:
            return False, screen
        if choice == 1:  # Save game
            slot, screen = _slot_menu(screen, title=MENU_TEXTS["choose_save"])
            if slot is None:
                continue
            game.current_slot = slot
            game.default_save_path = game.save_slots[slot]
            game.default_profile_path = game.profile_slots[slot]
            game.save_game(game.default_save_path, game.default_profile_path)
        elif choice == 2:  # Options
            screen = options_menu(screen)
        else:  # Quit to menu
            return True, screen
