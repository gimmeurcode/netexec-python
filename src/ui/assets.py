"""
assets.py — NETEXEC
====================
Procedural art generation for all card types and UI elements.

Every visual in this module is drawn from first principles using pygame.draw
primitives — no external image files are required. This means the game ships
as pure Python + pygame and can be packaged into a standalone executable
without a data/ art folder.

Card art catalogue
------------------
SITCOM   speech bubble + laugh lines
DRAMA    theatrical curtain + spotlight
SCIFI    rocket silhouette
REALITY  camera lens + record dot
SPORTS   trophy silhouette
NEWS     microphone + sound waves
COOKING  frying pan + steam wisps
STAR     5-point star polygon
AD       billboard rectangle + dollar sign
UPGRADE  gear / cog shape
EVENT    lightning bolt polygon
WILDCARD question mark in a decorative frame

UI art
------
VU meter      horizontal bar with gradient (green → amber → red)
Signal bars   stacked vertical bar chart
CRT scanlines horizontal dark-strip overlay
Blinking dot  filled circle that toggles
Genre badge   coloured pill with genre abbreviation text
"""

import math
import pygame
from engine.constants import (
    C_BG, C_GREEN_BRIGHT, C_GREEN_MID, C_GREEN_DIM,
    C_AMBER, C_RED, C_WHITE, C_BORDER,
    GENRE_COLORS, MIN_FONT_SIZE,
)
from .theme import C_TINT_PANEL_TITLE


def _try_svg_icon(surface: pygame.Surface, asset_name: str,
                  rect: pygame.Rect, color: tuple | None) -> bool:
    """Try to blit an SVG/PNG asset into rect.  Returns True on success."""
    try:
        from .assets_loader import get_asset
        surf = get_asset(asset_name, (rect.width, rect.height), color)
        surface.blit(surf, rect.topleft)
        return True
    except Exception:
        return False


# ─── GENRE ICON DISPATCH ──────────────────────────────────────────────────────

def draw_genre_icon(surface: pygame.Surface, genre: str, rect: pygame.Rect,
                    color: tuple = None):
    """
    Draw a genre icon that fits inside ``rect``.

    Tries the SVG asset (via assets_loader) first for pixel-perfect rendering
    at any size; falls back to the procedural shape when the asset is missing
    or pygame is not yet initialised for image loading.

    Parameters
    ----------
    surface : pygame.Surface  Destination surface.
    genre   : str             Genre key (SITCOM, DRAMA, SCIFI, REALITY, SPORTS, NEWS).
    rect    : pygame.Rect     Bounding box; icon is drawn centred inside it.
    color   : tuple           RGB tint; defaults to genre's text colour.
    """
    # Normalize genre: accept None or non-str values, use uppercase keys for lookups
    if not isinstance(genre, str):
        try:
            genre = str(genre)
        except Exception:
            genre = ""
    genre = (genre or "").upper().strip()

    col = color or GENRE_COLORS.get(genre, (C_GREEN_BRIGHT,))[0]

    # ── SVG / PNG via asset loader ────────────────────────────────────────────
    asset_name = f"genre-{genre.lower()}" if genre else "genre-unknown"
    if _try_svg_icon(surface, asset_name, rect, col):
        return

    # ── Procedural fallback ───────────────────────────────────────────────────
    cx = rect.centerx
    cy = rect.centery
    r  = min(rect.width, rect.height) // 2 - 2

    if genre == "SITCOM":
        _draw_speech_bubble(surface, cx, cy, r, col)
    elif genre == "DRAMA":
        _draw_curtain(surface, cx, cy, r, col)
    elif genre == "SCIFI":
        _draw_rocket(surface, cx, cy, r, col)
    elif genre == "REALITY":
        _draw_camera(surface, cx, cy, r, col)
    elif genre == "SPORTS":
        _draw_trophy(surface, cx, cy, r, col)
    elif genre == "NEWS":
        _draw_microphone(surface, cx, cy, r, col)
    elif genre == "COOKING":
        _draw_frying_pan(surface, cx, cy, r, col)
    else:
        _draw_question_mark(surface, cx, cy, r, col)


# ─── GENRE SHAPES ─────────────────────────────────────────────────────────────

def _draw_speech_bubble(surf, cx, cy, r, c):
    """SITCOM: speech bubble — wide oval body, tail, three dots."""
    bw  = int(r * 1.8)
    bh  = int(r * 1.1)
    ox  = cx - bw // 2
    oy  = cy - bh // 2 - r // 3
    # Bubble oval
    pygame.draw.ellipse(surf, c, (ox, oy, bw, bh), 2)
    # Tail: filled triangle from bubble bottom pointing down-left
    tail = [
        (cx - r // 4, oy + bh - 2),
        (cx - r // 2, cy + r // 2),
        (cx + r // 4, oy + bh - 2),
    ]
    pygame.draw.polygon(surf, c, tail)
    # Three dots inside bubble (sized to be visible at small icons)
    dot_r = max(2, r // 5)
    dot_y = oy + bh // 2 - 1
    for dx in (-bw // 4, 0, bw // 4):
        pygame.draw.circle(surf, c, (cx + dx, dot_y), dot_r)


def _draw_curtain(surf, cx, cy, r, c):
    """DRAMA: comedy/tragedy theater masks — the universal theater symbol."""
    mr  = max(4, int(r * 0.58))  # mask radius
    off = max(2, mr // 3)        # horizontal / vertical offset between mask centres
    # Tragedy mask (left/lower, frown = top arc ∩)
    tx, ty = cx - off, cy + off // 2
    pygame.draw.circle(surf, c, (tx, ty), mr, 2)
    pygame.draw.arc(surf, c,
                    (tx - mr * 3 // 4, ty - mr * 2 // 3,
                     mr * 3 // 2, mr * 2 // 3),
                    math.pi, math.pi * 2, 1)
    # Comedy mask (right/upper, smile = bottom arc U) — drawn second so it reads "in front"
    gx, gy = cx + off, cy - off // 2
    pygame.draw.circle(surf, c, (gx, gy), mr, 2)
    pygame.draw.arc(surf, c,
                    (gx - mr * 3 // 4, gy + mr // 3,
                     mr * 3 // 2, mr * 2 // 3),
                    0, math.pi, 1)


def _draw_rocket(surf, cx, cy, r, c):
    """SCIFI: rocket silhouette pointing upward."""
    hw = max(3, r // 2)           # half-body-width (wider than r//3 for better proportions)
    bh = int(r * 0.55)            # bottom of body (above exhaust)
    body = [
        (cx,        cy - r),      # nose tip
        (cx + hw,   cy - r // 4), # upper-right shoulder
        (cx + hw,   cy + bh),     # lower-right
        (cx - hw,   cy + bh),     # lower-left
        (cx - hw,   cy - r // 4), # upper-left shoulder
    ]
    pygame.draw.polygon(surf, c, body, 2)
    # Exhaust flame
    exhaust = [
        (cx - hw + 1, cy + bh),
        (cx,          cy + r),
        (cx + hw - 1, cy + bh),
    ]
    pygame.draw.polygon(surf, c, exhaust, 2)
    # Porthole
    pygame.draw.circle(surf, c, (cx, cy - r // 3), max(2, r // 4), 1)


def _draw_camera(surf, cx, cy, r, c):
    """REALITY: TV camera body with lens and record indicator."""
    # Camera body
    pygame.draw.rect(surf, c, (cx - r, cy - r // 2, r * 2, r), 2)
    # Lens
    pygame.draw.circle(surf, c, (cx, cy), r // 3, 2)
    # Record dot (top-right corner)
    pygame.draw.circle(surf, C_RED, (cx + r - 4, cy - r // 2 + 4), max(2, r // 6))
    # Viewfinder bump
    pygame.draw.rect(surf, c, (cx - r // 4, cy - r // 2 - r // 4, r // 2, r // 4), 1)


def _draw_trophy(surf, cx, cy, r, c):
    """SPORTS: classic trophy silhouette."""
    # Cup
    cup = [
        (cx - r // 2, cy - r),
        (cx + r // 2, cy - r),
        (cx + int(r * 0.6), cy - r // 3),
        (cx + r // 3,  cy + r // 4),
        (cx - r // 3,  cy + r // 4),
        (cx - int(r * 0.6), cy - r // 3),
    ]
    pygame.draw.polygon(surf, c, cup, 2)
    # Stem
    pygame.draw.rect(surf, c, (cx - 3, cy + r // 4, 6, r // 2), 1)
    # Base
    pygame.draw.rect(surf, c, (cx - r // 2, cy + int(r * 0.75), r, r // 5), 2)
    # Handles
    pygame.draw.arc(surf, c, (cx + r // 3, cy - r, r // 2, r // 2),
                    math.pi * 1.5, math.pi * 0.5, 2)
    pygame.draw.arc(surf, c, (cx - r // 3 - r // 2, cy - r, r // 2, r // 2),
                    math.pi * 0.5, math.pi * 1.5, 2)


def _draw_microphone(surf, cx, cy, r, c):
    """NEWS: upright microphone with sound waves."""
    mw = r * 2 // 3   # capsule width — integer (r // 1.5 gave float in Python 3)
    mh = int(r * 1.1)
    # Mic capsule
    pygame.draw.ellipse(surf, c, (cx - mw // 2, cy - r, mw, mh), 2)
    # Stand (starts at bottom of capsule, goes down then spreads into base)
    stand_y = cy - r + mh
    pygame.draw.line(surf, c, (cx, stand_y), (cx, cy + r // 2), 2)
    pygame.draw.line(surf, c,
                     (cx - r // 3, cy + r // 2),
                     (cx + r // 3, cy + r // 2), 2)
    # Sound waves (two arcs to the right of the capsule)
    for arc_r in (r // 2, int(r * 0.75)):
        pygame.draw.arc(surf, c,
                        (cx + mw // 2, cy - arc_r // 2, arc_r, arc_r),
                        -math.pi / 3, math.pi / 3, 1)


def _draw_frying_pan(surf, cx, cy, r, c):
    """COOKING: frying pan silhouette with handle and steam wisps."""
    # Pan body — circle shifted left to leave room for the handle
    pan_cx = cx - r // 4
    pan_r  = int(r * 0.62)
    pygame.draw.circle(surf, c, (pan_cx, cy), pan_r, 2)
    # Handle — horizontal bar extending right from the pan rim
    h_x1 = pan_cx + pan_r
    h_x2 = cx + r
    pygame.draw.line(surf, c, (h_x1, cy), (h_x2, cy), 3)
    pygame.draw.circle(surf, c, (h_x2, cy), 2)
    # Steam wisps — two small arcs rising above the pan centre
    for dx in (-pan_r // 3, pan_r // 3):
        wx = pan_cx + dx
        wy = cy - pan_r - r // 6
        pygame.draw.arc(surf, c, (wx - 3, wy - r // 4, 6, r // 4), 0, math.pi, 1)


def _draw_question_mark(surf, cx, cy, r, c):
    """Wildcard / Unknown: bold ? inside a diamond."""
    pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    pygame.draw.polygon(surf, c, pts, 2)


# ─── CARD TYPE ICONS ──────────────────────────────────────────────────────────

def draw_star_icon(surface: pygame.Surface, rect: pygame.Rect,
                   color: tuple = None, filled: bool = False):
    """
    Draw a 5-point star polygon centred in rect.

    Parameters
    ----------
    surface : pygame.Surface
    rect    : pygame.Rect
    color   : tuple  RGB colour (defaults to gold/amber).
    filled  : bool   If True draws a filled star; if False, outline only.
    """
    c = color or C_AMBER
    if _try_svg_icon(surface, "type-star", rect, c):
        return
    cx = rect.centerx
    cy = rect.centery
    r  = min(rect.width, rect.height) // 2 - 2
    pts = _star_points(cx, cy, r, r // 2, 5)
    pygame.draw.polygon(surface, c, pts, 0 if filled else 2)


def draw_ad_icon(surface: pygame.Surface, rect: pygame.Rect, color: tuple = None):
    """Draw an ad billboard icon."""
    c  = color or C_GREEN_MID
    if _try_svg_icon(surface, "type-ad", rect, c):
        return
    cx = rect.centerx
    cy = rect.centery
    w  = rect.width  - 4
    h  = rect.height - 4
    x  = rect.x + 2
    y  = rect.y + 2
    pygame.draw.rect(surface, c, (x, y, w, h), 2)
    post_h = h // 3
    pygame.draw.line(surface, c, (cx - w // 5, y + h), (cx - w // 5, y + h + post_h), 2)
    pygame.draw.line(surface, c, (cx + w // 5, y + h), (cx + w // 5, y + h + post_h), 2)
    try:
        f = pygame.font.SysFont("couriernew", max(MIN_FONT_SIZE, h // 2), bold=True)
        txt = f.render("$", True, c)
        surface.blit(txt, txt.get_rect(center=(cx, cy)))
    except Exception:
        pygame.draw.line(surface, c, (cx, y + 4), (cx, y + h - 4), 2)


def draw_upgrade_icon(surface: pygame.Surface, rect: pygame.Rect, color: tuple = None):
    """Draw a gear / cog icon for upgrades."""
    c  = color or C_GREEN_BRIGHT
    if _try_svg_icon(surface, "type-upgrade", rect, c):
        return
    cx = rect.centerx
    cy = rect.centery
    r  = min(rect.width, rect.height) // 2 - 3
    tooth_w = max(2, r // 4)
    tooth_h = max(3, r // 3)
    for i in range(8):
        angle = i * math.pi / 4
        tx = cx + int((r - tooth_h // 2) * math.cos(angle))
        ty = cy + int((r - tooth_h // 2) * math.sin(angle))
        tooth_rect = pygame.Rect(tx - tooth_w // 2, ty - tooth_h // 2, tooth_w, tooth_h)
        pygame.draw.rect(surface, c, tooth_rect)
    pygame.draw.circle(surface, c, (cx, cy), r, 2)
    pygame.draw.circle(surface, c, (cx, cy), max(2, r // 3), 2)


def draw_event_icon(surface: pygame.Surface, rect: pygame.Rect, color: tuple = None):
    """Draw a lightning bolt icon for one-off events."""
    c = color or C_AMBER
    if _try_svg_icon(surface, "type-event", rect, c):
        return
    cx = rect.centerx
    cy = rect.centery
    r  = min(rect.width, rect.height) // 2 - 2
    bolt = [
        (cx + r // 4, cy - r),
        (cx - r // 4, cy - r // 6),
        (cx + r // 4, cy - r // 6),
        (cx - r // 4, cy + r),
        (cx + r // 6, cy + r // 6),
        (cx - r // 6, cy + r // 6),
    ]
    pygame.draw.polygon(surface, c, bolt)


# ─── VU METER ─────────────────────────────────────────────────────────────────

def draw_vu_meter(surface: pygame.Surface, rect: pygame.Rect,
                  value: float, max_value: float,
                  label: str = "", show_label: bool = True):
    """
    Draw a horizontal VU-style signal bar (green → amber → red gradient).
    Used in the header to show view progress toward the milestone target.

    Parameters
    ----------
    surface   : pygame.Surface
    rect      : pygame.Rect     Bounding rectangle for the meter.
    value     : float           Current value (e.g. total_views).
    max_value : float           Target value (e.g. current_target_views).
    label     : str             Optional text label drawn left of the bar.
    show_label: bool            Whether to draw the label.
    """
    fill = min(1.0, value / max(1, max_value))
    bar_x, bar_y = rect.x, rect.y
    bar_w, bar_h = rect.width, rect.height

    # Background track
    pygame.draw.rect(surface, C_GREEN_DIM, rect, 0)
    pygame.draw.rect(surface, C_BORDER, rect, 1)

    # Filled portion — colour shifts green→amber→red as value approaches target
    if fill > 0:
        filled_w = max(2, int(bar_w * fill))
        if fill < 0.6:
            col = C_GREEN_BRIGHT
        elif fill < 0.85:
            col = C_AMBER
        else:
            col = C_RED
        pygame.draw.rect(surface, col, (bar_x, bar_y, filled_w, bar_h))
        # Bright leading edge
        pygame.draw.line(surface, C_WHITE,
                         (bar_x + filled_w - 1, bar_y),
                         (bar_x + filled_w - 1, bar_y + bar_h - 1))

    # Tick marks at 25%, 50%, 75%
    for frac in (0.25, 0.50, 0.75):
        tx = bar_x + int(bar_w * frac)
        pygame.draw.line(surface, C_GREEN_DIM, (tx, bar_y), (tx, bar_y + bar_h), 1)


# ─── SIGNAL BARS ──────────────────────────────────────────────────────────────

def draw_signal_bars(surface: pygame.Surface, x: int, y: int,
                     filled: int, total: int = 4,
                     color_on: tuple = None, color_off: tuple = None):
    """
    Draw N vertical signal-strength bars (like a phone's reception indicator).
    Used in time-slot cards to show how many shows are scheduled.

    Parameters
    ----------
    surface    : pygame.Surface
    x, y       : int  Top-left origin.
    filled     : int  Number of bars that are "on".
    total      : int  Total number of bars.
    color_on   : tuple  Colour for filled bars.
    color_off  : tuple  Colour for empty bars.
    """
    color_on  = color_on  or C_GREEN_BRIGHT
    color_off = color_off or C_GREEN_DIM
    bar_w     = 5
    gap       = 3
    max_h     = 20
    for i in range(total):
        bh  = max(4, int(max_h * (i + 1) / total))
        bx  = x + i * (bar_w + gap)
        by  = y + max_h - bh
        col = color_on if i < filled else color_off
        pygame.draw.rect(surface, col, (bx, by, bar_w, bh))


# ─── CRT OVERLAY ──────────────────────────────────────────────────────────────

_crt_cache: dict = {}


def draw_crt_scanlines(surface: pygame.Surface, alpha: int = 28, spacing: int = 4):
    """
    Draw horizontal scanline strips across the entire surface to simulate
    a CRT phosphor screen. Uses a transparent Surface blitted over the scene.

    Parameters
    ----------
    surface : pygame.Surface  Destination (the main screen).
    alpha   : int             Opacity of each dark strip (0–255).
    spacing : int             Pixels between strip tops (every Nth row is dark).
    """
    w, h = surface.get_size()
    key = (w, h, alpha, spacing)
    overlay = _crt_cache.get(key)
    if overlay is None:
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        strip = pygame.Surface((w, 2), pygame.SRCALPHA)
        strip.fill((0, 0, 0, alpha))
        for y in range(0, h, spacing):
            overlay.blit(strip, (0, y))
        _crt_cache.clear()
        _crt_cache[key] = overlay
    surface.blit(overlay, (0, 0))


# ─── GENRE BADGE ──────────────────────────────────────────────────────────────

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


# ─── BLINKING DOT ─────────────────────────────────────────────────────────────

def draw_blink_dot(surface: pygame.Surface, cx: int, cy: int, r: int,
                   color: tuple, tick_ms: int, period_ms: int = 700):
    """
    Draw a dot that blinks on/off based on the current game tick.

    Parameters
    ----------
    surface   : pygame.Surface
    cx, cy    : int   Centre coordinates.
    r         : int   Dot radius.
    color     : tuple RGB colour when visible.
    tick_ms   : int   pygame.time.get_ticks() — current clock.
    period_ms : int   Full on+off cycle duration in milliseconds.
    """
    on = (tick_ms % period_ms) < (period_ms // 2)
    if on:
        pygame.draw.circle(surface, color, (cx, cy), r)


# ─── NUMBER POP-UP ────────────────────────────────────────────────────────────

class NumberPop:
    """
    A floating +/- view or income number that rises and fades out.

    Instantiate with a value and position; call update(dt) each frame;
    render with draw(surface). Remove when is_done() returns True.
    """

    def __init__(self, value: int | float, x: int, y: int,
                 color: tuple = None, font: pygame.font.Font = None,
                 prefix: str = ""):
        """
        Parameters
        ----------
        value  : int or float  The number to display (positive or negative).
        x, y   : int           Starting centre position.
        color  : tuple         Text colour; defaults to amber for positive, red for negative.
        font   : pygame.font.Font  Rendering font.
        prefix : str           Optional prefix like '+' or '$'.
        """
        self.value    = value
        self.x        = float(x)
        self.y        = float(y)
        self.elapsed  = 0
        self.lifetime = 1400      # ms
        self.speed_y  = -60       # pixels/second (rises upward)
        self.font     = font
        sign          = "+" if value >= 0 else ""
        self.text     = f"{prefix}{sign}{int(value)}"
        if color is None:
            color = C_AMBER if value >= 0 else C_RED
        self.color = color

    def update(self, dt_ms: int):
        """Advance the pop-up animation by dt_ms milliseconds."""
        self.elapsed += dt_ms
        self.y       += self.speed_y * (dt_ms / 1000.0)

    def is_done(self) -> bool:
        """Return True when the pop-up has fully faded and should be removed."""
        return self.elapsed >= self.lifetime

    def draw(self, surface: pygame.Surface):
        """Render the pop-up at its current position with alpha fade."""
        if self.is_done():
            return
        alpha  = max(0, 255 - int(255 * (self.elapsed / self.lifetime)))
        if self.font is None:
            return
        try:
            txt = self.font.render(self.text, True, self.color)
            txt.set_alpha(alpha)
            surface.blit(txt, txt.get_rect(center=(int(self.x), int(self.y))))
        except Exception:
            pass


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _star_points(cx: int, cy: int, outer_r: int, inner_r: int, n: int) -> list:
    """
    Compute the vertices of an n-pointed star polygon.

    Parameters
    ----------
    cx, cy   : int  Centre.
    outer_r  : int  Outer (spike) radius.
    inner_r  : int  Inner (valley) radius.
    n        : int  Number of points.

    Returns
    -------
    list of (int, int)  Vertex coordinates.
    """
    pts   = []
    start = -math.pi / 2     # point upward
    for i in range(n * 2):
        r     = outer_r if i % 2 == 0 else inner_r
        angle = start + i * math.pi / n
        pts.append((cx + int(r * math.cos(angle)),
                    cy + int(r * math.sin(angle))))
    return pts


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
