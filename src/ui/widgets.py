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
  line_step            Minimum safe vertical step between two lines of a font.
  draw_row             Draw a run of coloured text segments on one line.
  draw_kv              Draw a label/value pair with collision-free spacing.
  draw_button          Draw a CRT-style button and register its click region.
  draw_modal_overlay   Draw a semi-transparent darkening layer for modals.
  draw_label           Draw a plain text label.
  draw_slider          Draw a horizontal slider with drag interaction.
  draw_text_wrapped    Render word-wrapped text inside a bounding rect.
"""

import pygame

from engine.constants import (
    C_BG, C_GREEN_BRIGHT, C_GREEN_MID, C_GREEN_DIM, C_GREEN_PANEL,
    C_WHITE, C_BORDER, C_BORDER_DIM, GENRE_COLORS,
)
from .theme import C_TINT_BTN_HOVER, C_TINT_SHADOW, C_TINT_PANEL_TITLE


def line_step(font: pygame.font.Font, scale: float = 1.0) -> int:
    """
    Return the minimum safe vertical distance between two consecutive lines
    of ``font``.

    This is the font's true rendered line height (``get_linesize``) scaled by
    ``scale``. Use it instead of a hardcoded ``y += N`` so stacked rows can
    never collide regardless of the font role in play.
    """
    return int(font.get_linesize() * scale)


def draw_row(ctx, segments, x: int, y: int, font: pygame.font.Font,
             gap: int = 6) -> int:
    """
    Draw a horizontal run of coloured text segments on a single line.

    Parameters
    ----------
    ctx      : GameUI  Controller instance (provides ``ctx.screen``).
    segments : list of (text, color) tuples  Drawn left-to-right.
    x, y     : int     Top-left origin of the run.
    font     : Font    Font used for every segment.
    gap      : int     Pixel gap inserted after each segment.

    Each segment is rendered immediately after the previous one, advancing the
    pen by ``font.size(text)[0] + gap`` so two segments can never share pixels.

    Returns
    -------
    int  The x position just past the last segment (its right edge + gap).
    """
    cx = x
    for text, color in segments:
        surf = font.render(text, True, color)
        ctx.screen.blit(surf, (cx, y))
        cx += font.size(text)[0] + gap
    return cx


def draw_kv(ctx, label: str, value: str, x: int, y: int,
            font: pygame.font.Font, label_color, value_color,
            col_w=None, gap: int = 10) -> int:
    """
    Draw a ``label``/``value`` pair so the value can never overlap the label.

    The value is placed at ``x + max(col_w or 0, font.size(label)[0] + gap)``,
    i.e. at a fixed column when ``col_w`` is supplied, but always pushed past a
    label that is wider than that column. Use a ``col_w`` equal to the widest
    label in a group to get clean aligned columns.

    Returns
    -------
    int  ``y + line_step(font)`` so callers can chain successive rows.
    """
    ctx.screen.blit(font.render(label, True, label_color), (x, y))
    vx = x + max(col_w or 0, font.size(label)[0] + gap)
    ctx.screen.blit(font.render(value, True, value_color), (vx, y))
    return y + line_step(font)


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

    _font  = ctx._f("small")
    _label = label
    _max_w = max(0, rect.width - 8)   # 4 px padding each side
    while _label and _font.size(_label)[0] > _max_w:
        _label = _label[:-1]
    if _label != label:
        # Trim one more char to fit the ellipsis
        while _label and _font.size(_label + "…")[0] > _max_w:
            _label = _label[:-1]
        _label = _label + "…"
    txt = _font.render(_label, True, tc)
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


def slider_value_at(rect: pygame.Rect, mouse_x: int) -> float:
    """Return the [0,1] slider value for a mouse x within ``rect``."""
    return max(0.0, min(1.0, (mouse_x - rect.x) / max(1, rect.width)))


def draw_slider(ctx, rect: pygame.Rect, value: float, on_change):
    """
    Draw a horizontal slider and register a region the controller drives by
    click (jump), drag (slide) and mouse wheel (nudge).

    Parameters
    ----------
    ctx       : GameUI  Controller instance.
    rect      : Rect    Slider bounding box.
    value     : float   Current value in [0.0, 1.0].
    on_change : callable  Called with the new float value (0..1).
    """
    value = max(0.0, min(1.0, value))
    dragging = (getattr(ctx, "_slider_drag", None) is not None
                and ctx._slider_drag.get("rect") == rect)
    hovered  = rect.collidepoint(ctx._mouse_pos) or dragging

    pygame.draw.rect(ctx.screen, C_GREEN_DIM, rect)
    pygame.draw.rect(ctx.screen, C_GREEN_BRIGHT if hovered else C_BORDER, rect, 1)
    filled_w = int(rect.width * value)
    if filled_w > 0:
        pygame.draw.rect(ctx.screen, C_GREEN_BRIGHT,
                         (rect.x, rect.y, filled_w, rect.height))
    hx = rect.x + filled_w
    knob = (255, 255, 255) if not dragging else C_GREEN_BRIGHT
    pygame.draw.rect(ctx.screen, knob, (hx - 3, rect.y - 2, 6, rect.height + 4))

    # Register for the controller's click/drag/wheel handling.
    ctx._slider_regions.append({"rect": pygame.Rect(rect), "set": on_change,
                                "value": value})


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

    # ── Up / down arrow buttons at the track ends ────────────────────────────
    arrow_h   = min(14, max(8, track_rect.height // 6))
    up_rect   = pygame.Rect(track_rect.x, track_rect.y, track_rect.width, arrow_h)
    down_rect = pygame.Rect(track_rect.x, track_rect.bottom - arrow_h,
                            track_rect.width, arrow_h)
    inner = pygame.Rect(track_rect.x, track_rect.y + arrow_h,
                        track_rect.width, track_rect.height - arrow_h * 2)

    # Track background (inner channel)
    pygame.draw.rect(ctx.screen, C_TINT_SHADOW, inner, border_radius=3)
    pygame.draw.rect(ctx.screen, C_BORDER_DIM,  inner, 1, border_radius=3)

    # Thumb size proportional to visible fraction, minimum 20px
    ratio    = view_h / total_h
    thumb_h  = max(20, int(inner.height * ratio))
    thumb_h  = min(thumb_h, inner.height)
    travel   = inner.height - thumb_h
    thumb_y  = inner.y + int(travel * scroll_y / max_scroll) if max_scroll else inner.y

    thumb = pygame.Rect(inner.x + 1, thumb_y, inner.width - 2, thumb_h)
    mpos  = ctx._mouse_pos
    dragging = (getattr(ctx, "_sb_drag", None) is not None
                and ctx._sb_drag.get("track") == inner)
    hovered  = inner.collidepoint(mpos) or dragging
    thumb_col = C_GREEN_BRIGHT if dragging else (C_GREEN_MID if hovered else C_GREEN_DIM)
    pygame.draw.rect(ctx.screen, thumb_col, thumb, border_radius=3)

    # Arrow glyphs
    for arr, pts_fn in (
        (up_rect,   lambda r: [(r.centerx, r.y + 3),
                               (r.x + 3, r.bottom - 3), (r.right - 3, r.bottom - 3)]),
        (down_rect, lambda r: [(r.centerx, r.bottom - 3),
                               (r.x + 3, r.y + 3), (r.right - 3, r.y + 3)]),
    ):
        a_hot = arr.collidepoint(mpos)
        pygame.draw.rect(ctx.screen, C_TINT_SHADOW, arr, border_radius=2)
        pygame.draw.polygon(ctx.screen, C_GREEN_MID if a_hot else C_GREEN_DIM, pts_fn(arr))

    # Register a structured region so ui.py can handle press / drag / arrows.
    step = max(view_h // 4, 24)
    ctx._scrollbar_regions.append({
        "track": inner, "thumb": thumb, "up": up_rect, "down": down_rect,
        "total_h": total_h, "view_h": view_h, "max_scroll": max_scroll,
        "scroll": scroll_y, "thumb_h": thumb_h, "step": step, "set": on_scroll,
    })
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


def draw_genre_badge(surface: pygame.Surface, genre: str,
                     x: int, y: int, font: pygame.font.Font) -> pygame.Rect:
    """
    Draw a small coloured genre pill badge (e.g. [DRAMA] in purple).

    Parameters
    ----------
    surface : pygame.Surface
    genre   : str             Genre key.
    x, y    : int             Top-left position.
    font    : pygame.font.Font  Small font for the badge label.

    Returns
    -------
    pygame.Rect  Bounding rect of the drawn badge (for layout purposes).
    """
    text_col, bg_col = GENRE_COLORS.get(genre, (C_GREEN_BRIGHT, C_GREEN_DIM))
    label    = genre[:4]          # abbreviate to 4 chars: SITC DRAM SCIF REAL SPOR NEWS
    txt_surf = font.render(label, True, text_col)
    pad      = 4
    badge_w  = txt_surf.get_width()  + pad * 2
    badge_h  = txt_surf.get_height() + 2

    badge_rect = pygame.Rect(x, y, badge_w, badge_h)
    pygame.draw.rect(surface, bg_col, badge_rect, border_radius=3)
    pygame.draw.rect(surface, text_col, badge_rect, 1, border_radius=3)
    surface.blit(txt_surf, (x + pad, y + 1))
    return badge_rect


def draw_panel_box(surface: pygame.Surface, rect: pygame.Rect,
                   border_color: tuple = None, bg_color: tuple = None,
                   title: str = "", title_font: pygame.font.Font = None,
                   title_color: tuple = None, border_radius: int = 4):
    """
    Draw a standard retro panel box: filled background + border + optional title bar.

    Parameters
    ----------
    surface      : pygame.Surface
    rect         : pygame.Rect  Panel bounding box.
    border_color : tuple        Border RGB (defaults to C_BORDER).
    bg_color     : tuple        Fill RGB (defaults to C_BG).
    title        : str          Optional title string drawn at the top of the panel.
    title_font   : Font         Font for the title text.
    title_color  : tuple        Title text colour (defaults to C_GREEN_BRIGHT).
    border_radius: int          Corner radius in pixels.
    """
    bg_color     = bg_color     or C_BG
    border_color = border_color or C_BORDER
    title_color  = title_color  or C_GREEN_BRIGHT

    pygame.draw.rect(surface, bg_color,     rect, border_radius=border_radius)
    pygame.draw.rect(surface, border_color, rect, 1, border_radius=border_radius)

    if title and title_font:
        # Shaded title bar across the top of the panel
        th = title_font.get_linesize() + 6
        title_bar = pygame.Rect(rect.x + 1, rect.y + 1, rect.width - 2, th)
        pygame.draw.rect(surface, C_TINT_PANEL_TITLE, title_bar, border_radius=border_radius - 1)
        # Accent separator line below title bar
        sep_y = rect.y + th + 1
        pygame.draw.line(surface, border_color, (rect.x + 1, sep_y), (rect.right - 1, sep_y))
        txt = title_font.render(title, True, title_color)
        surface.blit(txt, (rect.x + 8, rect.y + 4))
