"""
screen_enum.py — NETEXEC
=========================
Enum that replaces the stringly-typed SCREEN_* constants used throughout
the UI system. Use GameScreen.X everywhere instead of string literals.
"""

from enum import Enum, auto


class GameScreen(Enum):
    MENU          = auto()
    SEED_SELECT   = auto()
    DIFFICULTY    = auto()
    EXECUTIVE_SELECT = auto()
    SETTINGS      = auto()
    PLAYING       = auto()
    SEASON_SUMMARY = auto()
    PAUSE         = auto()
    GAME_OVER     = auto()
    WIN           = auto()
    WILDCARD_SHOW = auto()
    WILDCARD_AD   = auto()
