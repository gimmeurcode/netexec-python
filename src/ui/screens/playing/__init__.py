"""
ui.screens.playing — NETEXEC PLAYING screen package
===================================================
The main gameplay screen, split into focused modules:

  dispatcher  render / render_game entry points + PlayingScreen
  header      HUD bar (season, budget, projection, AIR SEASON)
  schedule    left panel (slots, vault, contracts bar, upgrades, monopoly, seasonal)
  shop        right panel shell (tabs, scroll viewport, reroll)
  cards       shop item card drawing (shows/stars/ads/upgrades/events)
  contracts   contracts tab (available offers + active contracts)
  detail      show-detail modal

Importers use ``from ui.screens import playing`` and call
``playing.render`` / ``playing.render_game`` / ``playing.PlayingScreen``;
those names are re-exported here from ``dispatcher``.
"""

from .dispatcher import render, render_game, PlayingScreen

__all__ = ["render", "render_game", "PlayingScreen"]
