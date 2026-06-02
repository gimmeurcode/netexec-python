"""
widgets.py — NETEXEC
=====================
Shared UI primitive functions used by all screen modules.

Each function accepts ``ctx`` — the live GameUI controller instance — which
provides the surface, fonts, mouse position, and click/tooltip region lists.
Screen modules import these instead of calling methods directly on the
controller so that widget logic has a single canonical home.

Public API
----------
  draw_button          Draw a CRT-style button and register its click region.
  draw_modal_overlay   Draw a semi-transparent darkening layer for modals.
  draw_label           Draw a plain text label.
  draw_slider          Draw a horizontal slider with drag interaction.
  draw_text_wrapped    Render word-wrapped text inside a bounding rect.
"""

import pygame

from scripts.engine.constants import (
    C_GREEN_BRIGHT, C_GREEN_MID, C_GREEN_DIM, C_GREEN_PANEL,
    C_WHITE, C_BORDER, C_BORDER_DIM,
)
from .theme import C_TINT_BTN_HOVER, C_TINT_SHADOW


def draw_button(ctx, rect: pygame.Rect, label: str, callback,
                bg_color=None, border_color=None, text_color=None):
    """
    Draw a retro CRT-style button and register its click region.

    Parameters
    ----------
    ctx          : GameUI  Controller instance (provides surface, fonts, etc.)
    rect         : Rect    Button bounding box.
    label        : str     Button text.
    callback     : callable  Invoked when the button is clicked.
    bg_color     : tuple | None  Override fill colour.
    border_color : tuple | None  Override border colour.
    text_color   : tuple | None  Override label colour.
    """
    hovered = rect.collidepoint(ctx._mouse_pos)
    bg      = bg_color     or (C_TINT_BTN_HOVER if hovered else C_GREEN_PANEL)
    border  = border_color or (C_GREEN_BRIGHT if hovered else C_BORDER)
    tc      = text_color   or (C_WHITE if hovered else C_GREEN_BRIGHT)

    pygame.draw.rect(ctx.screen, bg,     rect, border_radius=4)
    bw = 2 if hovered and border_color is None else 1
    pygame.draw.rect(ctx.screen, border, rect, bw, border_radius=4)

    if hovered:
        hl_col = tuple(min(255, c + 60) for c in border)
        pygame.draw.line(ctx.screen, hl_col,
                         (rect.x + 5, rect.y + 1), (rect.right - 5, rect.y + 1))

    txt = ctx._f("small").render(label, True, tc)
    ctx.screen.blit(txt, txt.get_rect(center=rect.center))

    ctx._click_regions.append((rect, callback))


def draw_modal_overlay(ctx, alpha: int = 160):
    """Draw a semi-transparent dark overlay behind modal dialogs."""
    overlay = pygame.Surface((ctx._sw, ctx._sh), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, alpha))
    ctx.screen.blit(overlay, (0, 0))


def draw_label(ctx, text: str, x: int, y: int, color=None):
    """Draw a simple text label using the 'small' font."""
    col  = color or C_GREEN_MID
    surf = ctx._f("small").render(text, True, col)
    ctx.screen.blit(surf, (x, y))


def draw_slider(ctx, rect: pygame.Rect, value: float, on_change):
    """
    Draw a horizontal slider and register drag interaction.

    Parameters
    ----------
    ctx       : GameUI  Controller instance.
    rect      : Rect    Slider bounding box.
    value     : float   Current value in [0.0, 1.0].
    on_change : callable  Called with the new float value when dragged.
    """
    pygame.draw.rect(ctx.screen, C_GREEN_DIM, rect)
    pygame.draw.rect(ctx.screen, C_BORDER,    rect, 1)
    filled_w = int(rect.width * value)
    if filled_w > 0:
        pygame.draw.rect(ctx.screen, C_GREEN_BRIGHT,
                         (rect.x, rect.y, filled_w, rect.height))
    hx = rect.x + filled_w
    pygame.draw.rect(ctx.screen, C_WHITE, (hx - 3, rect.y - 2, 6, rect.height + 4))

    def _drag():
        mx      = ctx._mouse_pos[0]
        new_val = max(0.0, min(1.0, (mx - rect.x) / rect.width))
        on_change(new_val)

    ctx._click_regions.append((rect, _drag))


def draw_scrollbar(ctx, track_rect: pygame.Rect,
                   total_h: int, view_h: int, scroll_y: int,
                   on_scroll) -> int:
    """
    Draw a vertical scrollbar and register its interactions.

    Parameters
    ----------
    ctx        : GameUI  Controller instance.
    track_rect : Rect    Full scrollbar track area (narrow vertical rect).
    total_h    : int     Total content height in pixels.
    view_h     : int     Visible viewport height in pixels.
    scroll_y   : int     Current scroll offset (px from top).
    on_scroll  : callable(new_scroll_y)  Called when the user drags the thumb.

    Returns
    -------
    int  Clamped scroll_y value (the caller should update its stored offset
         if it differs from the value passed in).
    """
    if total_h <= view_h:
        return 0   # nothing to scroll — don't render the bar

    # Clamp incoming offset
    max_scroll = max(0, total_h - view_h)
    scroll_y   = max(0, min(max_scroll, scroll_y))

    # Track background
    pygame.draw.rect(ctx.screen, C_TINT_SHADOW, track_rect, border_radius=3)
    pygame.draw.rect(ctx.screen, C_BORDER_DIM,  track_rect, 1, border_radius=3)

    # Thumb size proportional to visible fraction, minimum 20px
    ratio    = view_h / total_h
    thumb_h  = max(20, int(track_rect.height * ratio))
    thumb_y  = track_rect.y + int((track_rect.height - thumb_h) * scroll_y / max_scroll)

    thumb = pygame.Rect(track_rect.x + 2, thumb_y, track_rect.width - 4, thumb_h)
    hovered = track_rect.collidepoint(ctx._mouse_pos)
    thumb_col = C_GREEN_MID if hovered else C_GREEN_DIM
    pygame.draw.rect(ctx.screen, thumb_col, thumb, border_radius=3)

    # Click anywhere on track: jump to that position
    def _jump():
        _, my = ctx._mouse_pos
        rel   = (my - track_rect.y) / track_rect.height
        on_scroll(int(rel * total_h - view_h / 2))

    ctx._click_regions.append((track_rect, _jump))
    return scroll_y


def draw_text_wrapped(surface: pygame.Surface, text: str, rect: pygame.Rect,
                      font: pygame.font.Font, color: tuple):
    """
    Render multi-line word-wrapped text inside a bounding rectangle.

    Parameters
    ----------
    surface : pygame.Surface  Target surface.
    text    : str             Text to wrap and render.
    rect    : Rect            Clipping region (text clips at rect.bottom).
    font    : Font            Font to use.
    color   : tuple           RGB text colour.
    """
    words = text.split()
    line  = ""
    y     = rect.y
    for word in words:
        test = line + (" " if line else "") + word
        if font.size(test)[0] <= rect.width:
            line = test
        else:
            if line:
                s = font.render(line, True, color)
                surface.blit(s, (rect.x, y))
                y += font.get_linesize()
                if y + font.get_linesize() > rect.bottom:
                    return
            line = word
    if line:
        s = font.render(line, True, color)
        surface.blit(s, (rect.x, y))
