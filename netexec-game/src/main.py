"""
main.py — NETEXEC: Network Executive Simulator
===============================================
Entry point and main game loop.

Initialises pygame, creates the GameState and GameUI, then runs the
standard event-loop: handle events → update animations → render.

Running the game (developer terminal launch)
--------------------------------------------
  python main.py              (from inside src/)
  python3 main.py             (macOS)

Building the standalone executable
-----------------------------------
  python netexec-dev/build/build_game.py
  Outputs NETEXEC.exe (Windows) or NETEXEC.app (macOS) into src/.

Installing for end users (no terminal required)
------------------------------------------------
  Windows : double-click netexec-windows/netexec-setup/install.vbs
  macOS   : double-click netexec-mac/netexec-setup/install.command

The game requires Python 3.11+ and pygame (or pygame-ce).
Install pygame with:  pip install pygame
"""

import sys
import os

# ── Make sure the script's directory is on the path so all module imports work
# regardless of the current working directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
from engine.constants import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, WINDOW_TITLE, C_BG
from engine.network   import GameState
from platform         import load_settings, save_settings
from ui.ui     import GameUI
from ui.audio  import AudioManager
from ui.layout import MIN_W, MIN_H


def main():
    """
    Initialise pygame and run the game loop until the window is closed.
    All logic is delegated to GameUI (rendering + input) and GameState (engine).
    """
    # ── pygame init ──────────────────────────────────────────────────────────
    pygame.init()

    # Attempt to initialise the mixer for audio; silently skip on failure.
    try:
        from engine.constants import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_BUFFER
        pygame.mixer.pre_init(
            frequency=AUDIO_SAMPLE_RATE,
            size=-16,
            channels=AUDIO_CHANNELS,
            buffer=AUDIO_BUFFER,
        )
        pygame.mixer.init()
    except Exception:
        pass   # Game runs fine without audio

    # ── Load persisted settings early (before window creation) ───────────────
    # Settings must be read here so saved resolution and fullscreen preference
    # can be applied to the very first pygame.display.set_mode call.
    from engine.constants import RESOLUTIONS
    _s = load_settings()
    _saved_sfx_vol    = float(_s.get("sfx_vol",       0.65))  if _s else 0.65
    _saved_music_vol  = float(_s.get("music_vol",     0.30))  if _s else 0.30
    _saved_res_idx    = int(  _s.get("res_idx",          2))  if _s else 2
    _saved_fullscreen = bool( _s.get("fullscreen",   False))  if _s else False
    _saved_tut_done   = bool( _s.get("tutorial_done", False)) if _s else False

    # ── Auto-detect monitor and pick best-fitting resolution preset ───────────
    # pygame.display.Info() must be called after pygame.init() and before the
    # first set_mode so it returns the true desktop resolution.
    try:
        _info  = pygame.display.Info()
        _mon_w = _info.current_w
        _mon_h = _info.current_h
    except Exception:
        _mon_w, _mon_h = 0, 0

    # Walk RESOLUTIONS from largest to smallest; keep the biggest that fits.
    _auto_idx = 0
    if _mon_w > 0 and _mon_h > 0:
        for _i, (_rw, _rh) in enumerate(RESOLUTIONS):
            if _rw <= _mon_w and _rh <= _mon_h:
                _auto_idx = _i   # last (largest) entry that fits

    # Respect the saved res_idx only if the window still fits the monitor.
    _res_idx = _saved_res_idx
    _chosen_rw, _chosen_rh = RESOLUTIONS[_res_idx % len(RESOLUTIONS)]
    if _mon_w > 0 and (_chosen_rw > _mon_w or _chosen_rh > _mon_h):
        # Saved choice is too large for this monitor — use auto-detected fit.
        _res_idx = _auto_idx
        _chosen_rw, _chosen_rh = RESOLUTIONS[_res_idx % len(RESOLUTIONS)]

    # ── Window ───────────────────────────────────────────────────────────────
    pygame.display.set_caption(WINDOW_TITLE)
    if _saved_fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((_chosen_rw, _chosen_rh), pygame.RESIZABLE)

    # Try to set a window icon via a procedurally drawn surface.
    try:
        icon = pygame.Surface((32, 32))
        icon.fill(C_BG)
        pygame.draw.rect(icon, (0, 200, 50), (4, 4, 24, 24), 2)
        pygame.draw.line(icon, (0, 200, 50), (4, 16), (28, 16), 1)
        pygame.display.set_icon(icon)
    except Exception:
        pass

    # ── Core objects ─────────────────────────────────────────────────────────
    state  = GameState()
    ui     = GameUI(screen)
    audio  = AudioManager()
    ui.audio = audio   # give UI access to audio for sound effects

    # ── Apply saved settings to the UI controller ─────────────────────────────
    ui._settings_sfx_vol   = _saved_sfx_vol
    ui._settings_music_vol = _saved_music_vol
    ui._settings_res_idx   = _res_idx
    ui._fullscreen         = _saved_fullscreen
    ui._tutorial_done      = _saved_tut_done
    try:
        audio.set_sfx_volume(_saved_sfx_vol)
        audio.set_music_volume(_saved_music_vol)
    except Exception:
        pass

    clock  = pygame.time.Clock()

    # ── Main loop ─────────────────────────────────────────────────────────────
    running = True
    while running:
        dt_ms = clock.tick(FPS)   # milliseconds since last frame

        # ── Event processing ─────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            # Window resize — enforce minimum size, update ui surface reference.
            # Handles both pygame 1.x (VIDEORESIZE) and pygame 2.x (WINDOWRESIZED).
            # In pygame 2.x the surface is already updated by the OS before the
            # event fires, so we read the actual size from get_surface() and only
            # call set_mode again if we need to enforce the minimum.
            elif event.type in (pygame.VIDEORESIZE,
                                getattr(pygame, "WINDOWRESIZED", -1)):
                try:
                    cur_surf = pygame.display.get_surface()
                    raw_w    = getattr(event, "w", cur_surf.get_width())
                    raw_h    = getattr(event, "h", cur_surf.get_height())
                    new_w    = max(MIN_W, raw_w)
                    new_h    = max(MIN_H, raw_h)
                    if (new_w, new_h) != cur_surf.get_size():
                        # Size changed or needs clamping — re-apply via set_mode
                        screen = pygame.display.set_mode(
                            (new_w, new_h), pygame.RESIZABLE
                        )
                    else:
                        screen = cur_surf
                    ui.screen = screen
                except Exception:
                    pass

            # Pass to UI (handles clicks, keyboard, etc.)
            ui.handle_event(event, state)

            # Tutorial click regions (tutorial draws over the game and needs
            # its own click registrations to be injected into the frame)
            if ui._tutorial and not ui._tutorial.done:
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    cut = ui._layout.cutout
                    tut_pos = (event.pos[0] - cut.x, event.pos[1] - cut.y)
                    for rect, cb in ui._tutorial.get_click_regions(ui._fonts, state):
                        if rect.collidepoint(tut_pos):
                            cb()
                            break

        # ── Update animations ─────────────────────────────────────────────────
        ui.update(dt_ms, state)

        # ── Render ────────────────────────────────────────────────────────────
        ui.render(state)

        # ── Clean up completed tutorial ───────────────────────────────────────
        if ui._tutorial and ui._tutorial.done:
            ui._tutorial      = None
            ui._tutorial_done = True
            # Immediately persist so the flag survives a crash before clean exit
            save_settings({
                "sfx_vol":       ui._settings_sfx_vol,
                "music_vol":     ui._settings_music_vol,
                "res_idx":       ui._settings_res_idx,
                "fullscreen":    ui._fullscreen,
                "tutorial_done": True,
            })

    # ── Shutdown ─────────────────────────────────────────────────────────────
    # Persist settings to %APPDATA%\NETEXEC\settings.json before exit
    save_settings({
        "sfx_vol":       ui._settings_sfx_vol,
        "music_vol":     ui._settings_music_vol,
        "res_idx":       ui._settings_res_idx,
        "fullscreen":    ui._fullscreen,
        "tutorial_done": ui._tutorial_done,
    })
    audio.stop_bg_music()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
