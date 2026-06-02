"""
tutorial.py — NETEXEC
======================
Step-by-step tutorial system for first-time players.

Each step dims the entire screen, draws a spotlight highlight around the
relevant panel, shows an instruction popup with a solid plate (using the
type ramp from theme.py), and provides Next, Back, and Skip buttons.

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
from scripts.engine.constants import (
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
            "Stars and Ads add costs or bonuses. "
            "Run out of budget and your shows still air — "
            "but you can't buy new ones."
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
            "Five tabs: SHOWS, STARS, ADS, UPGRADES, EVENTS. "
            "Click REROLL to draw fresh items — starts at $3 and rises $1 per use, "
            "resetting each season. "
            "The pool also refills automatically when a new season starts."
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
            "Each show has BASE VIEWS, UPKEEP, STAR SLOTS, and AD SLOTS. "
            "2-SLOT shows occupy two adjacent positions for massive views. "
            "To cancel a show, click SELL — refund is 75% of the show cost "
            "plus 50% of each attached star's cost."
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
            "Step 2 — choose one of 3 rolled show types (genres); "
            "Step 3 — choose one of 3 generated abilities with different "
            "view/income effects. Then place it like any regular show."
        ),
        "highlight": "shop",
        "tab":       "shows",
        "trigger":   None,
    },
    # ── 5 ─────────────────────────────────────────────────────────────────────
    {
        "title":     "TIME SLOT ABILITIES",
        "body": (
            "Each of the 4 time slots has a passive ability: "
            "MORNING — Ad Income +20%; "
            "AFTERNOON — Base Views +10%; "
            "PRIME TIME — Star View Bonus x1.5 (amplifies the bonus portion); "
            "LATE NIGHT — Show Upkeep -50% (halved, floored at $0). "
            "Stack synergies: a star with x1.5 becomes x1.75 in Prime Time."
        ),
        "highlight": "left",
        "tab":       None,
        "trigger":   None,
    },
    # ── 6 ─────────────────────────────────────────────────────────────────────
    {
        "title":     "SLOT PENALTY",
        "body": (
            "Every show lists RECOMMENDED SLOTS on its card. "
            "If you place a show OUTSIDE all its recommended slots, "
            "it loses 30% of its views (x0.70). "
            "A warning MISMATCH appears on the slot card. "
            "You may do this deliberately to exploit a slot ability — "
            "but budget the view loss."
        ),
        "highlight": None,
        "tab":       None,
        "trigger":   None,
    },
    # ── 7 ─────────────────────────────────────────────────────────────────────
    {
        "title":     "STARS",
        "body": (
            "Stars attach to shows (up to the show's STAR SLOTS). "
            "Each star has a CONDITION. If the condition fires (e.g. show is DRAMA), "
            "you get the primary effect. Otherwise you get the fallback — "
            "usually weaker and with added upkeep. "
            "PRIME TIME amplifies star view multipliers."
        ),
        "highlight": "shop",
        "tab":       "stars",
        "trigger":   None,
    },
    # ── 8 ─────────────────────────────────────────────────────────────────────
    {
        "title":     "ADS — DUAL INCOME",
        "body": (
            "Click SIGN on an AD card to place it on a show. "
            "Ads pay you TWO ways: "
            "UPFRONT CASH credited immediately to budget, "
            "plus SEASONAL INCOME every season the show airs. "
            "The SIGN button shows the net out-of-pocket cost. "
            "MORNING slot scales positive ad income by +20%."
        ),
        "highlight": "shop",
        "tab":       "ads",
        "trigger":   None,
    },
    # ── 9 ─────────────────────────────────────────────────────────────────────
    {
        "title":     "GLOBAL UPGRADES",
        "body": (
            "UPGRADES apply to every show in your schedule — live AND vault. "
            "Maximum 5 active at once; they do not expire. "
            "Examples: Laugh Track (+50 views to all SITCOMs), "
            "Sweeps Week (Prime Time x1.3), Syndication Deal (vault views x0.5). "
            "Stack compatible upgrades for multiplicative effects."
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
            "Effects include: +views, +budget, rejuvenating show age, "
            "free shop reroll, permanent base-view buffs, and tradeoffs "
            "(budget for -views). Right-click any card for full details."
        ),
        "highlight": "shop",
        "tab":       "events",
        "trigger":   None,
    },
    # ── 11 ────────────────────────────────────────────────────────────────────
    {
        "title":     "SYNDICATION VAULT",
        "body": (
            "The VAULT holds up to 2 shows in RERUN. "
            "Vault shows earn 25% of their live views "
            "(50% with the Syndication Deal upgrade) "
            "and their AGE IS FROZEN — no further decay. "
            "Syndicating a peak-age-2 show preserves its x1.25 multiplier forever. "
            "Only size-1 shows can be syndicated."
        ),
        "highlight": "left",
        "tab":       None,
        "trigger":   None,
    },
    # ── 12 ────────────────────────────────────────────────────────────────────
    {
        "title":     "GENRE MONOPOLY",
        "body": (
            "Fill ALL 4 lineup slots with the SAME genre for a genre monopoly bonus. "
            "Each genre has a UNIQUE bonus type: "
            "SITCOM — upkeep halved; "
            "DRAMA — premium views + income; "
            "SCIFI — star bonuses amplified in ALL slots; "
            "REALITY — ad income x1.5; "
            "SPORTS — highest view multiplier; "
            "NEWS — quota target reduced; "
            "COOKING — direct budget added each season."
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
            "to simulate one season. Your shows will air, views and income "
            "will be calculated, and the Season Summary screen will show you "
            "exactly what happened — views per show, ad revenue, star performance, "
            "and your net profit/loss. "
            "Hit the quota at season 3 or the network ices you. Good luck."
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
            "Events can be POSITIVE (views boost, income flat, ad bonuses) "
            "or NEGATIVE (upkeep spike, views penalty). "
            "MODIFIER — passive multiplier while active (shown in left panel); "
            "MANDATE — meet a requirement each season or pay a fine; "
            "CONTRACT — hit a target in a window for a reward; "
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
            "CONTRACTS tab in the shop shows optional deals you can ACCEPT. "
            "Hit the requirement within the contract window for a budget bonus. "
            "If the window closes unmet, a penalty applies. "
            "MANDATES are non-optional: miss them each season and pay a fine automatically. "
            "Accepted contracts appear in the CONTRACTS & QUEUED EVENTS bar on the left panel. "
            "Selling a show: AGE 1 (never aired) gives NO refund. "
            "Older shows pay out based on views they earned."
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
            "a BAILOUT (up to twice per run): "
            "LOAN — cash injection plus a binding contract; miss it and pay penalties. "
            "GRANT — cash injection from a public broadcaster; "
            "you forfeit a chunk of total views upfront. "
            "After two bailouts there is no rescue."
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

    Instantiated by GameUI when a new game starts on Run 1 (unless the
    player has completed or skipped the tutorial before).
    Destroyed (set to None) after all steps are complete or skipped.
    """

    POPUP_W = 560
    POPUP_H = 220

    def __init__(self):
        self.step      = 0
        self.done      = False
        self._elapsed  = 0
        self._last_sw  = SCREEN_WIDTH
        self._last_sh  = SCREEN_HEIGHT

    def update(self, dt_ms: int):
        self._elapsed += dt_ms

    def advance(self, state=None):
        self.step    += 1
        self._elapsed = 0
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

    def skip(self):
        self.done = True

    def notify(self, event_type: str):
        """Auto-advance if the current step has a matching trigger."""
        if self.done:
            return
        current = STEPS[self.step] if self.step < len(STEPS) else None
        if current and current.get("trigger") == event_type:
            self.advance()

    def draw(self, surface: pygame.Surface, fonts: dict):
        """Render the tutorial overlay: dim + spotlight + popup plate."""
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
        popup_y = sh - self.POPUP_H - 24
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

        # Step counter
        f_mi   = fonts.get("micro", fonts.get("body"))
        f_bold = fonts.get("bold",  fonts.get("body"))
        f_sm   = fonts.get("small", fonts.get("body"))

        step_str  = f"TUTORIAL  {self.step + 1} / {len(STEPS)}"
        step_surf = f_mi.render(step_str, True, C_CYAN)
        step_surf.set_alpha(alpha)
        surface.blit(step_surf, (popup_rect.x + 10, popup_rect.y + 7))

        # Title
        t_surf = f_bold.render(step_data["title"], True, C_CYAN)
        t_surf.set_alpha(alpha)
        surface.blit(t_surf, (popup_rect.x + 10, popup_rect.y + 20))

        # Body text (word-wrapped)
        body_rect = pygame.Rect(popup_rect.x + 10, popup_rect.y + 42,
                                self.POPUP_W - 20, self.POPUP_H - 78)
        self._draw_wrapped(surface, step_data["body"], f_sm,
                           body_rect, C_WHITE, alpha)

        # Buttons
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
        popup_y    = sh - self.POPUP_H - 24
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

    def _draw_spotlight(self, surface: pygame.Surface, panel: str,
                        alpha: int, sw: int, sh: int):
        """
        Cut a bright spotlight rect out of the dim overlay and draw a
        glowing border around the highlighted panel.

        sw/sh are the game-surface dimensions (cutout-local, origin at 0,0).
        We compute panel rects in game-surface coordinates directly without the
        bezel offset (which does not apply here since surface IS the game surface).
        """
        from ui.layout import _PAD, _HUD_FRAC, _HUD_MIN, _HUD_MAX, _SPLIT
        hud_h   = max(_HUD_MIN, min(_HUD_MAX, int(sh * _HUD_FRAC)))
        left_w  = max(380, int(sw * _SPLIT))
        right_w = max(380, sw - left_w - _PAD)
        right_x = left_w + _PAD
        stage_y = hud_h + _PAD
        stage_h = max(1, sh - stage_y - _PAD)

        rects = {
            "header": pygame.Rect(0,            0,       sw,                hud_h),
            "left":   pygame.Rect(_PAD,          stage_y, left_w  - _PAD*2, stage_h),
            "shop":   pygame.Rect(right_x + _PAD, stage_y, right_w - _PAD*2, stage_h),
        }
        rect = rects.get(panel)
        if not rect:
            return

        # Bright window: redraw the game area at full brightness inside rect
        pad = 4
        bright = pygame.Rect(rect.x - pad, rect.y - pad,
                             rect.width + pad * 2, rect.height + pad * 2)
        # Re-lighten the spotlight area (remove the dim)
        clear = pygame.Surface((bright.width, bright.height), pygame.SRCALPHA)
        clear.fill((0, 0, 0, max(0, min(170, int(170 * alpha / 255)) - 60)))
        surface.blit(clear, bright.topleft, special_flags=pygame.BLEND_RGBA_SUB)

        # Glowing border around the spotlight
        glow_a = min(200, alpha)
        glow   = pygame.Surface((bright.width + 8, bright.height + 8), pygame.SRCALPHA)
        pygame.draw.rect(glow, (80, 220, 200, glow_a // 2),
                         (0, 0, bright.width + 8, bright.height + 8),
                         4, border_radius=8)
        surface.blit(glow, (bright.x - 4, bright.y - 4))
        pygame.draw.rect(surface, (80, 220, 200),
                         pygame.Rect(bright.x, bright.y, bright.width, bright.height),
                         2, border_radius=6)

    def _draw_wrapped(self, surface: pygame.Surface, text: str,
                      font: pygame.font.Font, rect: pygame.Rect,
                      color: tuple, alpha: int):
        """Word-wrap and render text with per-surface alpha."""
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
                    s.set_alpha(alpha)
                    surface.blit(s, (rect.x, y))
                    y += font.get_linesize()
                    if y + font.get_linesize() > rect.bottom:
                        return
                line = word
        if line:
            s = font.render(line, True, color)
            s.set_alpha(alpha)
            surface.blit(s, (rect.x, y))

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
