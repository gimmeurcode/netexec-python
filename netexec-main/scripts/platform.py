"""
platform.py — NETEXEC
======================
Platform abstraction layer (Steam stub).

All persistence, achievements, leaderboards, and cloud saves go through
this module.  Currently implemented as a local-filesystem stub:
  - Save data: %%APPDATA%%\\NETEXEC  (Windows)
               ~/.config/NETEXEC  (Linux/macOS)
  - Achievements / leaderboards: logged to console only.
  - Cloud saves: no-op (saves are local-only until Steamworks is integrated).

To swap in Steamworks later, replace only this file.  The rest of the game
calls get_save_dir(), load_settings(), save_settings(), etc. — none of those
callers need to change.
"""

import os
import json
import logging

logger = logging.getLogger(__name__)


# ─── SAVE DIRECTORY ───────────────────────────────────────────────────────────

def get_save_dir() -> str:
    """
    Return the canonical save-data directory for the current OS.
    Creates it on first call if it does not already exist.

    Returns
    -------
    str  Absolute path to the save directory.
    """
    if os.name == "nt":
        # Windows: %APPDATA%\NETEXEC  (e.g. C:\Users\Alice\AppData\Roaming\NETEXEC)
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        # Linux / macOS: ~/.config/NETEXEC
        base = os.environ.get("XDG_CONFIG_HOME",
                              os.path.join(os.path.expanduser("~"), ".config"))
    path = os.path.join(base, "NETEXEC")
    os.makedirs(path, exist_ok=True)
    return path


# ─── SETTINGS ────────────────────────────────────────────────────────────────

def load_settings() -> dict:
    """
    Load settings.json from the save directory.

    Returns
    -------
    dict  Persisted settings, or {} if the file is missing or corrupted.
    """
    path = os.path.join(get_save_dir(), "settings.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_settings(data: dict) -> None:
    """
    Write settings.json to the save directory.

    Parameters
    ----------
    data : dict  Settings to persist (must be JSON-serialisable).
    """
    path = os.path.join(get_save_dir(), "settings.json")
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        logger.debug("[platform] Settings saved to %s", path)
    except OSError as exc:
        logger.warning("[platform] Failed to save settings: %s", exc)


# ─── GAME SAVES ──────────────────────────────────────────────────────────────

def save_game(slot: int, data: dict) -> None:
    """
    Write a game-state snapshot to save_<slot>.json in the save directory.

    Parameters
    ----------
    slot : int   Save-slot index (0-based).
    data : dict  Serialisable game-state snapshot.
    """
    path = os.path.join(get_save_dir(), f"save_{slot}.json")
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        logger.info("[platform] Game saved → %s", path)
    except OSError as exc:
        logger.warning("[platform] Failed to save game: %s", exc)


def load_game(slot: int) -> dict | None:
    """
    Load a game-state snapshot from save_<slot>.json.

    Parameters
    ----------
    slot : int  Save-slot index.

    Returns
    -------
    dict  The saved game state, or None if the file is missing / corrupted.
    """
    path = os.path.join(get_save_dir(), f"save_{slot}.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        logger.info("[platform] Game loaded ← %s", path)
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return None


# ─── ACHIEVEMENTS (STUB) ─────────────────────────────────────────────────────

def unlock_achievement(achievement_id: str) -> None:
    """
    Unlock a Steam achievement.
    Currently logs to console only — no Steamworks call is made.

    Parameters
    ----------
    achievement_id : str  The Steamworks achievement API name.
    """
    logger.info("[platform] Achievement unlocked: %s", achievement_id)
    print(f"[ACHIEVEMENT] {achievement_id}")


def get_achievement(achievement_id: str) -> bool:
    """
    Check whether a Steam achievement is unlocked.
    Stub always returns False.

    Parameters
    ----------
    achievement_id : str

    Returns
    -------
    bool  Always False until Steamworks is integrated.
    """
    logger.debug("[platform] Achievement check (stub): %s → False", achievement_id)
    return False


# ─── LEADERBOARDS (STUB) ─────────────────────────────────────────────────────

def upload_score(leaderboard_name: str, score: int) -> None:
    """
    Upload a score to a Steam leaderboard.
    Currently logs to console only.

    Parameters
    ----------
    leaderboard_name : str  Steamworks leaderboard name.
    score            : int  Score to submit.
    """
    logger.info("[platform] Leaderboard upload: %s = %d", leaderboard_name, score)
    print(f"[LEADERBOARD] {leaderboard_name}: {score}")


def get_leaderboard(leaderboard_name: str) -> list:
    """
    Fetch entries from a Steam leaderboard.
    Stub always returns an empty list.

    Parameters
    ----------
    leaderboard_name : str

    Returns
    -------
    list  Always [] until Steamworks is integrated.
    """
    logger.debug("[platform] Leaderboard fetch (stub): %s → []", leaderboard_name)
    return []


# ─── CLOUD SAVES (STUB) ──────────────────────────────────────────────────────

def cloud_sync() -> None:
    """
    Trigger a Steam cloud-save sync.
    Currently a no-op — all saves are local-only.
    """
    logger.debug("[platform] Cloud sync requested (stub — local saves only)")
