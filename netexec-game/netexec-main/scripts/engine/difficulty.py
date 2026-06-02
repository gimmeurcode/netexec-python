"""
difficulty.py — NETEXEC
=======================
Manages per-run difficulty settings and network prestige scaling.

Two separate difficulty axes:
  1. Player-chosen difficulty (EASY / NORMAL / HARD / BRUTAL) — chosen at the
     start of each run and stored in GameState.difficulty. Affects starting
     budget, view targets, star costs, and ad income.

  2. Network Prestige — auto-increments each run. Raises the opening milestone
     quota and the milestone growth rate so each successive run is harder.

The DifficultyManager class is a stateless helper — it reads from the shared
GameState and constants, never stores its own copy of game data.
"""

from .constants import (
    DIFFICULTY_LEVELS,
    BASE_VIEW_TARGET,
    TARGET_GROWTH_RATE,
    PRESTIGE_TARGET_SCALE,
    PRESTIGE_GROWTH_BONUS,
    INITIAL_BUDGET,
)


class DifficultyManager:
    """Stateless helper that computes difficulty-adjusted values from a GameState."""

    # ─── EFFECTIVE STARTING VALUES ────────────────────────────────────────────

    @staticmethod
    def effective_starting_budget(state) -> int:
        """Return the starting budget after applying difficulty budget_mod."""
        diff   = DIFFICULTY_LEVELS.get(state.difficulty, DIFFICULTY_LEVELS["NORMAL"])
        budget = INITIAL_BUDGET + diff["budget_mod"]
        # Clamp to a minimum of $10 so Brutal doesn't leave the player broke.
        return max(10, budget)

    @staticmethod
    def effective_opening_target(state) -> int:
        """Compute the Season-3 view quota applying difficulty target_mult and prestige scaling."""
        diff    = DIFFICULTY_LEVELS.get(state.difficulty, DIFFICULTY_LEVELS["NORMAL"])
        prestige_scale = 1.0 + state.network_prestige * PRESTIGE_TARGET_SCALE
        base    = BASE_VIEW_TARGET * prestige_scale
        target  = int(round(base * diff["target_mult"])) + diff["rival_pressure"]
        return max(100, target)   # floor at 100 so the game is always winnable

    @staticmethod
    def effective_growth_rate(state) -> float:
        """Compute the milestone growth multiplier with difficulty and prestige applied."""
        diff = DIFFICULTY_LEVELS.get(state.difficulty, DIFFICULTY_LEVELS["NORMAL"])
        rate = (
            TARGET_GROWTH_RATE
            + state.network_prestige * PRESTIGE_GROWTH_BONUS
            + diff["growth_mod"]
        )
        # Clamp: growth rate must be at least 1.5 (meaningful progression)
        # and at most 5.0 (Brutal prestige cap — avoid overflow).
        return max(1.5, min(5.0, rate))

    # ─── ITEM COST / INCOME MODIFIERS ────────────────────────────────────────

    @staticmethod
    def adjusted_star_cost(state, base_cost: int) -> int:
        """Return the star's purchase price after difficulty star_cost_mult scaling."""
        diff = DIFFICULTY_LEVELS.get(state.difficulty, DIFFICULTY_LEVELS["NORMAL"])
        return max(1, round(base_cost * diff["star_cost_mult"]))

    @staticmethod
    def adjusted_ad_income(state, base_income: int) -> int:
        """Return an ad's seasonal income after difficulty ad_income_mult scaling."""
        diff = DIFFICULTY_LEVELS.get(state.difficulty, DIFFICULTY_LEVELS["NORMAL"])
        if base_income >= 0:
            return round(base_income * diff["ad_income_mult"])
        else:
            # Negative income penalty grows (more negative) on harder difficulties.
            return round(base_income / diff["ad_income_mult"])

    @staticmethod
    def adjusted_ad_upfront(state, base_upfront: int) -> int:
        """Return an ad's upfront signing bonus after difficulty scaling."""
        diff = DIFFICULTY_LEVELS.get(state.difficulty, DIFFICULTY_LEVELS["NORMAL"])
        return max(0, round(base_upfront * diff["ad_income_mult"]))

    # ─── PRESTIGE INFO ────────────────────────────────────────────────────────

    @staticmethod
    def prestige_summary(state) -> dict:
        """Return a human-readable snapshot of prestige difficulty for UI display."""
        dm = DifficultyManager
        return {
            "prestige":         state.network_prestige,
            "opening_quota":    dm.effective_opening_target(state),
            "growth_rate":      round(dm.effective_growth_rate(state), 2),
            "difficulty_label": state.difficulty,
        }

    # ─── NEWS MONOPOLY HOOK ───────────────────────────────────────────────────

    @staticmethod
    def apply_news_monopoly(current_target: int) -> int:
        """Apply NEWS monopoly target reduction; return the reduced target integer."""
        # 0.88 reduction factor matches shows.json NEWS monopoly definition
        return max(1, int(round(current_target * 0.88)))
