"""
ads.py — NETEXEC
================
Ad pool management, dual-income helpers, and ad-specific validation.

Key mechanic: Dual-Income Ads.
  upfront_cash  — credited to STATE.budget immediately on placement.
  income        — earned every season via yield calculation.
  Net out-of-pocket = cost - upfront_cash (always > 0 by design).

Difficulty scaling: both upfront_cash and seasonal income are adjusted by
DifficultyManager.adjusted_ad_income() and adjusted_ad_upfront() before
being used in-game.
"""

from engine.cards import load_ads
from .cardpool import CardPool

# load_ads() returns (db, wildcard)
_pool = CardPool(load_ads)


# ─── POOL MANAGEMENT ──────────────────────────────────────────────────────────

def build_pool() -> list:
    """
    Build a shuffled pool of all available ads including the wildcard.

    Returns
    -------
    list  Shuffled ad dicts (copies; wildcard included once).
    """
    return _pool.build()


def pop_for_shop(pool: list, count: int) -> list:
    """
    Pop up to `count` ads from the pool with unique shop UIDs.

    Parameters
    ----------
    pool  : list  Mutable ad pool (modified in-place).
    count : int   Maximum number of ads to pop.

    Returns
    -------
    list  Ads with 'uid' added.
    """
    return _pool.pop_for_shop(pool, count)


# ─── AD HELPERS ───────────────────────────────────────────────────────────────

def can_attach_to_show(show: dict) -> tuple[bool, str]:
    """
    Check whether an ad can be attached to the given show (slot availability).

    Parameters
    ----------
    show : dict  Live show instance (has 'ad_slots' and 'attached').

    Returns
    -------
    (ok: bool, message: str)
    """
    max_slots   = show.get("ad_slots", show.get("slots", {}).get("ad", 0))
    current_ads = len(show.get("attached", {}).get("ad", []))
    if current_ads >= max_slots:
        return False, "AD SLOTS FULL"
    return True, ""


def upfront_payment(ad: dict, state) -> int:
    """
    Return the signing bonus credited when the ad is placed, adjusted for
    current difficulty.

    Parameters
    ----------
    ad    : dict  Ad dict (has 'upfront_cash').
    state : GameState

    Returns
    -------
    int  Dollars credited to state.budget.
    """
    from engine.difficulty import DifficultyManager
    return DifficultyManager.adjusted_ad_upfront(state, ad.get("upfront_cash", 0))


def net_cost(ad: dict, state) -> float:
    """
    Return the net out-of-pocket cost of placing an ad.
    = rnd2(ad.cost) - rnd2(upfront_payment) (always ≥ 1 by data convention).

    Parameters
    ----------
    ad    : dict
    state : GameState

    Returns
    -------
    float  Net dollars deducted from budget.
    """
    from engine.network import rnd2
    return rnd2(ad.get("cost", 0)) - rnd2(upfront_payment(ad, state))


def wildcard_template() -> dict | None:
    """
    Return a copy of the wildcard ad template (or None if unavailable).
    The caller must stamp a target genre and uid before use.

    Returns
    -------
    dict or None
    """
    wc = _pool.wildcard()
    return dict(wc) if wc else None
