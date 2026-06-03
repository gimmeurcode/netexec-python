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
    # ── 0 ─────────────────────────────────────────────────────────────────────
    {
        "title":     "WELCOME, EXECUTIVE",
        "body": (
            "You run a TV network. Your goal: hit the VIEWS QUOTA every 3 seasons "
            "for 12 seasons without running out of budget. "
            "Miss a quota and you are iced. Hit all four and you win. "
            "The board is watching."
        ),
        "highlight": None,
        "tab":       None,
        "trigger":   None,
    },
    # ── 1 ─────────────────────────────────────────────────────────────────────
    {
        "title":     "YOUR BUDGET",
        "body": (
            "The number at the top-right is your BUDGET (in dollars). "
            "Every show you schedule costs UPKEEP each season. "
            "Stars and Ads add costs or bonuses on top of that. "
            "Run out of budget and your shows still air — "
            "but you can't buy new ones. Keep an eye on the projected end-of-season "
            "budget shown in the header."
        ),
        "highlight": "header",
        "tab":       None,
        "trigger":   None,
    },
    # ── 2 ─────────────────────────────────────────────────────────────────────
    {
        "title":     "THE SHOP (RIGHT PANEL)",
        "body": (
            "The right panel is your ACQUISITION TERMINAL. "
            "Tabs: SHOWS, STARS, ADS, UPGRADES, EVENTS, CONTRACTS. "
            "Click REROLL to draw fresh items — it costs a small fee that "
            "rises slightly with each use, resetting at the start of every season. "
            "The item pool also refills automatically each new season."
        ),
        "highlight": "shop",
        "tab":       None,
        "trigger":   None,
    },
    # ── 3 ─────────────────────────────────────────────────────────────────────
    {
        "title":     "BUYING & PLACING A SHOW",
        "body": (
            "Click BUY on a SHOW card to queue it, then click an empty time-slot "
            "on the left to place it. "
            "Each show lists BASE VIEWS, UPKEEP, STAR SLOTS, and AD SLOTS. "
            "2-SLOT shows occupy two adjacent positions for a large view bonus — "
            "but use two lineup spots. "
            "To remove a show, click SELL — you receive a partial refund based on "
            "the show's cost and any attached stars."
        ),
        "highlight": "left",
        "tab":       "shows",
        "trigger":   "place",
    },
    # ── 4 ─────────────────────────────────────────────────────────────────────
    {
        "title":     "WILDCARD SHOWS & ADS",
        "body": (
            "Each shop cycle includes one WILDCARD SHOW and one WILDCARD AD "
            "(shown in cyan). Buying a wildcard opens a 3-step configurator: "
            "Step 1 — enter a name (or leave blank for ???); "
            "Step 2 — choose one of three offered genres; "
            "Step 3 — choose one of three generated abilities with different "
            "view, income, or other effects. Then place it like any regular show."
        ),
        "highlight": "shop",
        "tab":       "shows",
        "trigger":   None,
    },
    # ── 5 ─────────────────────────────────────────────────────────────────────
    {
        "title":     "TIME SLOT ABILITIES",
        "body": (
            "Each of the four time slots has a passive bonus shown on its header bar. "
            "MORNING boosts ad income earned by the show in that slot. "
            "AFTERNOON raises the show's base views. "
            "PRIME TIME amplifies the bonus portion of star view multipliers — "
            "great for high-multiplier stars. "
            "LATE NIGHT cuts upkeep costs for that show. "
            "Hover any slot header to see the exact bonus values and a full description."
        ),
        "highlight": "left",
        "tab":       None,
        "trigger":   None,
    },
    # ── 6 ─────────────────────────────────────────────────────────────────────
    {
        "title":     "SLOT PENALTY",
        "body": (
            "Every show lists RECOMMENDED SLOTS on its card (REC: ...). "
            "Placing a show outside all its recommended slots applies a "
            "significant view penalty for that season. "
            "A warning marker appears on the slot card. "
            "You may still do this intentionally to exploit a slot ability — "
            "but account for the lost views in your planning."
        ),
        "highlight": None,
        "tab":       None,
        "trigger":   None,
    },
    # ── 7 ─────────────────────────────────────────────────────────────────────
    {
        "title":     "STARS",
        "body": (
            "Stars attach to shows (up to the show's STAR SLOTS limit). "
            "Each star has a CONDITION — for example, the show must be a specific genre. "
            "If the condition fires you get the primary effect (views, income, multiplier). "
            "Otherwise you get a weaker FALLBACK effect, often with added upkeep. "
            "PRIME TIME slot amplifies star view multipliers beyond their base value. "
            "Check each star's card for exact match and fallback values."
        ),
        "highlight": "shop",
        "tab":       "stars",
        "trigger":   None,
    },
    # ── 8 ─────────────────────────────────────────────────────────────────────
    {
        "title":     "ADS — DUAL INCOME",
        "body": (
            "Click SIGN on an AD card to place it on a show (up to the show's AD SLOTS). "
            "Ads pay you two ways: "
            "UPFRONT CASH credited immediately to budget when you sign, "
            "and SEASONAL INCOME every season the show airs. "
            "The SIGN pill shows the net out-of-pocket cost after the upfront bonus. "
            "Some ads have genre or slot conditions — check the CONDITION line. "
            "The MORNING slot boosts positive ad income for shows placed there."
        ),
        "highlight": "shop",
        "tab":       "ads",
        "trigger":   None,
    },
    # ── 9 ─────────────────────────────────────────────────────────────────────
    {
        "title":     "GLOBAL UPGRADES",
        "body": (
            "UPGRADES apply to every show in your schedule — live shows AND vault reruns. "
            "There is a maximum number of active upgrades at once; they do not expire. "
            "Upgrades can boost genre-specific views, amplify slot bonuses, "
            "increase vault rerun income, and more. "
            "Stack compatible upgrades for stronger combined effects. "
            "Read the EFFECT line on each upgrade card for exactly what it does."
        ),
        "highlight": "shop",
        "tab":       "upgrades",
        "trigger":   None,
    },
    # ── 10 ────────────────────────────────────────────────────────────────────
    {
        "title":     "ONE-OFF EVENTS (QUEUED)",
        "body": (
            "Click BUY on an EVENT card to queue it. "
            "Events do NOT fire immediately — they activate at the "
            "START of the NEXT season. Queued events appear in the "
            "CONTRACTS & QUEUED EVENTS bar on the left panel. "
            "Effects include: bonus views, budget injections, show age resets, "
            "free shop rerolls, and other tradeoffs. "
            "Hover any event card for full effect details."
        ),
        "highlight": "shop",
        "tab":       "events",
        "trigger":   None,
    },
    # ── 11 ────────────────────────────────────────────────────────────────────
    {
        "title":     "SYNDICATION VAULT",
        "body": (
            "The VAULT holds up to two shows in RERUN. "
            "Vault shows earn a fraction of their live view total each season — "
            "the exact rate is shown on the vault card, and the Syndication Deal "
            "upgrade increases it further. "
            "The show's AGE IS FROZEN when vaulted — no further decay. "
            "Syndicating a show at peak age locks in its best view multiplier permanently. "
            "Only size-1 shows can be syndicated (2-slot shows cannot fit the vault)."
        ),
        "highlight": "left",
        "tab":       None,
        "trigger":   None,
    },
    # ── 12 ────────────────────────────────────────────────────────────────────
    {
        "title":     "GENRE MONOPOLY",
        "body": (
            "Fill ALL 4 lineup slots with shows of the SAME genre for a MONOPOLY bonus. "
            "Each genre has a completely different bonus type: "
            "SITCOM cuts all show upkeep; "
            "DRAMA boosts views and income; "
            "SCIFI amplifies star bonuses across every slot, not just Prime Time; "
            "REALITY multiplies ad income; "
            "SPORTS gives the largest raw view multiplier; "
            "NEWS reduces your next quota milestone target; "
            "COOKING adds direct budget to your account each season. "
            "Hover the MONOPOLY bar at the bottom of the left panel "
            "to see the exact values for every genre."
        ),
        "highlight": "left",
        "tab":       None,
        "trigger":   None,
    },
    # ── 13 ────────────────────────────────────────────────────────────────────
    {
        "title":     "AIR SEASON — GO!",
        "body": (
            "You're ready. Click AIR SEASON in the top-right corner "
            "to simulate one season. Your shows air, views and income "
            "are calculated, and the Season Summary screen shows you exactly "
            "what happened — views per show, ad revenue, star performance, "
            "and your net profit/loss. "
            "Hit the views quota by season 3 or the network ices you. Good luck."
        ),
        "highlight": "header",
        "tab":       None,
        "trigger":   "season",
    },
    # ── 14 ────────────────────────────────────────────────────────────────────
    {
        "title":     "SEASONAL NEWS",
        "body": (
            "At the END of every season, a random SEASONAL EVENT rolls for NEXT season. "
            "Events can be positive (view boost, income bonus, ad bonuses) "
            "or negative (upkeep spike, view penalty). "
            "MODIFIER — passive multiplier active for several seasons (shown in left panel); "
            "MANDATE — meet a requirement each season or pay an automatic fine; "
            "CONTRACT — hit a target within a window for a budget reward; "
            "INSTANT — one-time effect at the start of next season."
        ),
        "highlight": "left",
        "tab":       None,
        "trigger":   None,
    },
    # ── 15 ────────────────────────────────────────────────────────────────────
    {
        "title":     "CONTRACTS & THE OFFERS BOARD",
        "body": (
            "The CONTRACTS tab shows optional deals you can ACCEPT. "
            "Hit the requirement within the contract window for a budget reward. "
            "If the window closes unmet, a penalty applies instead. "
            "MANDATES are non-optional: miss them each season and pay a fine automatically. "
            "Accepted contracts appear in the CONTRACTS & QUEUED EVENTS bar on the left. "
            "Note: selling an unaired show (Age 1) gives a smaller refund than "
            "selling a show that has already aired and earned views."
        ),
        "highlight": "shop",
        "tab":       "contracts",
        "trigger":   None,
    },
    # ── 16 ────────────────────────────────────────────────────────────────────
    {
        "title":     "INSOLVENCY BAILOUTS",
        "body": (
            "If your budget goes negative at end of season, you may receive "
            "a BAILOUT (available a limited number of times per run): "
            "LOAN — a cash injection plus a binding contract attached; "
            "miss the contract and pay penalties on top of the debt. "
            "GRANT — a cash injection from a public broadcaster; "
            "you forfeit a portion of your accumulated total views. "
            "After the bailout limit is reached there is no rescue — "
            "manage your upkeep carefully."
        ),
        "highlight": None,
        "tab":       None,
        "trigger":   None,
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
