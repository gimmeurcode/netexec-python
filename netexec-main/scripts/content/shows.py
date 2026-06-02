"""
shows.py — NETEXEC
==================
Show pool management and show-specific helper operations.

Responsibilities:
  - Build the shuffled show pool at run start.
  - Pop shows from the pool to fill the shop.
  - Validate show placement (size, slot availability).
  - Provide show-specific queries (genre, age, slot occupation).

All data comes from cards.py loaders; no JSON is parsed here.
"""

from ..engine.cards import load_shows
from .cardpool import CardPool

# load_shows() returns (db, genre_registry, wildcard) → stored in pool.extra
_pool = CardPool(load_shows)


# ─── POOL MANAGEMENT ──────────────────────────────────────────────────────────

def build_pool() -> list:
    """
    Build a shuffled pool of all available shows including the wildcard.
    Called once at the start of each run to reset the draw pool.

    Returns
    -------
    list  Shuffled list of show dicts (copies; originals untouched).
    """
    return _pool.build()


def pop_for_shop(pool: list, count: int) -> list:
    """
    Pop up to `count` shows from the end of the pool and stamp them with
    unique shop UIDs. Stops early if the pool is exhausted.

    Parameters
    ----------
    pool  : list  The mutable show pool (modified in-place).
    count : int   Maximum number of shows to pop.

    Returns
    -------
    list  Shows with 'uid' fields added, ready for the shop.
    """
    return _pool.pop_for_shop(pool, count)


# ─── PLACEMENT VALIDATION ─────────────────────────────────────────────────────

def can_place_in_lineup(show: dict, idx: int, lineup: list) -> tuple[bool, str]:
    """
    Check whether a show can be placed at lineup[idx].

    Validates:
      - 2-slot shows cannot go to the vault.
      - 2-slot shows need at least two remaining adjacent slots.
      - idx must be in bounds.

    Parameters
    ----------
    show   : dict  The show dict being placed (must have 'size').
    idx    : int   Target lineup index (0–3).
    lineup : list  Current STATE.lineup (length 4).

    Returns
    -------
    (ok: bool, message: str)
      ok      True if placement is legal.
      message Human-readable reason when ok is False.
    """
    if idx < 0 or idx >= len(lineup):
        return False, "INVALID SLOT INDEX"
    if show.get("size", 1) == 2:
        if idx >= len(lineup) - 1:
            return False, "2-SLOT SHOW NEEDS TWO ADJACENT SLOTS"
    return True, ""


def can_place_in_vault(show: dict) -> tuple[bool, str]:
    """
    Check whether a show can be placed in the Syndication Vault.
    2-slot shows cannot be syndicated — the vault has fixed 1-slot entries.

    Parameters
    ----------
    show : dict

    Returns
    -------
    (ok: bool, message: str)
    """
    if show.get("size", 1) == 2:
        return False, "2-SLOT SHOWS CANNOT BE SYNDICATED"
    return True, ""


# ─── SHOW QUERIES ─────────────────────────────────────────────────────────────

def get_genre_registry() -> dict:
    """
    Return the full genre registry dict (genre id → {label, monopoly}).
    Used by network.py for monopoly detection.

    Returns
    -------
    dict
    """
    _pool._ensure_loaded()
    return _pool.extra or {}


def get_slot_indices(show: dict, start_idx: int) -> list:
    """
    Return the physical lineup indices occupied by a show.
    A size-1 show occupies [start_idx].
    A size-2 show occupies [start_idx, start_idx + 1].

    Parameters
    ----------
    show      : dict  Live show instance.
    start_idx : int   Index of the show's head slot.

    Returns
    -------
    list of int
    """
    if show.get("size", 1) == 2:
        return [start_idx, start_idx + 1]
    return [start_idx]


def all_live_shows(lineup: list) -> list:
    """
    Return all non-None, non-extension shows from the lineup.

    Parameters
    ----------
    lineup : list  STATE.lineup (length 4, may contain None or extension markers).

    Returns
    -------
    list  Live show dicts (no nulls, no extension markers).
    """
    return [s for s in lineup if s is not None and not s.get("is_extension")]
