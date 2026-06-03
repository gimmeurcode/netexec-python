"""
assets_loader.py — NETEXEC
===========================
Loads SVG / PNG icon assets and returns pygame Surfaces scaled to an exact
requested size.  Results are cached by (name, w, h, color) so repeated
lookups within a session are O(1).

Fallback chain
--------------
1. SVG loaded natively by pygame-ce (SDL2_image) after replacing currentColor
   with the requested tint.  This is pixel-perfect at any resolution and
   requires no native C library beyond SDL2_image (already bundled with
   pygame-ce).
2. PNG from assets/png/ — used if the SVG is missing.
3. Procedural pygame.draw fallback — calls the draw_* helpers in assets.py
   so the game always has a surface to blit.

SVG tinting
-----------
The design-system icons use ``currentColor`` for all strokes/fills.  Before
loading, this string is replaced with the hex value of the requested color
(default: C_GREEN_BRIGHT).  The modified SVG bytes are fed to
``pygame.image.load()`` via a ``BytesIO`` buffer so no temp file is written.

Asset root
----------
``src/assets/`` — one level above this file's ``ui/`` directory.
SVGs are resolved from ``assets/icons/``.

Usage
-----
    from ui.assets_loader import get_asset

    icon  = get_asset("genre-sitcom", (48, 48))
    badge = get_asset("type-star",    (16, 16), color=(255, 200, 50))
"""

from __future__ import annotations

import io
import pathlib

import pygame

from engine.constants import C_GREEN_BRIGHT
from .assets import (
    draw_genre_icon,
    draw_star_icon,
    draw_ad_icon,
    draw_upgrade_icon,
    draw_event_icon,
)

# Asset root: src/assets/
# __file__ sits at src/ui/assets_loader.py
#   parents[0] → src/ui/
#   parents[1] → src/
_ASSET_ROOT = pathlib.Path(__file__).resolve().parents[1] / "assets"
_SVG_DIR    = _ASSET_ROOT / "icons"
_PNG_DIR    = _ASSET_ROOT / "png"

# In-process surface cache — keyed by (name, width, height, color)
_cache: dict[tuple, pygame.Surface] = {}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _rgb_to_css(color: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*color)


def _svg_path(name: str) -> pathlib.Path | None:
    """Return the SVG path for ``name`` if it exists, or None."""
    p = _SVG_DIR / f"{name}.svg"
    return p if p.exists() else None


def _load_svg(name: str, w: int, h: int,
              color: tuple[int, int, int] | None) -> pygame.Surface | None:
    """
    Rasterize an SVG using pygame-ce's native SDL2_image SVG support.

    The icon's ``currentColor`` token is replaced with the requested tint
    before loading so the design-system single-color icons pick up the
    game's palette at any size.
    """
    svg_path = _svg_path(name)
    if svg_path is None:
        return None
    try:
        src = svg_path.read_text(encoding="utf-8")
        css = _rgb_to_css(color if color is not None else C_GREEN_BRIGHT)
        src = src.replace("currentColor", css)
        buf = io.BytesIO(src.encode("utf-8"))
        # pygame-ce loads SVG from a file-like object; the .svg name hint
        # ensures SDL2_image selects the SVG decoder.
        raw = pygame.image.load(buf, f"{name}.svg").convert_alpha()
        if raw.get_size() == (w, h):
            return raw
        return pygame.transform.smoothscale(raw, (w, h))
    except Exception:
        return None


def _load_png(name: str, w: int, h: int) -> pygame.Surface | None:
    png_path = _PNG_DIR / f"{name}.png"
    if not png_path.exists():
        return None
    try:
        surf = pygame.image.load(str(png_path)).convert_alpha()
        return pygame.transform.smoothscale(surf, (w, h))
    except Exception:
        return None


def _procedural(name: str, w: int, h: int,
                color: tuple[int, int, int] | None) -> pygame.Surface:
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    rect = pygame.Rect(0, 0, w, h)

    if name.startswith("genre-"):
        genre = name[6:].upper()
        draw_genre_icon(surf, genre, rect, color)
    else:
        dispatch = {
            "type-star":     draw_star_icon,
            "type-ad":       draw_ad_icon,
            "type-upgrade":  draw_upgrade_icon,
            "type-event":    draw_event_icon,
            "type-wildcard": lambda s, r, c: draw_genre_icon(s, "WILDCARD", r, c),
        }
        fn = dispatch.get(name)
        if fn is not None:
            fn(surf, rect, color)

    return surf


# ── Public API ─────────────────────────────────────────────────────────────────

def get_asset(name: str, size: tuple[int, int],
              color: tuple[int, int, int] | None = None) -> pygame.Surface:
    """
    Return a pygame Surface of the named icon at the requested pixel size.

    Parameters
    ----------
    name  : str            Asset stem without extension (e.g. "genre-sitcom").
    size  : (int, int)     Exact (width, height) in pixels.
    color : tuple | None   RGB tint substituted for currentColor in SVGs and
                           forwarded to procedural draw helpers.
                           Defaults to C_GREEN_BRIGHT.

    Returns
    -------
    pygame.Surface  Always valid — never raises.
    """
    w, h = size
    key  = (name, w, h, color)
    if key in _cache:
        return _cache[key]

    surf = (
        _load_svg(name, w, h, color)
        or _load_png(name, w, h)
        or _procedural(name, w, h, color)
    )
    _cache[key] = surf
    return surf


def clear_cache() -> None:
    """Discard all cached surfaces (call on display mode change or window resize)."""
    _cache.clear()
