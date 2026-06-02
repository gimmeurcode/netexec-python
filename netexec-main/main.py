"""
main.py — NETEXEC: Network Executive Simulator
===============================================
Entry point and main game loop.

Initialises pygame, creates the GameState and GameUI, then runs the
standard event-loop: handle events → update animations → render.

Running the game
----------------
  python main.py

Packaging with PyInstaller (see README.md for full command)
  pyinstaller --onefile --windowed --name NETEXEC main.py

The game requires Python 3.11+ and pygame (or pygame-ce).
Install with:  pip install pygame
"""

import sys
import os

# ── Make sure the script's directory is on the path so all module imports work
# regardless of the current working directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
from scripts.engine.constants import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, WINDOW_TITLE, C_BG
from scripts.engine.network   import GameState
from scripts.platform         import load_settings, save_settings
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
        from scripts.engine.constants import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_BUFFER
        pygame.mixer.pre_init(
            frequency=AUDIO_SAMPLE_RATE,
            size=-16,
            channels=AUDIO_CHANNELS,
            buffer=AUDIO_BUFFER,
        )
        pygame.mixer.init()
    except Exception:
        pass   # Game runs fine without audio

    # ── Window ───────────────────────────────────────────────────────────────
    pygame.display.set_caption(WINDOW_TITLE)
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)

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

    # ── Load persisted settings from %APPDATA%\NETEXEC\settings.json ─────────
    _s = load_settings()
    if _s:
        ui._settings_sfx_vol   = float(_s.get("sfx_vol",   ui._settings_sfx_vol))
        ui._settings_music_vol = float(_s.get("music_vol", ui._settings_music_vol))
        ui._settings_res_idx   = int(  _s.get("res_idx",   ui._settings_res_idx))
        ui._fullscreen         = bool( _s.get("fullscreen", ui._fullscreen))
        ui._tutorial_done      = bool( _s.get("tutorial_done", False))
        # Apply audio volumes immediately
        try:
            audio.set_sfx_volume(ui._settings_sfx_vol)
            audio.set_music_volume(ui._settings_music_vol)
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

            # Window resize — enforce minimum size, update ui surface reference
            elif event.type == pygame.VIDEORESIZE:
                try:
                    new_w = max(MIN_W, event.w)
                    new_h = max(MIN_H, event.h)
                    screen = pygame.display.set_mode(
                        (new_w, new_h), pygame.RESIZABLE
                    )
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
