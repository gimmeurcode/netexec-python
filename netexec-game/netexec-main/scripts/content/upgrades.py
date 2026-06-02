"""
upgrades.py — NETEXEC
=====================
Upgrade pool management.

Upgrades are global — once purchased they apply to every show every season.
Max 5 active upgrades at once (MAX_ACTIVE_UPGRADES from constants.py).
The actual perk logic lives in network.py's _apply_perk() method.
"""

from ..engine.cards import load_upgrades
from .cardpool import CardPool

# load_upgrades() returns a plain list — no wildcard
_pool = CardPool(load_upgrades)


# ─── POOL MANAGEMENT ──────────────────────────────────────────────────────────

def build_pool() -> list:
    """
    Build a shuffled pool of all available upgrades.
    No wildcard upgrade exists in the base game.

    Returns
    -------
    list  Shuffled upgrade dicts (copies).
    """
    return _pool.build()


def pop_for_shop(pool: list, count: int) -> list:
    """
    Pop up to `count` upgrades from the pool with unique shop UIDs.

    Parameters
    ----------
    pool  : list  Mutable upgrade pool.
    count : int   Maximum items to pop.

    Returns
    -------
    list  Upgrades with 'uid' added.
    """
    return _pool.pop_for_shop(pool, count)


# ─── UPGRADE HELPERS ──────────────────────────────────────────────────────────

def is_already_owned(upg: dict, active_perks: list) -> bool:
    """
    Check whether an upgrade is already in the player's active perks.
    Prevents duplicate purchases of the same upgrade ID.

    Parameters
    ----------
    upg          : dict  Upgrade from the shop.
    active_perks : list  Current STATE.active_perks.

    Returns
    -------
    bool
    """
    return any(p["id"] == upg["id"] for p in active_perks)
