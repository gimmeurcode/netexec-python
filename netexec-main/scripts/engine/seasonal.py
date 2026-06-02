"""
seasonal.py — NETEXEC
======================
Seasonal event roll, modifier aggregation, and reward/penalty application.

Used exclusively by GameState.advance_season().  Public API:

  roll_seasonal_event(season, last_event_id, rng)
      Weighted-random draw from events that are eligible this season.

  aggregate_seasonal_mods(active_modifiers)
      Collapse all active modifier-kind events into one effect dict.

  apply_reward(reward, state) → str
      Mutate state with a contract/mandate reward; return description.

  apply_penalty(penalty, state) → str
      Mutate state with a contract/mandate penalty; return description.

  build_offers(season, active_ids, rng) → list[dict]
      Pick 1-2 offerable contracts for the offers board.

The events list is loaded lazily once per process from data/seasonal_events.json
via cards.load_seasonal_events().
"""

from __future__ import annotations

import random
from typing import Any


# ─── LAZY LOADER ─────────────────────────────────────────────────────────────

_EVENTS: list = []
_LOADED: bool = False


def _load() -> None:
    global _EVENTS, _LOADED
    if _LOADED:
        return
    from .cards import load_seasonal_events
    _EVENTS = load_seasonal_events()
    _LOADED = True


# ─── SEASONAL EVENT ROLL ─────────────────────────────────────────────────────

def roll_seasonal_event(
    season: int,
    last_event_id: str | None,
    rng: random.Random | None = None,
) -> dict | None:
    """Roll a weighted-random seasonal event for the given season; return event dict or None."""
    _load()
    if rng is None:
        rng = random

    candidates = [
        e for e in _EVENTS
        if e.get("min_season", 1) <= season
        and e.get("id") != last_event_id
        and not e.get("is_offerable", False)   # offerable contracts are drawn separately
    ]
    if not candidates:
        return None

    weights = [max(1, e.get("weight", 1)) for e in candidates]
    return rng.choices(candidates, weights=weights, k=1)[0]


# ─── OFFERS BOARD ────────────────────────────────────────────────────────────

def build_offers(
    season: int,
    active_contract_ids: set[str],
    rng: random.Random | None = None,
    count: int = 2,
) -> list[dict]:
    """Pick up to `count` offerable contracts for the player's offers board; return list."""
    _load()
    if rng is None:
        rng = random

    candidates = [
        e for e in _EVENTS
        if e.get("is_offerable", False)
        and e.get("min_season", 1) <= season
        and e.get("id") not in active_contract_ids
        and e.get("kind") == "contract"
    ]
    if not candidates:
        return []

    weights = [max(1, e.get("weight", 1)) for e in candidates]
    k       = min(count, len(candidates))
    chosen  = rng.choices(candidates, weights=weights, k=k)
    # de-duplicate (choices() can repeat)
    seen   = set()
    result = []
    for ev in chosen:
        if ev["id"] not in seen:
            seen.add(ev["id"])
            result.append(ev)
    return result


# ─── MODIFIER AGGREGATION ────────────────────────────────────────────────────

def aggregate_seasonal_mods(active_modifiers: list) -> dict:
    """Collapse all active modifier-kind events into one combined effect dict."""
    result: dict = {
        "view_mult":       1.0,
        "upkeep_mult":     1.0,
        "income_flat":     0.0,
        "genre_view_mult": {},
    }
    for entry in active_modifiers:
        effects = entry.get("event", {}).get("effects", {})
        result["view_mult"]   *= effects.get("view_mult",   1.0)
        result["upkeep_mult"] *= effects.get("upkeep_mult", 1.0)
        result["income_flat"] += effects.get("income_flat", 0.0)
        for genre, mult in effects.get("genre_view_mult", {}).items():
            prev = result["genre_view_mult"].get(genre, 1.0)
            result["genre_view_mult"][genre] = prev * mult
    return result


# ─── REWARD / PENALTY APPLICATION ────────────────────────────────────────────

def apply_reward(reward: dict, state: Any) -> str:
    """Apply a contract reward to the game state; return a human-readable description."""
    msgs = []
    budget = int(reward.get("budget_bonus", 0))
    views  = int(reward.get("views_bonus",  0))
    if budget:
        state.budget      += budget
        msgs.append(f"+${budget}")
    if views:
        state.total_views += views
        msgs.append(f"+{views} views")
    return ", ".join(msgs) if msgs else "Reward applied"


def apply_penalty(penalty: dict, state: Any) -> str:
    """Apply a contract/mandate penalty to the game state; return a human-readable description."""
    msgs = []
    budget = int(penalty.get("budget_loss", 0))
    views  = int(penalty.get("views_loss",  0))
    if budget:
        state.budget      -= budget
        msgs.append(f"-${budget}")
    if views:
        state.total_views  = max(0, state.total_views - views)
        msgs.append(f"-{views} views")
    return ", ".join(msgs) if msgs else "Penalty applied"
