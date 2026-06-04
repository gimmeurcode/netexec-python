"""
tutorial.py — NETEXEC
======================
Step-by-step tutorial system for first-time players.

Each step dims the entire screen, draws a spotlight highlight around the
relevant panel, shows a scrollable instruction popup, and provides Next,
Back, and Skip buttons.

Steps advance automatically when the player performs the expected action,
or manually via the buttons.  The tutorial fully blocks background clicks
while open.

Adding new steps
----------------
Append a dict to STEPS below.  No Python code changes required.

Each step dict:
  title     (str)       Short bold header.
  body      (str)       Explanation text (word-wrapped automatically).
  highlight (str|None)  Panel region to spotlight: 'shop', 'left', 'header'.
  tab       (str|None)  Shop tab to switch to on advance: 'shows', etc.
  trigger   (str|None)  Game event that auto-advances this step.
"""

import pygame
from engine.constants import (
    C_BG, C_GREEN_BRIGHT, C_GREEN_MID, C_GREEN_DIM,
    C_AMBER, C_WHITE, C_CYAN, C_BORDER,
    SCREEN_WIDTH, SCREEN_HEIGHT,
)

# ─── TUTORIAL STEPS DATA ──────────────────────────────────────────────────────

STEPS = [
    # ── 0 — WELCOME ────────────────────────────────────────────────────────────
    {
        "title":     "WELCOME, EXECUTIVE",
        "body": (
            "You run a TV network. Fill the four time slots with shows and hit "
            "each milestone's VIEWS QUOTA to survive all 12 seasons. Miss a quota "
            "and you're iced; clear them all and you win."
        ),
        "highlight": None,
        "tab":       None,
        "trigger":   None,
    },
    # ── 1 — THE SHOP ───────────────────────────────────────────────────────────
    {
        "title":     "THE SHOP",
        "body": (
            "The ACQUISITION TERMINAL on the right is where you BUY shows, stars, "
            "ads, upgrades and events, and ACCEPT contracts — switch tabs along the "
            "top. * REROLL draws a fresh pool for a small fee."
        ),
        "highlight": "shop",
        "tab":       None,
        "trigger":   None,
    },
    # ── 2 — THE SCHEDULE ───────────────────────────────────────────────────────
    {
        "title":     "THE SCHEDULE",
        "body": (
            "Click BUY on a show, then click an empty slot on the left to place it. "
            "Each slot grants a different bonus, and a show's card lists its best "
            "slots. Attach stars/ads, SELL, or VAULT shows from here."
        ),
        "highlight": "left",
        "tab":       "shows",
        "trigger":   "place",
    },
    # ── 3 — AIR IT ─────────────────────────────────────────────────────────────
    {
        "title":     "AIR IT",
        "body": (
            "When your lineup is set, hit >> AIR SEASON in the header to tally "
            "views and income. Full mechanics — slot bonuses, every genre's "
            "monopoly, stars, ads, upgrades, events, contracts, the vault and "
            "bailouts — are in SETTINGS - RULES any time."
        ),
        "highlight": "header",
        "tab":       None,
        "trigger":   "season",
    },
]


# ─── TUTORIAL CONTROLLER ──────────────────────────────────────────────────────

class TutorialController:
    """
    Manages tutorial step progression and overlay rendering.

    The popup body is fully scrollable: mouse wheel and the ▲/▼ buttons
    in the popup scroll through text that doesn't fit in one view.
    """

    POPUP_W  = 580
    POPUP_H  = 300   # tall enough for most steps; body area scrolls for overflow
    _SCROLL_SPEED = 18   # pixels per wheel tick

    def __init__(self):
        self.step      = 0
        self.done      = False
        self._elapsed  = 0
        self._scroll   = 0       # body scroll offset in pixels
        self._max_scroll = 0     # updated every draw(); used to clamp scroll
        self._last_sw  = SCREEN_WIDTH
        self._last_sh  = SCREEN_HEIGHT

    def update(self, dt_ms: int):
        self._elapsed += dt_ms

    def advance(self, state=None):
        self.step      += 1
        self._elapsed   = 0
        self._scroll    = 0
        self._max_scroll = 0
        if self.step >= len(STEPS):
            self.done = True
        elif state is not None:
            tab = STEPS[self.step].get("tab")
            if tab:
                state.set_tab(tab)

    def back(self):
        if self.step > 0:
            self.step    -= 1
            self._elapsed = 0
            self._scroll  = 0
            self._max_scroll = 0

    def skip(self):
        self.done = True

    def scroll(self, delta: int):
        """Scroll the body by delta pixels (positive = scroll down)."""
        self._scroll = max(0, min(self._max_scroll, self._scroll + delta))

    def notify(self, event_type: str):
        """Auto-advance if the current step has a matching trigger."""
        if self.done:
            return
        current = STEPS[self.step] if self.step < len(STEPS) else None
        if current and current.get("trigger") == event_type:
            self.advance()

    # ── Body area geometry constants ──────────────────────────────────────────
    _HEADER_H = 48   # space for step counter + title
    _FOOTER_H = 38   # space for buttons

    def _body_rect(self, popup_rect: pygame.Rect) -> pygame.Rect:
        return pygame.Rect(
            popup_rect.x + 12,
            popup_rect.y + self._HEADER_H,
            self.POPUP_W - 24,
            self.POPUP_H - self._HEADER_H - self._FOOTER_H,
        )

    def draw(self, surface: pygame.Surface, fonts: dict):
        """Render the tutorial overlay: dim + spotlight + scrollable popup."""
        if self.done or self.step >= len(STEPS):
            return

        step_data = STEPS[self.step]
        alpha = min(255, int(255 * self._elapsed / 300))

        sw = surface.get_width()
        sh = surface.get_height()
        self._last_sw = sw
        self._last_sh = sh

        highlight = step_data.get("highlight")

        # ── Full-screen dim overlay ───────────────────────────────────────────
        dim = pygame.Surface((sw, sh), pygame.SRCALPHA)
        dim.fill((0, 0, 0, min(170, int(170 * alpha / 255))))
        surface.blit(dim, (0, 0))

        # ── Spotlight cutout for highlighted panel ────────────────────────────
        if highlight:
            self._draw_spotlight(surface, highlight, alpha, sw, sh)

        # ── Popup plate ───────────────────────────────────────────────────────
        cx      = sw // 2
        popup_y = sh - self.POPUP_H - 20
        popup_rect = pygame.Rect(cx - self.POPUP_W // 2, popup_y,
                                 self.POPUP_W, self.POPUP_H)

        bg = pygame.Surface((self.POPUP_W, self.POPUP_H), pygame.SRCALPHA)
        bg.fill((0, 14, 4, min(235, alpha)))
        surface.blit(bg, popup_rect.topleft)

        border_col = (*self._lerp_col((0, 100, 200), (80, 220, 200),
                                       self._elapsed / 500), alpha)
        border_s = pygame.Surface((self.POPUP_W, self.POPUP_H), pygame.SRCALPHA)
        pygame.draw.rect(border_s, border_col,
                         (0, 0, self.POPUP_W, self.POPUP_H), 2, border_radius=6)
        surface.blit(border_s, popup_rect.topleft)

        # Top accent bar
        acc_s = pygame.Surface((self.POPUP_W - 2, 3), pygame.SRCALPHA)
        acc_s.fill((*C_CYAN, min(200, alpha)))
        surface.blit(acc_s, (popup_rect.x + 1, popup_rect.y + 2))

        # Step counter + title
        f_mi   = fonts.get("micro", fonts.get("body"))
        f_bold = fonts.get("bold",  fonts.get("body"))
        f_sm   = fonts.get("small", fonts.get("body"))

        step_str  = f"TUTORIAL  {self.step + 1} / {len(STEPS)}"
        step_surf = f_mi.render(step_str, True, C_CYAN)
        step_surf.set_alpha(alpha)
        surface.blit(step_surf, (popup_rect.x + 12, popup_rect.y + 7))

        t_surf = f_bold.render(step_data["title"], True, C_CYAN)
        t_surf.set_alpha(alpha)
        surface.blit(t_surf, (popup_rect.x + 12, popup_rect.y + 20))

        # ── Scrollable body area ──────────────────────────────────────────────
        body_rect = self._body_rect(popup_rect)
        all_lines = self._wrap_text(step_data["body"], f_sm, body_rect.width)
        lh        = f_sm.get_linesize()
        content_h = len(all_lines) * lh

        self._max_scroll = max(0, content_h - body_rect.height)
        self._scroll     = max(0, min(self._max_scroll, self._scroll))

        old_clip = surface.get_clip()
        surface.set_clip(body_rect)

        y = body_rect.y - self._scroll
        for line_text in all_lines:
            if y + lh >= body_rect.y and y < body_rect.bottom:
                s = f_sm.render(line_text, True, C_WHITE)
                s.set_alpha(alpha)
                surface.blit(s, (body_rect.x, y))
            y += lh

        surface.set_clip(old_clip)

        # ── Scrollbar (right edge of body area) ──────────────────────────────
        if self._max_scroll > 0:
            sb_x = body_rect.right + 2
            sb_y = body_rect.y
            sb_h = body_rect.height
            pygame.draw.rect(surface, C_GREEN_DIM,
                             pygame.Rect(sb_x, sb_y, 4, sb_h), border_radius=2)
            thumb_h = max(14, int(sb_h * body_rect.height / content_h))
            scroll_frac = self._scroll / self._max_scroll
            thumb_y = sb_y + int((sb_h - thumb_h) * scroll_frac)
            pygame.draw.rect(surface, C_CYAN,
                             pygame.Rect(sb_x, thumb_y, 4, thumb_h), border_radius=2)

            # "▼ SCROLL" hint at bottom of body when there is more text below
            if self._scroll < self._max_scroll:
                hint = f_mi.render("▼  MORE", True, C_CYAN)
                hint.set_alpha(min(alpha, 140))
                surface.blit(hint, (body_rect.right - hint.get_width() - 8,
                                    body_rect.bottom - f_mi.get_linesize() - 2))

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_y      = popup_rect.bottom - 30
        next_rect  = pygame.Rect(popup_rect.right - 114, btn_y, 104, 24)
        skip_rect  = pygame.Rect(popup_rect.x + 10,      btn_y,  84, 24)
        back_rect  = pygame.Rect(popup_rect.x + 104,     btn_y,  80, 24)

        self._draw_tut_btn(surface, next_rect,
                           "NEXT  >" if self.step < len(STEPS) - 1 else "FINISH",
                           C_CYAN, fonts, alpha)
        self._draw_tut_btn(surface, skip_rect, "SKIP", C_GREEN_DIM, fonts, alpha)
        if self.step > 0:
            self._draw_tut_btn(surface, back_rect, "< BACK", C_GREEN_MID, fonts, alpha)

    def get_click_regions(self, fonts: dict, state=None) -> list:
        """Return click regions for tutorial buttons this frame."""
        if self.done or self.step >= len(STEPS):
            return []

        sw = getattr(self, "_last_sw", SCREEN_WIDTH)
        sh = getattr(self, "_last_sh", SCREEN_HEIGHT)
        cx = sw // 2
        popup_y    = sh - self.POPUP_H - 20
        popup_rect = pygame.Rect(cx - self.POPUP_W // 2, popup_y,
                                 self.POPUP_W, self.POPUP_H)
        btn_y = popup_rect.bottom - 30

        next_rect = pygame.Rect(popup_rect.right - 114, btn_y, 104, 24)
        skip_rect = pygame.Rect(popup_rect.x + 10,      btn_y,  84, 24)
        back_rect = pygame.Rect(popup_rect.x + 104,     btn_y,  80, 24)

        regions = [
            (next_rect, lambda s=state: self.advance(s)),
            (skip_rect, self.skip),
        ]
        if self.step > 0:
            regions.append((back_rect, self.back))
        return regions

    # ─── PRIVATE HELPERS ──────────────────────────────────────────────────────

    @staticmethod
    def _wrap_text(text: str, font: pygame.font.Font, max_w: int) -> list:
        """Return a list of word-wrapped line strings fitting within max_w pixels."""
        words = text.split()
        lines = []
        line  = ""
        for word in words:
            test = line + (" " if line else "") + word
            if font.size(test)[0] <= max_w:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
        return lines

    def _draw_spotlight(self, surface: pygame.Surface, panel: str,
                        alpha: int, sw: int, sh: int):
        from ui.layout import _PAD, _HUD_FRAC, _HUD_MIN, _HUD_MAX, _SPLIT
        hud_h   = max(_HUD_MIN, min(_HUD_MAX, int(sh * _HUD_FRAC)))
        left_w  = max(380, int(sw * _SPLIT))
        right_w = max(380, sw - left_w - _PAD)
        right_x = left_w + _PAD
        stage_y = hud_h + _PAD
        stage_h = max(1, sh - stage_y - _PAD)

        rects = {
            "header": pygame.Rect(0,              0,       sw,                hud_h),
            "left":   pygame.Rect(_PAD,            stage_y, left_w  - _PAD*2, stage_h),
            "shop":   pygame.Rect(right_x + _PAD,  stage_y, right_w - _PAD*2, stage_h),
        }
        rect = rects.get(panel)
        if not rect:
            return

        pad    = 4
        bright = pygame.Rect(rect.x - pad, rect.y - pad,
                             rect.width + pad * 2, rect.height + pad * 2)
        clear  = pygame.Surface((bright.width, bright.height), pygame.SRCALPHA)
        clear.fill((0, 0, 0, max(0, min(170, int(170 * alpha / 255)) - 60)))
        surface.blit(clear, bright.topleft, special_flags=pygame.BLEND_RGBA_SUB)

        glow_a = min(200, alpha)
        glow   = pygame.Surface((bright.width + 8, bright.height + 8), pygame.SRCALPHA)
        pygame.draw.rect(glow, (80, 220, 200, glow_a // 2),
                         (0, 0, bright.width + 8, bright.height + 8),
                         4, border_radius=8)
        surface.blit(glow, (bright.x - 4, bright.y - 4))
        pygame.draw.rect(surface, (80, 220, 200),
                         pygame.Rect(bright.x, bright.y, bright.width, bright.height),
                         2, border_radius=6)

    def _draw_tut_btn(self, surface: pygame.Surface, rect: pygame.Rect,
                      label: str, color: tuple, fonts: dict, alpha: int):
        bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        bg.fill((0, 22, 10, min(210, alpha)))
        surface.blit(bg, rect.topleft)
        border_s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(border_s, (*color, alpha),
                         (0, 0, rect.width, rect.height), 1, border_radius=3)
        surface.blit(border_s, rect.topleft)
        f   = fonts.get("small", fonts.get("body"))
        txt = f.render(label, True, color)
        txt.set_alpha(alpha)
        surface.blit(txt, txt.get_rect(center=rect.center))

    @staticmethod
    def _lerp_col(a: tuple, b: tuple, t: float) -> tuple:
        t = max(0.0, min(1.0, t))
        return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
