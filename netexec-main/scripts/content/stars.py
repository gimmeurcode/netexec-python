"""
stars.py — NETEXEC
==================
Star pool management and star-specific helper operations.
"""

from ..engine.cards import load_stars
from .cardpool import CardPool

# load_stars() returns (db, wildcard) — wildcard is None in the base game
_pool = CardPool(load_stars)


# ─── POOL MANAGEMENT ──────────────────────────────────────────────────────────

def build_pool() -> list:
    """
    Build a shuffled pool of all available stars.
    Called once at the start of each run.

    Returns
    -------
    list  Shuffled list of star dicts (copies).
    """
    return _pool.build()


def pop_for_shop(pool: list, count: int) -> list:
    """
    Pop up to `count` stars from the pool with unique shop UIDs.

    Parameters
    ----------
    pool  : list  Mutable star pool (modified in-place).
    count : int   Maximum number of stars to pop.

    Returns
    -------
    list  Stars with 'uid' added.
    """
    return _pool.pop_for_shop(pool, count)


# ─── STAR HELPERS ─────────────────────────────────────────────────────────────

def can_attach_to_show(show: dict) -> tuple[bool, str]:
    """
    Check whether a star can be attached to the given show (slot availability).

    Parameters
    ----------
    show : dict  Live show instance (has 'star_slots' and 'attached').

    Returns
    -------
    (ok: bool, message: str)
    """
    max_slots     = show.get("star_slots", show.get("slots", {}).get("star", 0))
    current_stars = len(show.get("attached", {}).get("star", []))
    if current_stars >= max_slots:
        return False, "STAR SLOTS FULL"
    return True, ""


def condition_fires(star: dict, show: dict) -> bool:
    """
    Quick check whether a star's primary condition fires on a show.
    Used by the UI to colour-code star cards (green = fires, amber = fallback).

    Parameters
    ----------
    star : dict
    show : dict

    Returns
    -------
    bool
    """
    from ..engine.cards import check_condition
    return check_condition(star.get("condition"), show)
