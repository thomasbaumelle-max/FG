from __future__ import annotations

"""Simple options menu for adjusting audio and graphics settings."""

import json
import os
from typing import Tuple

import pygame
import settings

try:  # pragma: no cover - allow package and script use
    from .. import constants, audio
except ImportError:  # pragma: no cover
    import constants, audio  # type: ignore

try:  # pragma: no cover
    from .menu_utils import simple_menu
except ImportError:  # pragma: no cover
    from menu_utils import simple_menu  # type: ignore

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "settings.json")


def _load_fullscreen() -> bool:
    if os.path.isfile(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return bool(data.get("fullscreen", False))
        except Exception:  # pragma: no cover - invalid json
            return False
    return False


def _load_difficulty() -> str:
    """Return the saved AI difficulty or a sensible default."""
    default = constants.AI_DIFFICULTY
    if os.path.isfile(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            diff = str(data.get("ai_difficulty", default))
            return diff if diff in constants.AI_DIFFICULTIES else default
        except Exception:  # pragma: no cover - invalid json
            return default
    return default


def _key_name(code: int) -> str:
    for name in dir(pygame):
        if name.startswith("K_") and getattr(pygame, name, None) == code:
            return name
    return str(code)


def _wait_for_key(screen: pygame.Surface, prompt: str) -> int:
    font = pygame.font.SysFont(None, 32)
    rect = screen.get_rect()
    screen.fill((0, 0, 0))
    txt = font.render(prompt, True, (255, 255, 255))
    screen.blit(txt, txt.get_rect(center=rect.center))
    pygame.display.flip()
    while True:
        evt = pygame.event.wait()
        if evt.type == pygame.KEYDOWN:
            return evt.key


def _keymap_menu(screen: pygame.Surface) -> pygame.Surface:
    actions = [
        ("pan_left", "Caméra gauche"),
        ("pan_right", "Caméra droite"),
        ("pan_up", "Caméra haut"),
        ("pan_down", "Caméra bas"),
        ("zoom_in", "Zoom avant"),
        ("zoom_out", "Zoom arrière"),
    ]
    while True:
        opts = [
            f"{label} : {', '.join(settings.KEYMAP.get(key, []))}"
            for key, label in actions
        ]
        opts.append("Retour")
        choice, screen = simple_menu(screen, opts, title="Touches")
        if choice is None or choice == len(actions):
            audio.save_settings(keymap=settings.KEYMAP)
            return screen
        action_key, action_label = actions[choice]
        code = _wait_for_key(screen, f"Touche pour {action_label}")
        name = _key_name(code)
        settings.KEYMAP[action_key] = [name]


def options_menu(screen: pygame.Surface) -> pygame.Surface:
    """Display the options menu and return the (potentially new) screen."""

    music = audio.get_music_volume()
    sfx = audio.get_sfx_volume()
    volume = settings.VOLUME
    fullscreen = _load_fullscreen()
    difficulties = list(constants.AI_DIFFICULTIES)
    labels = [constants.DIFFICULTY_LABELS[d] for d in difficulties]
    difficulty_idx = difficulties.index(_load_difficulty())
    tracks = audio.get_music_tracks()
    current_track = audio.get_current_music() or audio.get_default_music()
    track_idx = tracks.index(current_track) if current_track in tracks else -1
    scroll_speed = settings.SCROLL_SPEED
    languages = {"en": "English", "fr": "Français"}
    lang_codes = list(languages.keys())
    lang_idx = lang_codes.index(settings.LANGUAGE) if settings.LANGUAGE in lang_codes else 0

    def _update_texts() -> Tuple[str, ...]:
        track_name = tracks[track_idx] if track_idx >= 0 else "Aucun"
        return (
            f"Volume : {int(volume * 100)}%",
            f"Musique : {int(music * 100)}%",
            f"Sons : {int(sfx * 100)}%",
            f"Vitesse scroll : {scroll_speed}",
            f"Plein écran : {'Oui' if fullscreen else 'Non'}",
            f"Difficulté IA : {labels[difficulty_idx]}",
            f"Musique de fond : {track_name}",
            "Touches",
            f"Langue : {languages[lang_codes[lang_idx]]}",
        )

    while True:
        (
            opt_vol,
            opt_music,
            opt_sfx,
            opt_scroll,
            opt_full,
            opt_ai,
            opt_track,
            opt_keys,
            opt_lang,
        ) = _update_texts()
        options = [
            opt_vol,
            opt_music,
            opt_sfx,
            opt_scroll,
            opt_full,
            opt_ai,
            opt_track,
            opt_keys,
            opt_lang,
            "Retour",
        ]

        choice, screen = simple_menu(screen, options, title="Options")

        if choice is None or choice == 9:
            audio.save_settings(
                fullscreen=fullscreen,
                ai_difficulty=difficulties[difficulty_idx],
                music_track=tracks[track_idx] if track_idx >= 0 else "",
                scroll_speed=scroll_speed,
                language=lang_codes[lang_idx],
                volume=volume,
            )
            return screen

        if choice == 0:
            sel, screen = simple_menu(
                screen, ["Augmenter", "Diminuer", "Retour"], title="Volume général"
            )
            if sel == 0:
                volume = min(1.0, volume + 0.1)
            elif sel == 1:
                volume = max(0.0, volume - 0.1)
            audio.set_music_volume(volume, save=False)
            audio.set_sfx_volume(volume, save=False)
            settings.VOLUME = volume
            audio.save_settings(
                fullscreen=fullscreen,
                ai_difficulty=difficulties[difficulty_idx],
                music_track=tracks[track_idx] if track_idx >= 0 else "",
                scroll_speed=scroll_speed,
                language=lang_codes[lang_idx],
                volume=volume,
            )
        elif choice == 1:
            sel, screen = simple_menu(
                screen, ["Augmenter", "Diminuer", "Retour"], title="Volume Musique"
            )
            if sel == 0:
                music = min(1.0, music + 0.1)
            elif sel == 1:
                music = max(0.0, music - 0.1)
            audio.set_music_volume(music, save=False)
            audio.save_settings(
                fullscreen=fullscreen,
                ai_difficulty=difficulties[difficulty_idx],
                music_track=tracks[track_idx] if track_idx >= 0 else "",
                scroll_speed=scroll_speed,
                language=lang_codes[lang_idx],
                volume=volume,
            )
        elif choice == 2:
            sel, screen = simple_menu(
                screen, ["Augmenter", "Diminuer", "Retour"], title="Volume Sons"
            )
            if sel == 0:
                sfx = min(1.0, sfx + 0.1)
            elif sel == 1:
                sfx = max(0.0, sfx - 0.1)
            audio.set_sfx_volume(sfx, save=False)
            audio.save_settings(
                fullscreen=fullscreen,
                ai_difficulty=difficulties[difficulty_idx],
                music_track=tracks[track_idx] if track_idx >= 0 else "",
                scroll_speed=scroll_speed,
                language=lang_codes[lang_idx],
                volume=volume,
            )
        elif choice == 3:
            sel, screen = simple_menu(
                screen, ["Augmenter", "Diminuer", "Retour"], title="Vitesse scroll"
            )
            if sel == 0:
                scroll_speed += 5
            elif sel == 1:
                scroll_speed = max(1, scroll_speed - 5)
            settings.SCROLL_SPEED = scroll_speed
            audio.save_settings(
                fullscreen=fullscreen,
                ai_difficulty=difficulties[difficulty_idx],
                music_track=tracks[track_idx] if track_idx >= 0 else "",
                scroll_speed=scroll_speed,
                language=lang_codes[lang_idx],
                volume=volume,
            )
        elif choice == 4:
            fullscreen = not fullscreen
            pygame.display.toggle_fullscreen()
            audio.save_settings(
                fullscreen=fullscreen,
                ai_difficulty=difficulties[difficulty_idx],
                music_track=tracks[track_idx] if track_idx >= 0 else "",
                scroll_speed=scroll_speed,
                language=lang_codes[lang_idx],
                volume=volume,
            )
        elif choice == 5:
            sel, screen = simple_menu(
                screen,
                [l.capitalize() for l in labels],
                title="Difficulté IA",
            )
            if sel is not None:
                difficulty_idx = sel
                audio.save_settings(
                    ai_difficulty=difficulties[difficulty_idx],
                    fullscreen=fullscreen,
                    music_track=tracks[track_idx] if track_idx >= 0 else "",
                    scroll_speed=scroll_speed,
                    language=lang_codes[lang_idx],
                    volume=volume,
                )
        elif choice == 6:
            if tracks:
                sel, screen = simple_menu(
                    screen,
                    tracks + ["Arrêter", "Retour"],
                    title="Musique de fond",
                )
                if sel is not None:
                    if sel < len(tracks):
                        track_idx = sel
                        audio.play_music(tracks[track_idx])
                    elif sel == len(tracks):
                        track_idx = -1
                        audio.stop_music()
                audio.save_settings(
                    fullscreen=fullscreen,
                    ai_difficulty=difficulties[difficulty_idx],
                    music_track=tracks[track_idx] if track_idx >= 0 else "",
                    scroll_speed=scroll_speed,
                    language=lang_codes[lang_idx],
                    volume=volume,
                )
        elif choice == 7:
            screen = _keymap_menu(screen)
            audio.save_settings(
                fullscreen=fullscreen,
                ai_difficulty=difficulties[difficulty_idx],
                music_track=tracks[track_idx] if track_idx >= 0 else "",
                scroll_speed=scroll_speed,
                language=lang_codes[lang_idx],
                volume=volume,
            )
        elif choice == 8:
            sel, screen = simple_menu(
                screen, list(languages.values()), title="Langue"
            )
            if sel is not None:
                lang_idx = sel
                settings.LANGUAGE = lang_codes[lang_idx]
                audio.save_settings(
                    fullscreen=fullscreen,
                    ai_difficulty=difficulties[difficulty_idx],
                    music_track=tracks[track_idx] if track_idx >= 0 else "",
                    scroll_speed=scroll_speed,
                    language=lang_codes[lang_idx],
                    volume=volume,
                )
