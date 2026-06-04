"""
network.py — NETEXEC (compatibility shim)
=========================================
network.py was split into two focused modules:

  engine.yields  — the stateless per-show yield pipeline (calculate_yield, ...).
  engine.state   — the GameState container and all game-flow logic.

This module re-exports their public names so existing imports
(``from engine.network import GameState, calculate_yield, rnd2``) keep working.
New code should import from engine.state / engine.yields directly.
"""

from .yields import (  # noqa: F401
    rnd2, _get_age_mult, calculate_yield,
)
from .state import GameState  # noqa: F401

__all__ = ["GameState", "calculate_yield", "rnd2", "_get_age_mult"]
