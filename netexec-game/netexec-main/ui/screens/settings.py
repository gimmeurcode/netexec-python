"""
settings.py — NETEXEC
======================
Settings screen: volume sliders, resolution picker, fullscreen toggle.
"""

import pygame

from scripts.engine.constants import C_GREEN_BRIGHT, C_BORDER, C_CYAN
from ..screen_enum import GameScreen
from ..widgets import draw_button, draw_label, draw_slider
from .base import Screen


class SettingsScreen(Screen):
    def render(self, ctx, state):
        render(ctx, state)


def render(ctx, state):
    from scripts.engine.constants import RESOLUTIONS

    cx  = ctx._sw // 2
    hdr = ctx._f("header").render("SETTINGS", True, C_GREEN_BRIGHT)
    ctx.screen.blit(hdr, hdr.get_rect(center=(cx, 60)))

    pygame.draw.line(ctx.screen, C_BORDER, (cx - 300, 90), (cx + 300, 90), 1)

    y = 120

    draw_label(ctx, "SFX VOLUME", cx - 300, y)
    sfx_rect = pygame.Rect(cx - 300, y + 22, 340, 18)
    draw_slider(ctx, sfx_rect, ctx._settings_sfx_vol,
                lambda v: setattr(ctx, "_settings_sfx_vol", v))
    y += 70

    draw_label(ctx, "MUSIC VOLUME", cx - 300, y)
    mus_rect = pygame.Rect(cx - 300, y + 22, 340, 18)
    draw_slider(ctx, mus_rect, ctx._settings_music_vol,
                lambda v: setattr(ctx, "_settings_music_vol", v))
    y += 70

    draw_label(ctx, "RESOLUTION", cx - 300, y)
    res      = RESOLUTIONS[ctx._settings_res_idx % len(RESOLUTIONS)]
    res_lbl  = ctx._f("body").render(f"{res[0]} x {res[1]}", True, C_GREEN_BRIGHT)
    ctx.screen.blit(res_lbl, (cx - 300, y + 24))

    prev_rect = pygame.Rect(cx, y + 20, 80, 28)
    next_rect = pygame.Rect(cx + 90, y + 20, 80, 28)

    def _prev_res():
        ctx._settings_res_idx = (ctx._settings_res_idx - 1) % len(RESOLUTIONS)

    def _next_res():
        ctx._settings_res_idx = (ctx._settings_res_idx + 1) % len(RESOLUTIONS)

    draw_button(ctx, prev_rect, "< PREV", _prev_res)
    draw_button(ctx, next_rect, "NEXT >", _next_res)
    y += 70

    fs_label = "EXIT FULLSCREEN" if ctx._fullscreen else "ENTER FULLSCREEN  (F11)"
    fs_rect  = pygame.Rect(cx - 150, y, 300, 38)
    draw_button(ctx, fs_rect, fs_label, ctx._toggle_fullscreen,
                border_color=C_CYAN, text_color=C_CYAN)
    y += 54

    tut_rect = pygame.Rect(cx - 150, y, 300, 38)

    def _replay_tutorial():
        ctx._replay_tutorial_requested = True
        ctx._toast("TUTORIAL WILL SHOW ON NEXT GAME START", "info")

    draw_button(ctx, tut_rect, "REPLAY TUTORIAL",
                _replay_tutorial,
                border_color=C_BORDER, text_color=C_GREEN_BRIGHT)
    y += 54

    return_screen = getattr(ctx, "_settings_return_screen", GameScreen.PAUSE)

    def _apply():
        if ctx.audio:
            ctx.audio.set_sfx_volume(ctx._settings_sfx_vol)
            ctx.audio.set_music_volume(ctx._settings_music_vol)
        r = RESOLUTIONS[ctx._settings_res_idx % len(RESOLUTIONS)]
        try:
            pygame.display.set_mode(r)
            ctx.screen = pygame.display.get_surface()
        except Exception:
            pass
        ctx._toast("SETTINGS APPLIED", "success")
        ctx.set_screen(return_screen)

    apply_rect = pygame.Rect(cx - 150, y, 300, 44)
    draw_button(ctx, apply_rect, "APPLY & CLOSE", _apply)

    back_rect = pygame.Rect(20, 20, 100, 36)
    draw_button(ctx, back_rect, "< BACK",
                lambda: ctx.set_screen(return_screen))
