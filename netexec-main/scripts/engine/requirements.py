"""
requirements.py — NETEXEC
==========================
Shared declarative requirement evaluator.

Used by seasonal mandates, seasonal contracts, and the offers board.
Each requirement is a plain dict with a "type" key; evaluate() dispatches
to the registered handler for that type.

Requirement types
-----------------
  air_genre_count    N+ shows of a given genre in the live lineup
  reach_views        state.total_views >= value  (checked after season yields)
  attach_stars_count N+ stars attached across all live lineup shows
  air_in_slot        at least one show occupying the specified slot index
  avoid_genre        no shows of the specified genre in the live lineup
  min_budget         state.budget >= value

Adding a new type
-----------------
  1. Decorate a function with @requirement_handler("your_type").
  2. The function receives (req: dict, state: GameState) → bool.
  3. No other files need changing.
"""

from __future__ import annotations

from typing import Any

_REGISTRY: dict = {}


def requirement_handler(req_type: str):
    """Register a callable as the evaluator for a requirement type; use as decorator."""
    def decorator(fn):
        _REGISTRY[req_type] = fn
        return fn
    return decorator


def get_registered_requirement_types() -> set:
    """Return all requirement type strings that have a registered handler."""
    return set(_REGISTRY.keys())


# ─── HANDLERS ─────────────────────────────────────────────────────────────────

@requirement_handler("air_genre_count")
def _check_air_genre_count(req: dict, state: Any) -> bool:
    genre   = req.get("genre", "")
    count   = req.get("count", 1)
    live    = [
        s for s in state.lineup
        if s and not s.get("is_extension") and s.get("genre") == genre
    ]
    return len(live) >= count


@requirement_handler("reach_views")
def _check_reach_views(req: dict, state: Any) -> bool:
    return state.total_views >= req.get("value", 0)


@requirement_handler("attach_stars_count")
def _check_attach_stars_count(req: dict, state: Any) -> bool:
    count = req.get("count", 1)
    total = sum(
        len(s.get("attached", {}).get("star", []))
        for s in state.lineup
        if s and not s.get("is_extension")
    )
    return total >= count


@requirement_handler("air_in_slot")
def _check_air_in_slot(req: dict, state: Any) -> bool:
    slot = req.get("slot", 0)
    if 0 <= slot < len(state.lineup):
        s = state.lineup[slot]
        return s is not None and not s.get("is_extension")
    return False


@requirement_handler("avoid_genre")
def _check_avoid_genre(req: dict, state: Any) -> bool:
    genre = req.get("genre", "")
    live  = [
        s for s in state.lineup
        if s and not s.get("is_extension") and s.get("genre") == genre
    ]
    return len(live) == 0


@requirement_handler("min_budget")
def _check_min_budget(req: dict, state: Any) -> bool:
    return state.budget >= req.get("value", 0)


# ─── PUBLIC API ───────────────────────────────────────────────────────────────

def evaluate(requirement: dict, state: Any) -> bool:
    """Evaluate a single requirement against the current game state; return True if satisfied."""
    rtype   = requirement.get("type", "")
    handler = _REGISTRY.get(rtype)
    if handler is None:
        return False   # unknown type → treat as unmet (safe for penalties)
    return handler(requirement, state)


def describe(requirement: dict) -> str:
    """Return a short human-readable description of a requirement."""
    rtype = requirement.get("type", "")
    if rtype == "air_genre_count":
        return (
            f"Air {requirement.get('count', 1)}+ "
            f"{requirement.get('genre', '?')} shows"
        )
    if rtype == "reach_views":
        return f"Reach {requirement.get('value', 0):,} total views"
    if rtype == "attach_stars_count":
        return f"Attach {requirement.get('count', 1)}+ stars"
    if rtype == "air_in_slot":
        try:
            from .constants import TIME_SLOTS
            slot  = requirement.get("slot", 0)
            label = TIME_SLOTS[slot]["label"] if 0 <= slot < len(TIME_SLOTS) else f"Slot {slot}"
        except ImportError:
            label = f"Slot {requirement.get('slot', 0)}"
        return f"Air a show in {label}"
    if rtype == "avoid_genre":
        return f"No {requirement.get('genre', '?')} shows on air"
    if rtype == "min_budget":
        return f"Budget >= ${requirement.get('value', 0)}"
    return "Special condition"
