"""
ui.py — NETEXEC
===============
Thin GameUI controller.

Owns the pygame surface, font objects, click/tooltip regions, toast queue,
animation state, and the current active screen.  Each frame it:
  1. Rebuilds click/tooltip regions.
  2. Delegates rendering to the appropriate screen module.
  3. Draws global overlays (scanlines, flash, toasts, number pops, tooltips).

The main game loop (main.py) calls:
  ui.handle_event(event, state)  — once per pygame event
  ui.update(dt_ms, state)        — once per frame
  ui.render(state)               — once per frame

Screen navigation
-----------------
All screen transitions go through set_screen(GameScreen.X).  Screen modules
receive the GameUI instance as ``ctx`` and call ctx.set_screen() to navigate;
they never import other screen modules directly.
"""

import pygame
import math

from engine.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
    HEADER_H, PAD,
    C_BG, C_PANEL, C_PANEL_BORDER,
    C_GREEN_BRIGHT, C_GREEN_MID, C_GREEN_DIM,
    C_AMBER, C_AMBER_DIM, C_RED, C_RED_DIM, C_WHITE, C_CYAN,
    C_GREY_LIGHT, C_GREY_MID, C_GREY_DARK,
    C_SELECTED, C_BORDER, C_BORDER_DIM,
    C_FLASH_POS, C_FLASH_NEG,
    C_NET_POS, C_NET_NEG, C_VIEWS_ACCENT,
    TOAST_DURATION, TOAST_FADE_MS,
    FLASH_DURATION_MS, BLINK_PERIOD_MS, SCANLINE_ALPHA, SCANLINE_SPACING,
)
from .theme import load_fonts
from .assets import draw_crt_scanlines, apply_crt, NumberPop
from .bezel import draw_bezel, C_CHROME_BASE
from .layout import compute_layout, Layout, MIN_W, MIN_H
from .screen_enum import GameScreen
from .screens import playing as _playing_mod
from .screens.menu import MenuScreen
from .screens.difficulty import DifficultyScreen
from .screens.settings import SettingsScreen
from .screens.summary import SummaryScreen
from .screens.pause import PauseScreen
from .screens.game_over import GameOverScreen
from .screens.win import WinScreen
from .screens.wildcard_show import WildcardShowScreen
from .screens.wildcard_ad import WildcardAdScreen


class GameUI:
    """
    Top-level UI controller.

    Owns the pygame surface, font objects, click regions, toast queue,
    animation state, and current screen enum.

    The main game loop (main.py) calls:
      ui.handle_event(event, state)  — once per pygame event
      ui.update(dt_ms, state)        — once per frame
      ui.render(state)               — once per frame (draws to screen)
    """

    def __init__(self, surface: pygame.Surface):
        self.screen      = surface          # pygame.Surface (main display)
        self.screen_name = GameScreen.MENU  # active screen identifier

        # ── Fonts ──────────────────────────────────────────────────────────────
        self._fonts = {}
        self._init_fonts()

        # ── Click regions (rebuilt every frame) ────────────────────────────────
        self._click_regions: list[tuple[pygame.Rect, callable]] = []

        # ── Scrollbar regions (rebuilt every frame) + active drag state ────────
        self._scrollbar_regions: list[dict] = []
        self._sb_drag: dict | None = None

        # ── Slider regions (rebuilt every frame) + active drag state ───────────
        self._slider_regions: list[dict] = []
        self._slider_drag: dict | None = None

        # Settings screen tab index + RULES-tab scroll offset.
        self._settings_tab: int = 0
        self._settings_scroll: int = 0

        # ── Graphics toggles ───────────────────────────────────────────────────
        # When the GPU CRT presenter (self._gl) is active the full curved-tube
        # shader runs every frame, so the effect can default ON. Without GPU,
        # the CPU path is heavier, so it stays opt-in (see render()).
        self._crt_enabled: bool = True

        # GPU CRT presenter (ModernGL). Set by main.py when a GL context is
        # available; None means the CPU/numpy path is used instead.
        self._gl = None
        self._present_surf = None   # offscreen full-window composite for GL mode

        # Drifting atmosphere haze (rendered before the CRT pass). Toggle in
        # settings; subtle by default.
        from .atmosphere import Atmosphere
        self._atmosphere = Atmosphere()
        # Off by default so the baseline look is clean; opt-in via settings.
        self._atmosphere_enabled: bool = False

        # Per-effect CRT intensities (normalized 0..1), driven by Settings
        # sliders and applied by the GPU shader (see crt_gl.present).
        self._crt_params = {
            "curvature":  0.45,
            "scanline":   0.40,
            "aberration": 0.40,
            "vignette":   0.55,
        }

        # ── Toast notifications {text, level, color, elapsed} ──────────────────
        self._toasts: list[dict] = []

        # ── Floating number pop-ups ────────────────────────────────────────────
        self._pops: list[NumberPop] = []

        # ── Flash overlay ─────────────────────────────────────────────────────
        self._flash_color   = None
        self._flash_elapsed = 0

        # ── Mouse tracking ────────────────────────────────────────────────────
        self._mouse_pos = (0, 0)

        # ── Tick for blinking elements and menu animation ──────────────────────
        self._tick_ms        = 0
        self._last_dt_ms     = 0
        self._menu_logo_phase = 0.0

        # ── Tutorial overlay controller ────────────────────────────────────────
        self._tutorial = None
        # Set True once tutorial is done; persisted across sessions via settings.
        self._tutorial_done          = False
        # Set True from Settings screen to force tutorial on next game start.
        self._replay_tutorial_requested = False

        # ── Wildcard modal state ───────────────────────────────────────────────
        self._wc_name              = ""
        self._wc_input_active      = False
        self._wc_step              = 1       # 1=name, 2=type, 3=ability
        self._wc_offered_types:    list = []
        self._wc_genre             = None    # chosen type ID
        self._wc_offered_abilities: list = []
        self._wc_chosen_ability:   dict | None = None
        self._wc_slots:            list = []  # legacy, kept for safety

        # ── Settings state ────────────────────────────────────────────────────
        self._settings_return_screen = GameScreen.MENU
        self._settings_sfx_vol   = 0.65
        self._settings_music_vol = 0.30
        self._settings_res_idx   = 2

        # ── Scroll / summary ──────────────────────────────────────────────────
        self._summary_scroll = 0

        # ── Audio reference (injected from main.py) ───────────────────────────
        self.audio = None

        # ── Game-over state ───────────────────────────────────────────────────
        self._gameover_state = None   # 'win' or 'loss'

        # ── Screen instances ──────────────────────────────────────────────────
        self._screen_map = {
            GameScreen.MENU:           MenuScreen(),
            GameScreen.DIFFICULTY:     DifficultyScreen(),
            GameScreen.SETTINGS:       SettingsScreen(),
            GameScreen.PLAYING:        _playing_mod.PlayingScreen(),
            GameScreen.SEASON_SUMMARY: SummaryScreen(),
            GameScreen.PAUSE:          PauseScreen(),
            GameScreen.GAME_OVER:      GameOverScreen(),
            GameScreen.WIN:            WinScreen(),
            GameScreen.WILDCARD_SHOW:  WildcardShowScreen(),
            GameScreen.WILDCARD_AD:    WildcardAdScreen(),
        }
        # Screens that render game background before their own layer
        self._overlay_screens = {
            GameScreen.SEASON_SUMMARY,
            GameScreen.WILDCARD_SHOW,
            GameScreen.WILDCARD_AD,
        }

        # ── Adaptive sizing ───────────────────────────────────────────────────
        self._sw = SCREEN_WIDTH
        self._sh = SCREEN_HEIGHT
        self._layout: Layout = compute_layout(SCREEN_WIDTH, SCREEN_HEIGHT)
        self._game_surf: pygame.Surface | None = None   # game-content sub-surface

        # ── Tooltip tracking (right-click to show/dismiss) ────────────────────
        self._tooltip_regions: list[tuple[pygame.Rect, dict]] = []
        self._pinned_tooltip_key: str = ""      # key of the pinned tooltip
        self._pinned_tooltip_pos: tuple = (0, 0)  # screen pos where it was pinned
        # Legacy fields kept so _draw_tooltip compiles without change
        self._hover_ttip_key   = ""
        self._hover_start_tick = 0

        # ── Show detail modal ─────────────────────────────────────────────────
        self._show_detail: dict | None = None
        self._detail_scroll: int = 0

        # ── Fullscreen ────────────────────────────────────────────────────────
        self._fullscreen = False

        # ── Cross-screen transition state ─────────────────────────────────────
        self._pending_new_run = False

        # ── Scroll offsets (pixels) for scrollable panels ─────────────────────
        self._schedule_scroll: int = 0
        self._shop_scroll:     int = 0
        self._SCROLL_SPEED:    int = 24

        # ── Ledger panel toggle & scroll ──────────────────────────────────────
        self._show_ledger:       bool = False
        self._ledger_scroll:     int  = 0
        self._ledger_prev_count: int  = 0

    # ─── FONT INIT ────────────────────────────────────────────────────────────

    def _init_fonts(self):
        self._fonts = load_fonts()

    def _f(self, key: str) -> pygame.font.Font:
        """Shorthand font accessor."""
        return self._fonts.get(key, self._fonts["body"])

    # ── Layout ─────────────────────────────────────────────────────────────────

    @property
    def layout(self) -> Layout:
        """Current frame's responsive layout (recomputed each render call)."""
        return self._layout

    @property
    def _L(self) -> int:
        return self._layout.left_w

    @property
    def _R(self) -> int:
        return self._layout.right_w

    @property
    def _X(self) -> int:
        return self._layout.right_x

    # ─── SCREEN NAVIGATION ───────────────────────────────────────────────────

    def set_screen(self, screen: GameScreen):
        """Navigate to a new screen. All transitions go through this method."""
        if screen in (GameScreen.WILDCARD_SHOW, GameScreen.WILDCARD_AD):
            self._reset_wc_state()
        self.screen_name = screen

    def _reset_wc_state(self):
        """Reset all wildcard modal state for a fresh modal session."""
        self._wc_name              = ""
        self._wc_input_active      = False
        self._wc_step              = 1
        self._wc_offered_types     = []
        self._wc_genre             = None
        self._wc_offered_abilities = []
        self._wc_chosen_ability    = None
        self._wc_slots             = []

    # ─── EVENT HANDLING ───────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event, state):
        # Translate window-space coords to cutout-local coords so that click
        # regions (which are expressed in game-surface coordinates) match.
        cut = self._layout.cutout

        if event.type == pygame.MOUSEMOTION:
            self._mouse_pos = (event.pos[0] - cut.x, event.pos[1] - cut.y)
            # Live thumb drag: map mouse-y within the track to a scroll offset.
            if self._sb_drag is not None:
                d      = self._sb_drag
                track  = d["track"]
                travel = max(1, track.height - d["thumb_h"])
                rel    = (self._mouse_pos[1] - track.y - d["grab"]) / travel
                d["set"](int(max(0.0, min(1.0, rel)) * d["max_scroll"]))
            # Live slider drag: map mouse-x within the slider to a 0..1 value.
            elif self._slider_drag is not None:
                from .widgets import slider_value_at
                r = self._slider_drag["rect"]
                self._slider_drag["set"](slider_value_at(r, self._mouse_pos[0]))

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = (event.pos[0] - cut.x, event.pos[1] - cut.y)
            if self._handle_scrollbar_press(pos):
                return
            if self._handle_slider_press(pos):
                return

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            # Right-click: pin/unpin a tooltip for the region under the cursor.
            self._toggle_pinned_tooltip(event.pos)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._slider_drag is not None:
                self._slider_drag = None    # finish slider drag; swallow the click
                return
            if self._sb_drag is not None:
                self._sb_drag = None        # finish thumb drag; swallow the click
                return
            pos = (event.pos[0] - cut.x, event.pos[1] - cut.y)
            if self._tutorial and not self._tutorial.done:
                return
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_CTRL:
                # Ctrl+left-click: same as right-click (tooltip toggle for laptop users)
                self._toggle_pinned_tooltip(event.pos)
                return
            # Plain left-click: dismiss any pinned tooltip, then fire click region
            self._pinned_tooltip_key = ""
            for rect, callback in self._click_regions:
                if rect.collidepoint(pos):
                    callback()
                    break

        elif event.type == pygame.MOUSEWHEEL:
            dy = -event.y * self._SCROLL_SPEED
            # Wheel over a slider nudges its value (takes priority over scroll).
            if self._nudge_slider_under_cursor(event.y):
                return
            if self._tutorial and not self._tutorial.done:
                self._tutorial.scroll(dy)
            elif self.screen_name == GameScreen.SETTINGS:
                # Wheel scrolls the RULES tab content
                self._settings_scroll = max(0, self._settings_scroll + dy)
            elif self._show_detail:
                # Wheel on show detail modal scrolls the modal content
                self._detail_scroll = max(0, self._detail_scroll + dy)
            elif self._show_ledger:
                # Wheel on ledger panel scrolls the ledger
                self._ledger_scroll = max(0, self._ledger_scroll + dy)
            else:
                # Route wheel scrolling to the panel under the cursor.
                mx, my = self._mouse_pos
                lo = self._layout
                if lo.schedule.collidepoint(mx, my):
                    self._schedule_scroll = max(0, self._schedule_scroll + dy)
                elif lo.shop.collidepoint(mx, my):
                    self._shop_scroll = max(0, self._shop_scroll + dy)

        elif event.type == pygame.KEYDOWN:
            if self._tutorial and not self._tutorial.done:
                return
            self._handle_key(event, state)

    def _handle_scrollbar_press(self, pos: tuple) -> bool:
        """Left-press on a scrollbar: arrows step, thumb begins drag, track pages.

        Returns True if the press hit a scrollbar (so the click is consumed).
        """
        for r in self._scrollbar_regions:
            if r["thumb"].collidepoint(pos):
                # Begin dragging — remember where on the thumb we grabbed.
                self._sb_drag = {
                    "track": r["track"], "thumb_h": r["thumb_h"],
                    "max_scroll": r["max_scroll"], "set": r["set"],
                    "grab": pos[1] - r["thumb"].y,
                }
                return True
            if r["up"].collidepoint(pos):
                r["set"](max(0, r["scroll"] - r["step"]))
                return True
            if r["down"].collidepoint(pos):
                r["set"](min(r["max_scroll"], r["scroll"] + r["step"]))
                return True
            if r["track"].collidepoint(pos):
                # Page toward the click position.
                if pos[1] < r["thumb"].y:
                    r["set"](max(0, r["scroll"] - r["view_h"]))
                else:
                    r["set"](min(r["max_scroll"], r["scroll"] + r["view_h"]))
                return True
        return False

    def _handle_slider_press(self, pos: tuple) -> bool:
        """Left-press on a slider: jump to the clicked value and begin dragging.

        Returns True if the press hit a slider (so the click is consumed).
        """
        from .widgets import slider_value_at
        for r in self._slider_regions:
            rect = r["rect"]
            # Generous vertical hit area so the thin slider is easy to grab.
            hit = rect.inflate(0, 10)
            if hit.collidepoint(pos):
                r["set"](slider_value_at(rect, pos[0]))
                self._slider_drag = {"rect": rect, "set": r["set"]}
                return True
        return False

    def _nudge_slider_under_cursor(self, wheel_y: int) -> bool:
        """Mouse wheel over a slider nudges its value by a small step."""
        for r in self._slider_regions:
            if r["rect"].inflate(0, 10).collidepoint(self._mouse_pos):
                step = 0.05 * (1 if wheel_y > 0 else -1)
                r["set"](max(0.0, min(1.0, r["value"] + step)))
                return True
        return False

    def _toggle_pinned_tooltip(self, raw_pos: tuple):
        """Pin or unpin a tooltip at raw_pos (window coords). Called on right-click or Ctrl+click."""
        if self._tutorial and not self._tutorial.done:
            return
        cut = self._layout.cutout
        pos = (raw_pos[0] - cut.x, raw_pos[1] - cut.y)
        new_key = ""
        for rect, data in self._tooltip_regions:
            if rect.collidepoint(pos):
                new_key = data.get("title", "") + data.get("type", "")
                break
        if new_key and new_key != self._pinned_tooltip_key:
            self._pinned_tooltip_key = new_key
            self._pinned_tooltip_pos = pos
        else:
            self._pinned_tooltip_key = ""

    def _handle_key(self, event: pygame.event.Event, state):
        key = event.key

        # Wildcard text input
        if (self.screen_name in (GameScreen.WILDCARD_SHOW, GameScreen.WILDCARD_AD)
                and self._wc_input_active):
            if key == pygame.K_BACKSPACE:
                self._wc_name = self._wc_name[:-1]
            elif key == pygame.K_RETURN:
                self._wc_input_active = False
            elif len(self._wc_name) < 28:
                char = event.unicode
                if char and char.isprintable():
                    self._wc_name += char

        elif key == pygame.K_F11:
            self._toggle_fullscreen()

        elif key == pygame.K_ESCAPE:
            if self._show_detail:
                self._show_detail = None
            elif self.screen_name == GameScreen.PLAYING:
                self.set_screen(GameScreen.PAUSE)
            elif self.screen_name == GameScreen.PAUSE:
                self.set_screen(GameScreen.PLAYING)
            elif self.screen_name == GameScreen.SETTINGS:
                self.set_screen(getattr(self, "_settings_return_screen", GameScreen.PAUSE))

    # ─── UPDATE ───────────────────────────────────────────────────────────────

    def update(self, dt_ms: int, state):
        self._tick_ms    += dt_ms
        self._last_dt_ms  = dt_ms

        for t in self._toasts:
            t["elapsed"] += dt_ms
        self._toasts = [t for t in self._toasts
                        if t["elapsed"] < TOAST_DURATION + TOAST_FADE_MS]

        for p in self._pops:
            p.update(dt_ms)
        self._pops = [p for p in self._pops if not p.is_done()]

        if self._flash_color:
            self._flash_elapsed += dt_ms
            if self._flash_elapsed >= FLASH_DURATION_MS:
                self._flash_color   = None
                self._flash_elapsed = 0

        self._menu_logo_phase = (self._menu_logo_phase + dt_ms * 0.003) % (2 * math.pi)

        if self._tutorial:
            self._tutorial.update(dt_ms)

    # ─── RENDER DISPATCHER ────────────────────────────────────────────────────

    def render(self, state):
        """Draw the current screen; rebuild click/tooltip regions each frame."""
        self._click_regions     = []
        self._tooltip_regions   = []
        self._scrollbar_regions = []
        self._slider_regions    = []

        _window = self.screen
        win_w = _window.get_width()
        win_h = _window.get_height()
        self._layout = compute_layout(win_w, win_h)
        cutout = self._layout.cutout

        # In GPU mode the whole frame is composited onto an offscreen surface and
        # presented through the CRT shader; the GL window itself is never blitted.
        if self._gl is not None:
            if (self._present_surf is None or
                    self._present_surf.get_size() != (win_w, win_h)):
                self._present_surf = pygame.Surface((win_w, win_h))
            main_target = self._present_surf
        else:
            main_target = _window

        # Recreate the game sub-surface whenever the cutout size changes.
        if (self._game_surf is None or
                self._game_surf.get_size() != (cutout.w, cutout.h)):
            self._game_surf = pygame.Surface((cutout.w, cutout.h))

        # _sw/_sh are cutout dimensions; all game code renders relative to (0,0).
        self._sw = cutout.w
        self._sh = cutout.h

        # Fill the main window with chrome background colour.
        main_target.fill(C_CHROME_BASE)

        # ── Render game content into the sub-surface ──────────────────────────
        _main_screen    = main_target
        self.screen     = self._game_surf
        self.screen.fill(C_BG)

        s = self.screen_name

        if s in self._overlay_screens:
            _playing_mod.render_game(self, state)
            # Overlay screens (pause, wildcard, summary) block game interaction:
            # discard any click/tooltip regions the game just registered so that
            # only the overlay's own regions are active this frame.
            self._click_regions     = []
            self._tooltip_regions   = []
            self._scrollbar_regions = []
        self._slider_regions    = []
        if s in self._screen_map:
            self._screen_map[s].render(self, state)

        # CRT filter on the game surface. In GPU mode the shader handles the
        # whole frame at present time, so skip the CPU pass here. Otherwise the
        # baseline is cheap cached scanlines; the full numpy pipeline is opt-in.
        if self._gl is None and self._last_dt_ms <= 50:
            if self._crt_enabled:
                apply_crt(self.screen, True)
            else:
                draw_crt_scanlines(self.screen, SCANLINE_ALPHA, SCANLINE_SPACING)

        # Flash overlay on game surface
        if self._flash_color:
            alpha = max(0, 180 - int(180 * self._flash_elapsed / FLASH_DURATION_MS))
            flash = pygame.Surface((self._sw, self._sh), pygame.SRCALPHA)
            flash.fill((*self._flash_color, alpha))
            self.screen.blit(flash, (0, 0))

        self._draw_toasts()

        for p in self._pops:
            p.draw(self.screen)

        self._draw_tooltip()

        # ── Restore main screen, blit game surface, draw bezel ────────────────
        self.screen = _main_screen
        self.screen.blit(self._game_surf, cutout.topleft)

        # Determine ON-AIR state for bezel LED animation
        _on_air = getattr(state, 'season', 0) > 0
        draw_bezel(self.screen, self._layout, self._tick_ms, on_air=_on_air)

        # Drifting atmosphere haze over the screen cutout, before the CRT pass.
        if self._atmosphere_enabled:
            self._atmosphere.draw(self.screen, cutout, self._tick_ms, intensity=0.4)

        # ── Present ───────────────────────────────────────────────────────────
        if self._gl is not None:
            try:
                self._gl.present(main_target, self._crt_enabled,
                                 self._tick_ms * 0.001, self._crt_params)
            except Exception:
                # GPU present failed mid-run: disable GL and fall back next frame
                self._gl = None
            self.screen = _window      # keep the window as the stable reference
        else:
            pygame.display.flip()

    # ─── SHARED HELPERS (called by screen modules via ctx) ────────────────────

    def _draw_game(self, state):
        """Draw the game background (header + left + right panels)."""
        _playing_mod.render_game(self, state)

    def _add_click(self, rect: pygame.Rect, callback):
        """Register a clickable region for this frame.

        Clip-aware: the rect is intersected with the surface's active clip
        region before being stored. Scroll panels (shop, schedule, ledger,
        contracts) draw their content inside ``set_clip(view_rect)``, so a
        card scrolled up behind a header/tab bar is visually hidden — this
        ensures it is also non-interactive. A region that falls entirely
        outside the clip is dropped, so hidden/clipped content never receives
        clicks. Unclipped UI (header buttons, tabs, reroll) is unaffected
        because their clip is the full surface.
        """
        clip = self.screen.get_clip()
        if clip is not None:
            rect = rect.clip(clip)
            if rect.width <= 0 or rect.height <= 0:
                return
        self._click_regions.append((rect, callback))

    def _add_tooltip(self, rect: pygame.Rect, data: dict):
        """Register a tooltip region for this frame (clip-aware; see _add_click)."""
        clip = self.screen.get_clip()
        if clip is not None:
            rect = rect.clip(clip)
            if rect.width <= 0 or rect.height <= 0:
                return
        self._tooltip_regions.append((rect, data))

    def _toast(self, message: str, level: str = "info"):
        """Queue a toast notification."""
        color_map = {
            "info":    C_GREEN_MID,
            "success": C_GREEN_BRIGHT,
            "warn":    C_AMBER,
            "error":   C_RED,
        }
        self._toasts.append({
            "text":    message,
            "level":   level,
            "color":   color_map.get(level, C_GREEN_MID),
            "elapsed": 0,
        })
        if self.audio:
            self.audio.play("sfx_toast")

    def _toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        self._fullscreen = not self._fullscreen
        # Preserve the OpenGL context flags when GPU CRT is active.
        _gl = (pygame.OPENGL | pygame.DOUBLEBUF) if self._gl else 0
        if self._fullscreen:
            pygame.display.set_mode((0, 0), pygame.FULLSCREEN | _gl)
        else:
            from engine.constants import RESOLUTIONS
            r = RESOLUTIONS[self._settings_res_idx % len(RESOLUTIONS)]
            # Include RESIZABLE so the window can be resized after exiting fullscreen
            pygame.display.set_mode(r, pygame.RESIZABLE | _gl)
        self.screen     = pygame.display.get_surface()
        if self._gl:
            self._gl.resize(self.screen.get_width(), self.screen.get_height())
        # Reset cached dimensions and game sub-surface so the next render()
        # recomputes layout and recreates the cutout at the new window size.
        self._sw        = self.screen.get_width()
        self._sh        = self.screen.get_height()
        self._game_surf = None
        self._layout    = compute_layout(self._sw, self._sh)

    def _place_on_slot(self, arr_type: str, idx: int, state):
        """Handle placing the selected item onto a schedule slot."""
        result = state.place_selected(arr_type, idx)
        self._toast(result["message"], result["level"])
        if result["ok"]:
            if self.audio: self.audio.play("sfx_place")
            self._flash_color   = C_FLASH_POS
            self._flash_elapsed = 0
        else:
            if self.audio: self.audio.play("sfx_error")

    def _handle_season_result(self, result: dict, state):
        """Process the result of advance_season() and navigate to summary."""
        self.set_screen(GameScreen.SEASON_SUMMARY)
        if result.get("milestone_met") is True:
            self._toast(f"MILESTONE MET! +${result.get('milestone_bonus', 0)}", "success")
            self._flash_color   = C_FLASH_POS
            self._flash_elapsed = 0
            if self.audio: self.audio.play("sfx_milestone")
        elif result.get("milestone_met") is False:
            self._toast("MILESTONE MISSED - RUN OVER", "error")
            self._flash_color   = C_FLASH_NEG
            self._flash_elapsed = 0
            if self.audio: self.audio.play("sfx_gameover")

        if result.get("status") == "win" and self.audio:
            self.audio.play("sfx_win")

        self._pops.append(NumberPop(
            result["season_views"], self._sw // 2, self._sh // 2 - 60,
            color=C_GREEN_BRIGHT, font=self._f("header"), prefix="+",
        ))

    def _start_new_game(self, state, new_run: bool):
        """Navigate to difficulty selection."""
        self._pending_new_run = new_run
        self.set_screen(GameScreen.DIFFICULTY)

    def _resume_game(self, state):
        """Load save slot 0 and resume the game from the exact saved state."""
        from saves import load_game
        data = load_game(0)
        if data:
            state._deserialize(data)
            self._show_ledger    = False
            self._ledger_scroll  = 0
            self._ledger_prev_count = len(state.ledger_log)
            self.set_screen(GameScreen.PLAYING)
        else:
            self._toast("NO SAVE FILE FOUND", "error")

    def _save_game(self, state):
        """Manually save the game to slot 0 (called from the pause menu)."""
        from saves import save_game
        save_game(0, state._serialize())
        self._toast("GAME SAVED", "success")

    # ─── TOAST RENDERING ──────────────────────────────────────────────────────

    def _draw_toasts(self):
        """Render all active toast notifications (bottom-right corner)."""
        x = self._sw - 340
        y = self._sh - 30
        for t in reversed(self._toasts):
            elapsed = t["elapsed"]
            if elapsed >= TOAST_DURATION:
                fade = max(0, 1.0 - (elapsed - TOAST_DURATION) / TOAST_FADE_MS)
            else:
                fade = 1.0
            alpha = int(255 * fade)
            col   = t["color"]

            surf = self._f("small").render(t["text"][:60], True, col)
            surf.set_alpha(alpha)

            bg_surf = pygame.Surface((surf.get_width() + 16, surf.get_height() + 6),
                                     pygame.SRCALPHA)
            bg_surf.fill((0, 12, 0, int(180 * fade)))
            self.screen.blit(bg_surf, (x - 8, y - 3))
            self.screen.blit(surf, (x, y))
            y -= surf.get_height() + 8

    # ─── TOOLTIP RENDERING ────────────────────────────────────────────────────

    def _draw_tooltip(self):
        """Render a rich tooltip panel at the right-click position (pinned until dismissed)."""
        if self._tutorial and not self._tutorial.done:
            return
        if not self._pinned_tooltip_key:
            return

        mx, my = self._pinned_tooltip_pos
        found_data: dict | None = None
        for rect, data in self._tooltip_regions:
            key = data.get("title", "") + data.get("type", "")
            if key == self._pinned_tooltip_key:
                found_data = data
                break

        if not found_data:
            # Region no longer on screen — clear pin
            self._pinned_tooltip_key = ""
            return

        _ACCENT = {
            "show":    C_GREEN_BRIGHT,
            "star":    C_AMBER,
            "ad":      C_GREEN_MID,
            "upgrade": C_CYAN,
            "event":   C_RED,
        }
        card_type = found_data.get("type", "generic")
        accent    = found_data.get("accent", _ACCENT.get(card_type, C_PANEL_BORDER))

        title    = found_data.get("title", "")
        subtitle = found_data.get("subtitle", "")
        sections = found_data.get("sections")
        lines    = found_data.get("lines")

        f_b  = self._f("bold")
        f_mi = self._f("micro")
        PAD_TT  = 10
        WRAP_W  = 300
        lh_mi   = f_mi.get_linesize() + 1

        rows: list[tuple] = []

        def _wrap_text(text: str, col):
            if not text:
                rows.append(("gap",))
                return
            words, cur = text.split(), ""
            for w in words:
                test = (cur + " " + w).strip()
                if f_mi.size(test)[0] <= WRAP_W:
                    cur = test
                else:
                    if cur:
                        rows.append(("text", cur, col))
                    cur = w
            if cur:
                rows.append(("text", cur, col))

        if sections:
            for si, section in enumerate(sections):
                if si > 0:
                    rows.append(("div",))
                for row in section:
                    kind = row.get("kind", "text")
                    if kind == "kv":
                        rows.append(("kv", row["key"], str(row.get("val", "")),
                                     row.get("val_col", C_GREY_LIGHT)))
                    elif kind == "text":
                        _wrap_text(row.get("text", ""), row.get("col", C_GREY_LIGHT))
                    elif kind == "gap":
                        rows.append(("gap",))
        elif lines:
            for text, col in lines:
                _wrap_text(text, col)

        ACCENT_H = 4
        title_h  = (f_b.get_linesize() + 5) if title else 0
        sub_h    = (lh_mi + 1) if subtitle else 0

        max_w = max(
            (f_b.size(title)[0]    if title    else 0),
            (f_mi.size(subtitle)[0] if subtitle else 0),
        )
        row_h = 0
        for row in rows:
            k = row[0]
            if k == "kv":
                max_w = max(max_w, f_mi.size(row[1] + ":  " + row[2])[0])
                row_h += lh_mi
            elif k == "text":
                max_w = max(max_w, f_mi.size(row[1])[0])
                row_h += lh_mi
            elif k == "div":
                row_h += 6
            elif k == "gap":
                row_h += lh_mi // 2

        total_w = min(max_w + PAD_TT * 2 + 8, 360)
        total_h = ACCENT_H + title_h + sub_h + row_h + PAD_TT * 2 + 4

        tx = mx + 16
        if tx + total_w > self._sw - 4:
            tx = mx - total_w - 8
        ty = my - total_h // 3
        ty = max(4, min(ty, self._sh - total_h - 4))

        panel = pygame.Rect(tx, ty, total_w, total_h)
        pygame.draw.rect(self.screen, C_PANEL,        panel, border_radius=5)
        pygame.draw.rect(self.screen, C_PANEL_BORDER, panel, 1, border_radius=5)

        pygame.draw.rect(self.screen, accent,
                         pygame.Rect(tx + 2, ty + 1, total_w - 4, ACCENT_H),
                         border_radius=3)

        cy = ty + ACCENT_H + PAD_TT // 2

        if title:
            self.screen.blit(f_b.render(title, True, C_WHITE), (tx + PAD_TT, cy))
            cy += f_b.get_linesize() + 2
            pygame.draw.line(self.screen, C_PANEL_BORDER,
                             (tx + 4, cy), (panel.right - 4, cy))
            cy += 3

        if subtitle:
            self.screen.blit(f_mi.render(subtitle, True, C_GREY_LIGHT), (tx + PAD_TT, cy))
            cy += lh_mi + 1

        cy += PAD_TT // 2

        for row in rows:
            k = row[0]
            if k == "kv":
                _, key, val, vcol = row
                ks = f_mi.render(key + ":", True, C_GREY_MID)
                vs = f_mi.render(val[:42],  True, vcol)
                self.screen.blit(ks, (tx + PAD_TT, cy))
                self.screen.blit(vs, (panel.right - PAD_TT - vs.get_width(), cy))
                cy += lh_mi
            elif k == "text":
                self.screen.blit(f_mi.render(row[1], True, row[2]), (tx + PAD_TT, cy))
                cy += lh_mi
            elif k == "div":
                mid = cy + 3
                pygame.draw.line(self.screen, C_PANEL_BORDER,
                                 (tx + 4, mid), (panel.right - 4, mid))
                cy += 6
            elif k == "gap":
                cy += lh_mi // 2

    # ─── PUBLIC API ───────────────────────────────────────────────────────────

    def show_toast(self, message: str, level: str = "info"):
        """Public wrapper for external callers (e.g. tutorial)."""
        self._toast(message, level)

    def add_number_pop(self, value, x, y, color=None, prefix=""):
        """Add a floating number pop-up animation."""
        self._pops.append(NumberPop(value, x, y,
                                    color=color, font=self._f("body"), prefix=prefix))

    @property
    def current_screen(self) -> GameScreen:
        """Return the current screen identifier."""
        return self.screen_name

    def go_to(self, screen: GameScreen):
        """Navigate to a screen (public alias for set_screen)."""
        self.set_screen(screen)
