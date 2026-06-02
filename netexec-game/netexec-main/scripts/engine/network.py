"""
network.py — NETEXEC
====================
Core game state container and all game logic.

This module is the single source of truth for the in-memory game state.
The UI and tutorial read from GameState and call engine methods to mutate it —
they never write to state fields directly.

Systems implemented here:
  GameState          Mutable state container.
  calculate_yield()  Pure per-show season view/income math (port of JS pipeline).
  GameState.start_new_run()     Reset state, rebuild pools, choose difficulty.
  GameState.generate_shop()     Refresh shop from pools.
  GameState.attempt_purchase()  Buy an item (upgrade/event fires; show/star/ad queues).
  GameState.place_selected()    Place a queued show/star/ad onto a slot.
  GameState.advance_season()    Run one season: calc yields, check milestone.
  GameState.sell_show()         Cancel/sell a show for a partial refund.
  GameState.move_to_vault()     Syndicate a live show to the vault.
  GameState.reroll_shop()       Pay $5 to refresh the shop.
  GameState.get_lineup_summary() Query monopoly and fill state for UI.

Seasonal events (added Prompt 11):
  GameState.active_seasonal_modifiers  Ongoing modifier events.
  GameState.active_contracts           Accepted/auto-attached contracts.
  GameState.active_mandates            Ongoing mandate events.
  GameState.available_contracts        Offers board — player may accept this season.
  GameState.accept_contract()          Accept an offer-board contract.
  GameState.accept_bailout()           Take a bailout (loan or grant) when in the red.
  GameState.aggregate_seasonal_mods()  Collapse active modifiers for calculate_yield.
"""

import math
import random

from .. import platform as _platform
from .constants import (
    MAX_SEASONS, INITIAL_BUDGET, MAX_RERUN_SLOTS, REROLL_BASE_COST,
    BASE_INCOME, MAX_ACTIVE_UPGRADES, TARGET_INTERVAL,
    BASE_VIEW_TARGET, TARGET_GROWTH_RATE, MILESTONE_REWARD,
    SELL_REFUND_RATE, STAR_REFUND_RATE, SHOP_SHOW_COUNT, SHOP_STAR_COUNT,
    SHOP_AD_COUNT, SHOP_UPG_COUNT, SHOP_EVENT_COUNT,
    AGE_MULTIPLIERS, SLOT_PENALTY_MULT, DIFFICULTY_LEVELS,
    DEFAULT_DIFFICULTY, TIME_SLOTS,
)
from .cards import (
    evaluate_star, evaluate_ad, make_show_instance, stamp_uids,
)
from .difficulty import DifficultyManager
from .effects import resolve_upgrade_effects, resolve_vault_rerun
from .requirements import evaluate as eval_requirement, describe as describe_requirement
from . import seasonal as seasonal_mod
from ..content import shows   as show_pool
from ..content import stars   as star_pool
from ..content import ads     as ad_pool
from ..content import upgrades as upg_pool
from ..content import events   as event_pool


# ─── ROUNDING HELPER ─────────────────────────────────────────────────────────

def rnd2(x: float) -> float:
    """Deterministic half-up rounding to 2 decimal places (avoids banker's rounding)."""
    return math.floor(x * 100 + 0.5) / 100


# ─── AGE MULTIPLIER LOOKUP ────────────────────────────────────────────────────

def _get_age_mult(age: int) -> float:
    """
    Look up the lifecycle decay multiplier for a show's current age.

    Parameters
    ----------
    age : int  Number of seasons the show has aired (1-indexed).

    Returns
    -------
    float  View multiplier (e.g. 1.25 at age 2, 0.45 at age 7+).
    """
    for (mn, mx, mult) in AGE_MULTIPLIERS:
        if mn <= age <= mx:
            return mult
    return 1.0


# ─── YIELD PIPELINE STAGES ──────────────────────────────────────────────────────────
#
# Each _stage_* function handles exactly one documented pipeline step.
# They are pure functions — no mutations, no shared state.
# The orchestrator (calculate_yield) calls them in the invariant order
# documented in its docstring.

def _stage_upkeep(show: dict, slot_indices: list, is_rerun: bool,
                  monopoly_bonus: dict = None) -> float:
    """Stage 1: effective upkeep. Late Night (slot 3) halves it; reruns pay nothing.
    SITCOM monopoly (upkeep_halved) further multiplies upkeep by 0.5."""
    upkeep = 0.0 if is_rerun else float(show.get("upkeep", 0))
    if not is_rerun and 3 in slot_indices:
        upkeep *= 0.5
    if monopoly_bonus and not is_rerun:
        if monopoly_bonus.get("type") == "upkeep_halved":
            upkeep *= monopoly_bonus.get("upkeep_mult", 0.5)
    return upkeep


def _stage_base_views(show: dict, slot_indices: list, is_rerun: bool) -> float:
    """Stage 2: base views with Afternoon (slot 1) +10% inflation."""
    v = float(show.get("base_views", 0))
    if not is_rerun and 1 in slot_indices:
        v *= 1.1
    return v


def _stage_stars(show: dict, slot_indices: list, is_rerun: bool,
                 monopoly_bonus: dict = None) -> tuple:
    """
    Stage 3: star contributions → (v_add, mult_factor, star_income, upkeep_add).

    Prime Time (slot 2) amplifies only the *bonus* portion of v_mult so that
    a ×1.5 star becomes ×1.75: ((1.5 − 1.0) × 1.5) + 1.0 = 1.75.
    Stars with v_mult ≤ 1.0 are not amplified.
    SCIFI monopoly (star_amplifier) overrides the prime-time multiplier to apply
    across ALL slots at an elevated level (default 2.5×).
    """
    star_prime_mult = 1.5 if (not is_rerun and 2 in slot_indices) else 1.0
    # SCIFI monopoly: star bonuses amplified across all slots
    if monopoly_bonus and not is_rerun:
        if monopoly_bonus.get("type") == "star_amplifier":
            amp = monopoly_bonus.get("star_prime_mult", 2.5)
            star_prime_mult = max(star_prime_mult, amp)
    v_add       = 0.0
    mult_factor = 1.0
    star_income = 0.0
    upkeep_add  = 0.0
    for star in show.get("attached", {}).get("star", []):
        eff = evaluate_star(star, show)
        v_add      += eff["v_flat"]
        upkeep_add += eff["upkeep"]
        if not is_rerun:
            star_income += eff["income"]
        vm = eff["v_mult"]
        if vm > 1.0:
            mult_factor *= ((vm - 1.0) * star_prime_mult) + 1.0
    return v_add, mult_factor, star_income, upkeep_add


def _stage_ads(show: dict, slot_indices: list, is_rerun: bool,
               monopoly_bonus: dict = None) -> tuple:
    """
    Stage 4: ad contributions → (v_add, mult_factor, ad_income).

    Morning (slot 0) scales positive ad income by ×1.2.
    Negative-income ads (e.g. Sludge Cola, RivalStream) pass through unscaled.
    Ad v_mults (positive or negative) apply unconditionally to the view mult.
    REALITY monopoly (ad_multiplier) further scales all positive ad income by ad_mult.
    """
    morning_scale = 1.2 if (not is_rerun and 0 in slot_indices) else 1.0
    reality_mult  = 1.0
    if monopoly_bonus and not is_rerun:
        if monopoly_bonus.get("type") == "ad_multiplier":
            reality_mult = monopoly_bonus.get("ad_mult", 1.5)
    v_add       = 0.0
    mult_factor = 1.0
    ad_income   = 0.0
    for ad in show.get("attached", {}).get("ad", []):
        eff = evaluate_ad(ad, show)
        v_add += eff["v_flat"]
        if not is_rerun:
            raw = eff["income"]
            ai = round(raw * morning_scale) if raw > 0 else raw
            if ai > 0:
                ai = round(ai * reality_mult)
            ad_income += ai
        vm = eff["v_mult"]
        if vm != 1.0:
            mult_factor *= vm
    return v_add, mult_factor, ad_income


def _stage_upgrades(active_perks: list, show: dict, slot_indices: list,
                    is_rerun: bool, season: int) -> tuple:
    """Stage 5: global upgrade perk contributions → (v_add, mult_factor, income_add)."""
    v_add       = 0.0
    mult_factor = 1.0
    income_add  = 0.0
    for perk in active_perks:
        pv, pm, pi = resolve_upgrade_effects(perk, show, slot_indices, is_rerun, season)
        v_add      += pv
        mult_factor *= pm
        income_add  += pi
    return v_add, mult_factor, income_add


def _stage_monopoly(mult: float, income: float,
                    monopoly_bonus, is_rerun: bool) -> tuple:
    """
    Stage 6: genre monopoly bonus → (new_mult, new_income).

    Live shows only. Handled by type:
      views_income   — mult × views_mult, income + income_bonus  (DRAMA, SPORTS)
      upkeep_halved  — upkeep handled in Stage 1; income + income_bonus  (SITCOM)
      star_amplifier — star mult handled in Stage 3; mult × views_mult, income + income_bonus  (SCIFI)
      ad_multiplier  — ad income handled in Stage 4; mult × views_mult, income + income_bonus  (REALITY)
      target_reduction — quota handled in advance_season(); income + income_bonus  (NEWS)
      budget_boost   — direct budget applied in advance_season(); mult × views_mult  (COOKING)
    """
    if monopoly_bonus and not is_rerun:
        mono_type = monopoly_bonus.get("type", "views_income")
        mult   *= monopoly_bonus.get("views_mult", 1.0)
        if mono_type != "budget_boost":
            income += monopoly_bonus.get("income_bonus", 0)
    return mult, income


def _stage_seasonal(mult: float, income: float, upkeep: float,
                    seasonal_mods: dict | None, show: dict,
                    is_rerun: bool) -> tuple:
    """
    Stage 6b (Seasonal): apply active seasonal modifier effects.

    Lives between monopoly (6) and age decay (7) — after all genre/global
    bonuses have been accumulated, before the age and slot multipliers
    collapse the total into a final integer.

    Applies only to live (non-rerun) shows so vault shows remain frozen.
    genre_view_mult entries only fire when the show's genre matches.
    """
    if not seasonal_mods or is_rerun:
        return mult, income, upkeep
    mult   *= seasonal_mods.get("view_mult", 1.0)
    income += seasonal_mods.get("income_flat", 0.0)
    upkeep *= seasonal_mods.get("upkeep_mult", 1.0)
    # Per-genre view multiplier stacks multiplicatively on top of global view_mult
    genre = show.get("genre", "")
    if genre:
        genre_vm = seasonal_mods.get("genre_view_mult", {}).get(genre, 1.0)
        mult *= genre_vm
    return mult, income, upkeep


def _stage_age_decay(show: dict) -> float:
    """Stage 7: lifecycle age multiplier from the AGE_MULTIPLIERS table."""
    return _get_age_mult(show.get("age", 1))


def _stage_slot_penalty(show: dict, slot_indices: list, is_rerun: bool) -> float:
    """Stage 8: ×0.70 when the show is outside all its rec_slots. Reruns are exempt."""
    rec_slots   = show.get("rec_slots") or []
    in_rec_slot = any(s in rec_slots for s in slot_indices)
    return 1.0 if (is_rerun or in_rec_slot) else SLOT_PENALTY_MULT


def _stage_floor(v: float, mult: float, age_mult: float, time_mult: float) -> float:
    """Stage 9: collapse accumulated view factors into a final 2-decimal value."""
    return rnd2((v * mult) * age_mult * time_mult)


def _vault_return(final_v: float, active_perks: list,
                  show: dict, slot_indices: list) -> dict:
    """
    Vault override: replace live-schedule views and income with rerun share.

    Base rerun view multiplier is 0.25; vault-scoped upgrade effects add to it.
    Income is exclusively from vault-scoped upgrade effects (upg_synd, upg_dvr).
    """
    rerun_view_mult, rerun_income = resolve_vault_rerun(active_perks, show, slot_indices)
    return {
        "v":            rnd2(final_v * rerun_view_mult),
        "i":            rnd2(rerun_income),
        "ad_income":    0.0,
        "star_income":  0.0,
        "upkeep":       0.0,
        "slot_indices": slot_indices,
    }


# ─── YIELD CALCULATOR ─────────────────────────────────────────────────────────────

def calculate_yield(show: dict, *,
                    is_rerun: bool    = False,
                    start_idx: int    = 0,
                    active_perks: list = None,
                    season: int       = 1,
                    monopoly_bonus: dict = None,
                    seasonal_mods: dict  = None) -> dict:
    """Compute the season output (views + income) for a single show instance.

    Returns a full breakdown of every contributing factor so callers can
    display or test each component independently.
    """
    if active_perks is None:
        active_perks = []

    _ZERO = {
        "v": 0, "i": 0, "ad_income": 0, "star_income": 0, "upkeep": 0,
        "slot_indices": [], "base_views": 0, "timeslot_bonus": 1.0,
        "star_v_flat": 0, "star_v_mult": 1.0, "star_upkeep": 0,
        "ad_v_flat": 0, "ad_v_mult": 1.0,
        "upgrade_v_flat": 0, "upgrade_v_mult": 1.0, "upgrade_income": 0,
        "wildcard_v_flat": 0, "wildcard_v_mult": 1.0, "wildcard_income": 0,
        "monopoly_v_mult": 1.0, "monopoly_income": 0,
        "seasonal_v_mult": 1.0, "seasonal_income": 0, "seasonal_upkeep_mult": 1.0,
        "age_mult": 1.0, "slot_penalty": 1.0, "show_upkeep": 0,
    }
    if not show or show.get("is_extension"):
        return _ZERO

    slot_indices = (
        [start_idx, start_idx + 1] if show.get("size", 1) == 2 else [start_idx]
    )

    _mb = monopoly_bonus if not is_rerun else None  # monopoly only applies to live shows

    # Stage 1: upkeep (show's own cost; star upkeep added in stage 3)
    show_upkeep_raw = _stage_upkeep(show, slot_indices, is_rerun, _mb)
    upkeep = show_upkeep_raw

    # Stage 2: base views + Afternoon timeslot bonus
    v         = _stage_base_views(show, slot_indices, is_rerun)
    base_v    = v
    ts_bonus  = 1.1 if (not is_rerun and 1 in slot_indices) else 1.0
    mult      = 1.0
    income    = 0.0

    # Stage 3: stars
    s_v, s_mult, star_income, s_upkeep = _stage_stars(show, slot_indices, is_rerun, _mb)
    v += s_v; mult *= s_mult; income += star_income; upkeep += s_upkeep

    # Stage 4: ads
    a_v, a_mult, ad_income = _stage_ads(show, slot_indices, is_rerun, _mb)
    v += a_v; mult *= a_mult; income += ad_income

    # Stage 5: upgrades
    u_v, u_mult, u_income = _stage_upgrades(
        active_perks, show, slot_indices, is_rerun, season)
    v += u_v; mult *= u_mult; income += u_income

    # Stage 5b: wildcard show ability (live shows only)
    wa_v = 0.0; wa_mul = 1.0; wa_inc = 0.0; wa_upk = 0.0
    if not is_rerun:
        wa     = show.get("wildcard_ability_effect") or {}
        wa_v   = float(wa.get("v_flat",  0))
        wa_mul = float(wa.get("v_mult",  1.0))
        wa_inc = float(wa.get("income",  0))
        wa_upk = float(wa.get("upkeep",  0))
        v += wa_v; mult *= wa_mul; income += wa_inc; upkeep += wa_upk

    # Stage 6: monopoly — derive breakdown values directly from the bonus dict
    # to avoid floating-point division artefacts in the breakdown report.
    if _mb:
        mono_type       = _mb.get("type", "views_income")
        mono_v_mult     = _mb.get("views_mult", 1.0)
        mono_income_raw = 0 if mono_type == "budget_boost" else _mb.get("income_bonus", 0)
    else:
        mono_v_mult     = 1.0
        mono_income_raw = 0
    mult, income = _stage_monopoly(mult, income, monopoly_bonus, is_rerun)

    # Stage 6b: seasonal — derive breakdown values from the mods dict directly.
    if seasonal_mods and not is_rerun:
        seas_v_mult   = seasonal_mods.get("view_mult", 1.0)
        genre_vm      = seasonal_mods.get("genre_view_mult", {}).get(show.get("genre", ""), 1.0)
        seas_v_mult  *= genre_vm
        seas_income   = seasonal_mods.get("income_flat", 0.0)
        seas_upk_mult = seasonal_mods.get("upkeep_mult", 1.0)
    else:
        seas_v_mult = 1.0; seas_income = 0.0; seas_upk_mult = 1.0
    mult, income, upkeep = _stage_seasonal(
        mult, income, upkeep, seasonal_mods, show, is_rerun)

    age_mult  = _stage_age_decay(show)                              # 7. age decay
    time_mult = _stage_slot_penalty(show, slot_indices, is_rerun)   # 8. slot penalty
    final_v   = _stage_floor(v, mult, age_mult, time_mult)          # 9. floor

    if is_rerun:
        return _vault_return(final_v, active_perks, show, slot_indices)

    safe_upkeep = max(0.0, upkeep)
    return {
        # Core summary (backward-compatible keys)
        "v":            final_v,
        "i":            rnd2(income - safe_upkeep),
        "ad_income":    rnd2(ad_income),
        "star_income":  rnd2(star_income),
        "upkeep":       rnd2(safe_upkeep),
        "slot_indices": slot_indices,
        # Detailed breakdown — one field per pipeline stage
        "base_views":          base_v,
        "timeslot_bonus":      ts_bonus,
        "star_v_flat":         rnd2(s_v),
        "star_v_mult":         round(s_mult, 4),
        "star_upkeep":         rnd2(s_upkeep),
        "ad_v_flat":           rnd2(a_v),
        "ad_v_mult":           round(a_mult, 4),
        "upgrade_v_flat":      rnd2(u_v),
        "upgrade_v_mult":      round(u_mult, 4),
        "upgrade_income":      rnd2(u_income),
        "wildcard_v_flat":     rnd2(wa_v),
        "wildcard_v_mult":     round(wa_mul, 4),
        "wildcard_income":     rnd2(wa_inc),
        "monopoly_v_mult":     round(mono_v_mult, 4),
        "monopoly_income":     rnd2(mono_income_raw),
        "seasonal_v_mult":     round(seas_v_mult, 4),
        "seasonal_income":     rnd2(seas_income),
        "seasonal_upkeep_mult": round(seas_upk_mult, 4),
        "age_mult":            age_mult,
        "slot_penalty":        time_mult,
        "show_upkeep":         rnd2(show_upkeep_raw),
    }


# ─── GAME STATE ───────────────────────────────────────────────────────────────

class GameState:
    """Single mutable container for all in-memory game state."""

    def __init__(self):
        self.run              = 1
        self.network_prestige = 0
        self.season           = 1
        self.budget           = INITIAL_BUDGET
        self.total_views      = 0
        self.lineup           = [None] * 4
        self.reruns           = [None] * MAX_RERUN_SLOTS
        self.active_perks     = []
        self.current_tab      = "shows"
        self.selected_item    = None
        self.next_target      = TARGET_INTERVAL
        self.current_target   = BASE_VIEW_TARGET
        self.shop = {"shows": [], "stars": [], "ads": [], "upgrades": [], "events": []}
        self.pool = {"shows": [], "stars": [], "ads": [], "upgrades": [], "events": []}
        self.difficulty           = DEFAULT_DIFFICULTY
        self.last_season_summary  = None
        self.last_monopoly_genre  = None

        # ── Seasonal events (Prompt 11) ────────────────────────────────────────
        # active_seasonal_modifiers: list of {event, remaining_seasons}
        self.active_seasonal_modifiers: list = []
        # active_contracts: list of {event, remaining_seasons, fulfilled}
        self.active_contracts: list = []
        # active_mandates: list of {event, remaining_seasons}
        self.active_mandates: list = []
        # available_contracts: offer board shown to player each season
        self.available_contracts: list = []
        # id of the last seasonal event rolled (avoids immediate repeats)
        self.last_seasonal_event_id: str | None = None
        # full log of seasonal events that have fired this run
        self.seasonal_event_log: list = []
        # isolated RNG for seasonal events — does not consume from global random
        self._seasonal_rng = random.Random()
        # guard flag: tests that check golden values can set this to False
        self.seasonal_events_enabled: bool = True
        # bailout tracking (Prompt 11.3)
        self.bailouts_used: int = 0
        # cached collapsed modifier dict — reset whenever active_seasonal_modifiers changes
        self._seasonal_mods_cache: dict | None = None
        self.reroll_cost: int = REROLL_BASE_COST

        # ── Pending events (purchased from shop, fire at start of next season) ──
        # Each entry: {event: dict, cost_paid: float}
        self.pending_events: list = []

        # ── Projection cache (preview_lineup_yield) ────────────────────────────
        self._proj_cache_key: tuple | None = None
        self._proj_cache_pv:  int   = 0
        self._proj_cache_pi:  float = 0.0

        # ── Terminal ledger — season-stamped financial history ─────────────────
        self.ledger_log: list[str] = []

    # ─── RUN MANAGEMENT ───────────────────────────────────────────────────────

    def start_new_run(self, increment_run: bool = False, difficulty: str = None) -> None:
        """Reset all transient state and begin a new run."""
        if increment_run:
            self.run             += 1
            self.network_prestige += 1

        if difficulty is not None:
            self.difficulty = difficulty

        self.season          = 1
        self.budget          = DifficultyManager.effective_starting_budget(self)
        self.total_views     = 0
        self.lineup          = [None] * 4
        self.reruns          = [None] * MAX_RERUN_SLOTS
        self.active_perks    = []
        self.selected_item   = None
        self.current_tab     = "shows"
        self.next_target     = TARGET_INTERVAL
        self.current_target  = DifficultyManager.effective_opening_target(self)
        self.last_season_summary = None
        self.last_monopoly_genre = None

        # Seasonal resets
        self.active_seasonal_modifiers = []
        self.active_contracts          = []
        self.active_mandates           = []
        self.available_contracts       = []
        self.last_seasonal_event_id    = None
        self.seasonal_event_log        = []
        self.pending_events            = []
        # Derive the seasonal RNG seed from the global RNG so that games with
        # the same random.seed() are fully reproducible end-to-end.
        self._seasonal_rng = random.Random(random.getrandbits(32))
        self.bailouts_used             = 0
        self._seasonal_mods_cache      = None
        self.reroll_cost               = REROLL_BASE_COST
        self._proj_cache_key           = None
        self._proj_cache_pv            = 0
        self._proj_cache_pi            = 0.0

        self.ledger_log                = []
        self._init_pools()
        self.generate_shop()
        # Delete any existing autosave so the menu doesn't offer a stale RESUME
        _platform.delete_save(0)

    def _init_pools(self):
        """Rebuild all card draw pools from the JSON databases."""
        self.pool["shows"]    = show_pool.build_pool()
        self.pool["stars"]    = star_pool.build_pool()
        self.pool["ads"]      = ad_pool.build_pool()
        self.pool["upgrades"] = upg_pool.build_pool()
        self.pool["events"]   = event_pool.build_pool()

    # ─── LEDGER ───────────────────────────────────────────────────────────────

    def _ledger_append(self, season: int, category: str, text: str) -> None:
        """Append a season-stamped entry to the terminal ledger log."""
        self.ledger_log.append(f"S{season:02d}  {category:<10}  {text}")

    # ─── SERIALIZE / DESERIALIZE ──────────────────────────────────────────────

    def _serialize(self) -> dict:
        """Return a fully JSON-serialisable snapshot of all game state."""
        rng_v, rng_s, rng_g = self._seasonal_rng.getstate()
        return {
            "version":                 2,
            "run":                     self.run,
            "network_prestige":        self.network_prestige,
            "season":                  self.season,
            "budget":                  self.budget,
            "total_views":             self.total_views,
            "lineup":                  self.lineup,
            "reruns":                  self.reruns,
            "active_perks":            self.active_perks,
            "current_tab":             self.current_tab,
            "selected_item":           self.selected_item,
            "next_target":             self.next_target,
            "current_target":          self.current_target,
            "difficulty":              self.difficulty,
            "last_season_summary":     self.last_season_summary,
            "last_monopoly_genre":     self.last_monopoly_genre,
            "active_seasonal_modifiers": self.active_seasonal_modifiers,
            "active_contracts":        self.active_contracts,
            "active_mandates":         self.active_mandates,
            "available_contracts":     self.available_contracts,
            "last_seasonal_event_id":  self.last_seasonal_event_id,
            "seasonal_event_log":      self.seasonal_event_log,
            "seasonal_events_enabled": self.seasonal_events_enabled,
            "bailouts_used":           self.bailouts_used,
            "pending_events":          self.pending_events,
            "reroll_cost":             self.reroll_cost,
            "ledger_log":              self.ledger_log,
            "shop":                    self.shop,
            "pool":                    self.pool,
            # Preserve RNG state so seasonal events are reproducible after a reload
            "seasonal_rng": {"version": rng_v, "state": list(rng_s), "gauss": rng_g},
        }

    def _deserialize(self, data: dict) -> None:
        """Restore all game state from a serialised snapshot (full fidelity)."""
        self.run                       = data.get("run", 1)
        self.network_prestige          = data.get("network_prestige", 0)
        self.season                    = data.get("season", 1)
        self.budget                    = data.get("budget", INITIAL_BUDGET)
        self.total_views               = data.get("total_views", 0)
        self.lineup                    = data.get("lineup", [None] * 4)
        self.reruns                    = data.get("reruns", [None] * MAX_RERUN_SLOTS)
        self.active_perks              = data.get("active_perks", [])
        self.current_tab               = data.get("current_tab", "shows")
        self.selected_item             = data.get("selected_item")
        self.next_target               = data.get("next_target", TARGET_INTERVAL)
        self.current_target            = data.get("current_target", BASE_VIEW_TARGET)
        self.difficulty                = data.get("difficulty", DEFAULT_DIFFICULTY)
        self.last_season_summary       = data.get("last_season_summary")
        self.last_monopoly_genre       = data.get("last_monopoly_genre")
        self.active_seasonal_modifiers = data.get("active_seasonal_modifiers", [])
        self.active_contracts          = data.get("active_contracts", [])
        self.active_mandates           = data.get("active_mandates", [])
        self.available_contracts       = data.get("available_contracts", [])
        self.last_seasonal_event_id    = data.get("last_seasonal_event_id")
        self.seasonal_event_log        = data.get("seasonal_event_log", [])
        self.seasonal_events_enabled   = data.get("seasonal_events_enabled", True)
        self.bailouts_used             = data.get("bailouts_used", 0)
        self.pending_events            = data.get("pending_events", [])
        self.reroll_cost               = data.get("reroll_cost", REROLL_BASE_COST)
        self.ledger_log                = data.get("ledger_log", [])
        self.shop                      = data.get("shop", {"shows": [], "stars": [], "ads": [], "upgrades": [], "events": []})
        self.pool                      = data.get("pool", {"shows": [], "stars": [], "ads": [], "upgrades": [], "events": []})

        # Restore the isolated seasonal RNG state for reproducibility
        rng_data = data.get("seasonal_rng")
        if rng_data and isinstance(rng_data, dict):
            try:
                self._seasonal_rng.setstate(
                    (rng_data["version"], tuple(rng_data["state"]), rng_data["gauss"])
                )
            except (KeyError, TypeError, ValueError):
                self._seasonal_rng = random.Random()
        else:
            self._seasonal_rng = random.Random()

        # Clear transient computation caches
        self._seasonal_mods_cache = None
        self._proj_cache_key      = None
        self._proj_cache_pv       = 0
        self._proj_cache_pi       = 0.0

    # ─── SHOP ─────────────────────────────────────────────────────────────────

    def generate_shop(self) -> None:
        """Refresh the shop by popping items from the pools."""
        diff = DIFFICULTY_LEVELS.get(self.difficulty, DIFFICULTY_LEVELS["NORMAL"])
        event_mod = diff["event_freq_mod"]

        self.shop["shows"]    = show_pool.pop_for_shop(self.pool["shows"],    SHOP_SHOW_COUNT)
        self.shop["stars"]    = star_pool.pop_for_shop(self.pool["stars"],    SHOP_STAR_COUNT)
        self.shop["ads"]      = ad_pool.pop_for_shop(  self.pool["ads"],      SHOP_AD_COUNT)
        self.shop["upgrades"] = upg_pool.pop_for_shop( self.pool["upgrades"], SHOP_UPG_COUNT)
        # Event count is difficulty-adjusted: EASY gets more events, BRUTAL fewer.
        adj_event_count = max(0, round(SHOP_EVENT_COUNT * (1 + event_mod)))
        self.shop["events"]   = event_pool.pop_for_shop(self.pool["events"],  adj_event_count)

        # Refresh contracts offers board if none are available (first shop of season)
        if self.seasonal_events_enabled and not self.available_contracts and self.season >= 2:
            active_ids = {e.get("event", {}).get("id") for e in self.active_contracts}
            self.available_contracts = seasonal_mod.build_offers(
                self.season, active_ids, self._seasonal_rng
            )

    def reroll_shop(self) -> dict:
        """Pay REROLL_COST to refresh the shop; return {ok, message, level}."""
        if self.budget < self.reroll_cost:
            return {"ok": False, "message": "NOT ENOUGH FUNDS TO REROLL", "level": "error"}
        cost = self.reroll_cost
        self.budget -= cost
        self.reroll_cost += 1
        self.generate_shop()
        return {"ok": True, "message": f"SHOP REROLLED (-${cost})", "level": "info"}

    def set_tab(self, tab_id: str) -> None:
        """Switch the active shop tab."""
        if tab_id in self.shop or tab_id == "contracts":
            self.current_tab = tab_id

    # ─── SEASONAL HELPERS ─────────────────────────────────────────────────────

    def aggregate_seasonal_mods(self) -> dict | None:
        """Collapse active modifier events into one effect dict; return None when none active."""
        if not self.seasonal_events_enabled:
            return None
        if not self.active_seasonal_modifiers:
            return None
        if self._seasonal_mods_cache is None:
            self._seasonal_mods_cache = seasonal_mod.aggregate_seasonal_mods(
                self.active_seasonal_modifiers
            )
        return self._seasonal_mods_cache

    def accept_contract(self, event_id: str) -> dict:
        """Accept a contract from the offers board; return {ok, message, level}."""
        offer = next(
            (e for e in self.available_contracts if e.get("id") == event_id), None
        )
        if offer is None:
            return {"ok": False, "message": "CONTRACT NOT ON OFFER BOARD", "level": "error"}

        already = any(e.get("event", {}).get("id") == event_id for e in self.active_contracts)
        if already:
            return {"ok": False, "message": "CONTRACT ALREADY ACTIVE", "level": "warn"}

        self.active_contracts.append({
            "event":            offer,
            "remaining_seasons": offer.get("duration", 3),
            "fulfilled":        False,
        })
        self.available_contracts = [
            e for e in self.available_contracts if e.get("id") != event_id
        ]
        return {
            "ok": True,
            "message": f"CONTRACT ACCEPTED: {offer.get('name', '?')}",
            "level": "success",
        }

    def accept_bailout(self, choice: str) -> dict:
        """Accept a bailout (loan or grant) when budget is negative; return {ok, message, level}."""
        if self.bailouts_used >= 2:
            return {"ok": False, "message": "NO BAILOUTS REMAINING", "level": "error"}
        if self.budget >= 0:
            return {"ok": False, "message": "BUDGET IS NOT NEGATIVE", "level": "warn"}

        from .cards import load_bailouts
        tiers     = load_bailouts()
        tier_idx  = self.bailouts_used          # 0 for first bailout, 1 for second
        tier      = tiers[tier_idx]
        cash      = tier["grant_amount"]

        self.budget    += cash
        self.bailouts_used += 1
        self._ledger_append(self.season, "BAILOUT", f"+${cash}  ({choice})")

        if choice == "loan":
            loan_cfg = tier["loan"]
            contract_event = {
                "id":          f"_bailout_loan_{self.bailouts_used}",
                "name":        loan_cfg["name"],
                "desc":        loan_cfg["desc"],
                "kind":        "contract",
                "duration":    loan_cfg["window_seasons"],
                "requirement": loan_cfg["requirement"],
                "reward":      {},
                "penalty":     loan_cfg["penalty"],
            }
            self.active_contracts.append({
                "event":             contract_event,
                "remaining_seasons": loan_cfg["window_seasons"],
                "fulfilled":         False,
            })
            return {
                "ok":      True,
                "message": (
                    f"BAILOUT LOAN: +${cash} BUDGET  |  "
                    f"CONTRACT: {loan_cfg['name']}"
                ),
                "level": "info",
            }

        else:   # grant
            grant_cfg  = tier["grant"]
            views_loss = int(grant_cfg["views_loss"])
            self.total_views = max(0, self.total_views - views_loss)
            return {
                "ok":      True,
                "message": (
                    f"BAILOUT GRANT: +${cash} BUDGET  |  "
                    f"-{views_loss} VIEWS (arts grant conditions)"
                ),
                "level": "warn",
            }

    # ─── PURCHASE ─────────────────────────────────────────────────────────────

    def attempt_purchase(self, item: dict, category: str) -> dict:
        """Attempt to buy a shop item; return {ok, message, level, action}."""
        if not item:
            return {"ok": False, "message": "INVALID ITEM", "level": "error"}
        if self.budget < item.get("cost", 0):
            return {"ok": False, "message": "NOT ENOUGH FUNDS", "level": "error"}

        # ── Upgrades (immediate, global effect) ───────────────────────────────
        if category == "upgrades":
            if len(self.active_perks) >= MAX_ACTIVE_UPGRADES:
                return {"ok": False, "message": "UPGRADE BAY FULL (MAX 5)", "level": "error"}
            if upg_pool.is_already_owned(item, self.active_perks):
                return {"ok": False, "message": "UPGRADE ALREADY OWNED", "level": "warn"}
            self.budget -= item["cost"]
            self.active_perks.append(dict(item))
            self.shop["upgrades"] = [u for u in self.shop["upgrades"] if u.get("uid") != item.get("uid")]
            self._ledger_append(self.season, "BUY", f"{item['name']}  -${item['cost']}")
            return {"ok": True, "message": f"ACQUIRED: {item['name']}", "level": "success", "action": "placed"}

        # ── Events (queued — fire at the START of the next season) ───────────────
        if category == "events":
            self.budget -= item["cost"]
            self.shop["events"] = [e for e in self.shop["events"] if e.get("uid") != item.get("uid")]
            self.pending_events.append({"event": dict(item)})
            self._ledger_append(self.season, "BUY", f"{item.get('name', '?')}  -${item['cost']}  (queued event)")
            return {
                "ok": True,
                "message": f"QUEUED FOR NEXT SEASON: {item.get('name', '?')}",
                "level": "info",
                "action": "placed",
            }

        # ── Shows, stars, ads: queue for placement ────────────────────────────
        self.selected_item = {**item, "shop_type": category}

        if item.get("is_wildcard"):
            return {"ok": True, "action": "wildcard", "message": "CONFIGURE WILDCARD", "level": "info"}

        return {"ok": True, "action": "select", "message": f"SELECT SLOT FOR: {item.get('name','???')}", "level": "info"}

    def clear_selection(self) -> None:
        """Cancel the current pending item selection."""
        self.selected_item = None

    # ─── WILDCARD RESOLUTION ──────────────────────────────────────────────────

    def roll_wildcard_types(self) -> list:
        """Sample 3 distinct genre IDs for the wildcard type-selection step; return list."""
        from .cards import load_wildcards
        wc        = load_wildcards()
        genre_ids = [g["id"] for g in wc["wildcard_show"]["genre_options"]]
        return random.sample(genre_ids, 3)

    def roll_wildcard_abilities(self, show_type: str, card_type: str = "show") -> list:
        """Sample 3 distinct ability dicts for the chosen wildcard type; return list."""
        from .cards import load_wildcards
        wc      = load_wildcards()
        section = "wildcard_ad" if card_type == "ad" else "wildcard_show"
        pool    = wc[section]["ability_templates"].get(show_type, [])
        return random.sample(pool, min(3, len(pool)))

    def resolve_wildcard_show(self, name: str, show_type: str, ability: dict) -> dict:
        """Stamp name, type, and ability onto the pending wildcard show; return {ok, message, level}."""
        item = self.selected_item
        if not item or not item.get("is_wildcard") or item.get("shop_type") != "shows":
            return {"ok": False, "message": "NO WILDCARD SHOW PENDING", "level": "error"}

        from .cards import load_wildcards
        wc_cfg     = load_wildcards()
        genre_opts = {g["id"]: g for g in wc_cfg["wildcard_show"]["genre_options"]}
        gmod       = genre_opts.get(show_type, {})

        resolved                            = dict(item)
        resolved["name"]                    = name.strip() or "???"
        resolved["genre"]                   = show_type
        resolved["rec_slots"]               = gmod.get("rec_slots", [])
        resolved["is_wildcard"]             = False
        resolved["cost"]                    = item.get("cost", 30) + gmod.get("cost_mod", 0)
        resolved["base_views"]              = item.get("base_views", 150) + gmod.get("views_mod", 0)
        resolved["wildcard_ability_effect"] = dict(ability.get("effect", {}))
        self.selected_item                  = resolved
        return {"ok": True, "message": f"WILDCARD CONFIGURED: {resolved['name']}", "level": "success"}

    def resolve_wildcard_ad(self, name: str, show_type: str, ability: dict) -> dict:
        """Stamp name, target genre, and ability onto the pending wildcard ad; return {ok, message, level}."""
        item = self.selected_item
        if not item or not item.get("is_wildcard") or item.get("shop_type") != "ads":
            return {"ok": False, "message": "NO WILDCARD AD PENDING", "level": "error"}

        abi_effect      = ability.get("effect", {})
        match_income    = abi_effect.get("income", 20)
        fallback_income = max(0, match_income // 2)

        resolved                   = dict(item)
        resolved["name"]           = name.strip() or "???"
        resolved["genre_target"]   = show_type
        resolved["condition"]      = {"type": "genre", "genres": [show_type]}
        resolved["condition_text"] = (
            f"If on {show_type}: +${match_income} Income. "
            f"Otherwise: +${fallback_income}"
        )
        resolved["effect"]         = dict(abi_effect)
        resolved["fallback"]       = {"income": fallback_income}
        resolved["is_wildcard"]    = False
        resolved["shop_type"]      = "ads"
        self.selected_item         = resolved
        return {"ok": True, "message": f"AD CONFIGURED: {resolved['name']}", "level": "success"}

    # ─── PLACEMENT ────────────────────────────────────────────────────────────

    def place_selected(self, arr_type: str, idx: int) -> dict:
        """Place the currently selected item into a lineup or vault slot; return {ok, message, level}."""
        item = self.selected_item
        if not item:
            return {"ok": False, "message": "NO ITEM SELECTED", "level": "error"}
        if item.get("is_wildcard"):
            return {"ok": False, "message": "CONFIGURE WILDCARD FIRST", "level": "error"}
        if self.budget < item.get("cost", 0):
            return {"ok": False, "message": "NOT ENOUGH FUNDS", "level": "error"}

        target = self.lineup if arr_type == "lineup" else self.reruns

        # ── Place a Show ──────────────────────────────────────────────────────
        if item.get("shop_type") == "shows":
            # Vault placement validation
            if arr_type == "reruns":
                ok, msg = show_pool.can_place_in_vault(item)
                if not ok:
                    return {"ok": False, "message": msg, "level": "error"}

            # Lineup placement validation
            if arr_type == "lineup":
                ok, msg = show_pool.can_place_in_lineup(item, idx, self.lineup)
                if not ok:
                    return {"ok": False, "message": msg, "level": "error"}

            # Check vault has room
            if arr_type == "reruns" and target[idx] is not None:
                return {"ok": False, "message": "VAULT SLOT OCCUPIED", "level": "error"}

            self.budget -= item["cost"]
            instance = make_show_instance(item)

            if item.get("size", 1) == 2 and arr_type == "lineup":
                self._clear_slot("lineup", idx)
                self._clear_slot("lineup", idx + 1)
                self.lineup[idx]     = instance
                self.lineup[idx + 1] = {"is_extension": True, "head": idx}
            else:
                self._clear_slot(arr_type, idx)
                target[idx] = instance

            self.shop["shows"] = [s for s in self.shop["shows"] if s.get("uid") != item.get("uid")]
            self.selected_item = None
            self._ledger_append(self.season, "BUY", f"{item.get('name', '???')}  -${item['cost']}")
            return {"ok": True, "message": f"DEPLOYED: {item.get('name','???')}", "level": "success"}

        # ── Attach a Star or Ad to an existing show ───────────────────────────
        slot_type  = "star" if item.get("shop_type") == "stars" else "ad"
        target_show = target[idx] if 0 <= idx < len(target) else None

        if not target_show or target_show.get("is_extension"):
            return {"ok": False, "message": "NO SHOW IN THAT SLOT", "level": "error"}

        if slot_type == "star":
            ok, msg = star_pool.can_attach_to_show(target_show)
        else:
            ok, msg = ad_pool.can_attach_to_show(target_show)

        if not ok:
            return {"ok": False, "message": msg, "level": "error"}

        # Dual-income: credit upfront cash before deducting full cost.
        upfront = 0
        if slot_type == "ad":
            upfront = ad_pool.upfront_payment(item, self)
            self.budget += upfront

        self.budget -= item["cost"]
        target_show["attached"][slot_type].append(dict(item))
        cat = "stars" if slot_type == "star" else "ads"
        self.shop[cat] = [x for x in self.shop[cat] if x.get("uid") != item.get("uid")]
        self.selected_item = None
        net_cost = item["cost"] - upfront
        self._ledger_append(
            self.season, "BUY",
            f"{item.get('name', '???')} → {target_show.get('name', '???')}  -${net_cost:.0f}",
        )
        return {
            "ok": True,
            "message": f"{slot_type.upper()} ATTACHED TO {target_show.get('name','???')}",
            "level": "success",
        }

    # ─── SLOT MANAGEMENT ──────────────────────────────────────────────────────

    def _clear_slot(self, arr_type: str, idx: int):
        """
        Internal helper: clear a single slot (handles 2-slot show extension markers).

        Parameters
        ----------
        arr_type : str  'lineup' or 'reruns'.
        idx      : int  Slot index to clear.
        """
        arr  = self.lineup if arr_type == "lineup" else self.reruns
        slot = arr[idx] if 0 <= idx < len(arr) else None
        if slot is None:
            return
        if slot.get("is_extension"):
            head = slot["head"]
            arr[head] = None
            arr[idx]  = None
        elif slot.get("size", 1) == 2 and arr_type == "lineup":
            arr[idx]     = None
            if idx + 1 < len(arr):
                arr[idx + 1] = None
        else:
            arr[idx] = None

    def sell_show(self, arr_type: str, idx: int) -> dict:
        """
        Cancel a show from a lineup or vault slot.

        Sell value is based on accumulated views:
          - Age 1 (never aired): $0 — no refund (penalises impulse buys).
          - Age 2+: views_earned × 0.04, capped at the show's original cost.
        Stars attached to the show are lost with no refund.
        """
        arr   = self.lineup if arr_type == "lineup" else self.reruns
        slot  = arr[idx] if 0 <= idx < len(arr) else None
        if not slot:
            return {"ok": False, "message": "NOTHING TO CANCEL", "level": "error"}

        head_idx = slot.get("head", idx) if slot.get("is_extension") else idx
        show     = arr[head_idx]
        if not show or show.get("is_extension"):
            return {"ok": False, "message": "NOTHING TO CANCEL", "level": "error"}

        age             = show.get("age", 1)
        accumulated     = show.get("accumulated_views", 0)
        show_cost       = show.get("cost", 0)

        if age <= 1:
            # Show has never aired — no refund
            refund = 0.0
            msg    = f"CANCELLED (NEVER AIRED) — NO REFUND | {show.get('name', '???')}"
            level  = "warn"
        else:
            # Refund based on views earned; capped at original cost
            refund = rnd2(min(accumulated * 0.04, float(show_cost)))
            msg    = f"SOLD — +${refund:.2f} from {int(accumulated)} views | {show.get('name', '???')}"
            level  = "info"

        self.budget += refund
        self._clear_slot(arr_type, head_idx)
        return {"ok": True, "message": msg, "level": level}

    def move_to_vault(self, lineup_idx: int) -> dict:
        """Move a live lineup show to the Syndication Vault; return {ok, message, level}."""
        show = self.lineup[lineup_idx] if 0 <= lineup_idx < len(self.lineup) else None
        if not show or show.get("is_extension"):
            return {"ok": False, "message": "NO SHOW TO SYNDICATE", "level": "error"}

        ok, msg = show_pool.can_place_in_vault(show)
        if not ok:
            return {"ok": False, "message": msg, "level": "error"}

        empty = next((i for i, s in enumerate(self.reruns) if s is None), None)
        if empty is None:
            return {"ok": False, "message": "VAULT IS FULL (2 MAX)", "level": "error"}

        self.reruns[empty] = show
        self.lineup[lineup_idx] = None
        return {"ok": True, "message": f"SYNDICATED: {show.get('name','???')}", "level": "success"}

    # ─── SEASON ADVANCE ───────────────────────────────────────────────────────

    def advance_season(self) -> dict:
        """Advance one season: calculate yields, update totals, check milestones; return summary dict."""
        self.reroll_cost = REROLL_BASE_COST
        season_views  = 0
        season_income = float(BASE_INCOME)
        seasonal_event_messages: list = []
        # Season-level budget delta trackers for the totals breakdown
        cooking_boost_amount  = 0
        season_contract_income = 0
        season_mandate_penalty = 0

        # ── Fire queued shop events (purchased last season) ───────────────────
        if self.pending_events:
            fired_messages = []
            for entry in self.pending_events:
                ev = entry["event"]
                result = event_pool.apply_event(ev, self, generate_shop_fn=self.generate_shop)
                fired_messages.append({
                    "text":  f"[EVENT TRIGGERED] {result.get('message', ev.get('name', '?'))}",
                    "level": result.get("level", "info"),
                })
            seasonal_event_messages.extend(fired_messages)
            self.pending_events = []

        # ── (a) Aggregate seasonal modifiers for this season's yield calc ─────
        s_mods = self.aggregate_seasonal_mods() if self.seasonal_events_enabled else None

        # ── Genre monopoly detection ──────────────────────────────────────────
        live_shows     = show_pool.all_live_shows(self.lineup)
        all_filled     = all(s is not None for s in self.lineup)
        monopoly_bonus = None
        monopoly_genre = None

        if all_filled and len(live_shows) >= 1:
            genres = list({s.get("genre") for s in live_shows if s.get("genre")})
            if len(genres) == 1:
                registry = show_pool.get_genre_registry()
                entry    = registry.get(genres[0], {})
                mono     = entry.get("monopoly")
                if mono:
                    monopoly_bonus = mono
                    monopoly_genre = genres[0]

        self.last_monopoly_genre = monopoly_genre

        # ── NEWS monopoly: apply target reduction NOW (before milestone check) ─
        effective_target = self.current_target
        if monopoly_genre == "NEWS":
            effective_target = DifficultyManager.apply_news_monopoly(self.current_target)

        # ── COOKING monopoly: budget_boost applied directly to budget ─────────
        if monopoly_bonus and monopoly_bonus.get("type") == "budget_boost":
            boost = monopoly_bonus.get("budget_per_season", 0)
            if boost:
                cooking_boost_amount = boost
                self.budget = rnd2(self.budget + boost)
                seasonal_event_messages.append({
                    "text":  f"CULINARY EMPIRE: +${boost} DIRECT BUDGET",
                    "level": "success",
                })

        # ── (b) Evaluate mandates BEFORE yields ───────────────────────────────
        if self.seasonal_events_enabled:
            for entry in self.active_mandates:
                ev  = entry["event"]
                req = ev.get("requirement", {})
                if not eval_requirement(req, self):
                    pen     = ev.get("penalty", {})
                    season_mandate_penalty += int(pen.get("budget_loss", 0))
                    pen_str = seasonal_mod.apply_penalty(pen, self)
                    seasonal_event_messages.append({
                        "text":  f"MANDATE UNMET - {ev.get('name','?')}: {pen_str}",
                        "level": "error",
                    })
                else:
                    seasonal_event_messages.append({
                        "text":  f"MANDATE MET - {ev.get('name','?')}",
                        "level": "success",
                    })

        # ── Show breakdowns for the Season Summary ────────────────────────────
        show_breakdowns  = []
        vault_breakdowns = []

        # ── (c) Live lineup yields ────────────────────────────────────────────
        for idx, show in enumerate(self.lineup):
            if not show or show.get("is_extension"):
                continue
            y = calculate_yield(
                show,
                is_rerun       = False,
                start_idx      = idx,
                active_perks   = self.active_perks,
                season         = self.season,
                monopoly_bonus = monopoly_bonus,
                seasonal_mods  = s_mods,
            )
            season_views  += y["v"]
            season_income += y["i"]
            show["accumulated_views"] = show.get("accumulated_views", 0) + y["v"]
            show["age"]   += 1   # age every live season

            slot_label = TIME_SLOTS[idx]["label"] if idx < len(TIME_SLOTS) else f"Slot {idx}"
            show_breakdowns.append({
                # Identity
                "name":        show.get("name", "???"),
                "genre":       show.get("genre", ""),
                "slot":        slot_label,
                "age":         show.get("age", 1) - 1,   # age before this season
                # Core totals (backward-compatible)
                "views":       y["v"],
                "ad_income":   y["ad_income"],
                "star_income": y["star_income"],
                "upkeep":      y["upkeep"],
                "net_income":  y["i"],
                # Detailed view breakdown
                "base_views":        y["base_views"],
                "timeslot_bonus":    y["timeslot_bonus"],
                "star_v_flat":       y["star_v_flat"],
                "star_v_mult":       y["star_v_mult"],
                "ad_v_flat":         y["ad_v_flat"],
                "ad_v_mult":         y["ad_v_mult"],
                "upgrade_v_flat":    y["upgrade_v_flat"],
                "upgrade_v_mult":    y["upgrade_v_mult"],
                "wildcard_v_flat":   y["wildcard_v_flat"],
                "wildcard_v_mult":   y["wildcard_v_mult"],
                "monopoly_v_mult":   y["monopoly_v_mult"],
                "seasonal_v_mult":   y["seasonal_v_mult"],
                "age_mult":          y["age_mult"],
                "slot_penalty":      y["slot_penalty"],
                # Detailed income breakdown
                "upgrade_income":    y["upgrade_income"],
                "wildcard_income":   y["wildcard_income"],
                "monopoly_income":   y["monopoly_income"],
                "seasonal_income":   y["seasonal_income"],
                # Detailed upkeep breakdown
                "show_upkeep":       y["show_upkeep"],
                "star_upkeep":       y["star_upkeep"],
                "seasonal_upkeep_mult": y["seasonal_upkeep_mult"],
            })

        # ── Vault reruns ──────────────────────────────────────────────────────
        for idx, show in enumerate(self.reruns):
            if not show:
                continue
            y = calculate_yield(
                show,
                is_rerun      = True,
                start_idx     = idx,
                active_perks  = self.active_perks,
                season        = self.season,
                monopoly_bonus = None,
                seasonal_mods  = None,   # vault shows are frozen — no seasonal effect
            )
            season_views  += y["v"]
            season_income += y["i"]

            vault_breakdowns.append({
                "name":       show.get("name", "???"),
                "views":      y["v"],
                "net_income": y["i"],
            })

        # ── (d) Update totals ─────────────────────────────────────────────────
        season_views     = int(round(season_views))   # round once after summing per-show floats
        self.total_views = int(round(self.total_views + season_views))
        self.budget      = rnd2(self.budget      + season_income)

        # ── (e) Evaluate contracts AFTER updating totals ──────────────────────
        if self.seasonal_events_enabled:
            for entry in self.active_contracts:
                if entry["fulfilled"]:
                    continue
                ev  = entry["event"]
                req = ev.get("requirement", {})
                if eval_requirement(req, self):
                    entry["fulfilled"] = True
                    rew     = ev.get("reward", {})
                    season_contract_income += int(rew.get("budget_bonus", 0))
                    rew_str = seasonal_mod.apply_reward(rew, self)
                    if rew_str:
                        seasonal_event_messages.append({
                            "text":  f"CONTRACT FULFILLED - {ev.get('name','?')}: {rew_str}",
                            "level": "success",
                        })

        # ── (f) Decrement remaining_seasons; expire finished events ───────────
        if self.seasonal_events_enabled:
            expired_contracts = []
            for entry in self.active_contracts:
                entry["remaining_seasons"] -= 1
                if entry["remaining_seasons"] <= 0 and not entry["fulfilled"]:
                    ev      = entry["event"]
                    pen     = ev.get("penalty", {})
                    pen_str = seasonal_mod.apply_penalty(pen, self)
                    if pen_str:
                        seasonal_event_messages.append({
                            "text":  (
                                f"CONTRACT EXPIRED UNMET - {ev.get('name','?')}: {pen_str}"
                            ),
                            "level": "error",
                        })
                if entry["remaining_seasons"] <= 0:
                    expired_contracts.append(entry)
            self.active_contracts = [
                e for e in self.active_contracts if e not in expired_contracts
            ]

            for e in self.active_mandates:
                e["remaining_seasons"] -= 1
            self.active_mandates = [
                e for e in self.active_mandates if e["remaining_seasons"] > 0
            ]
            for e in self.active_seasonal_modifiers:
                e["remaining_seasons"] -= 1
            self.active_seasonal_modifiers = [
                e for e in self.active_seasonal_modifiers if e["remaining_seasons"] > 0
            ]
            self._seasonal_mods_cache = None  # modifiers list changed — bust cache

        # ── Milestone check ───────────────────────────────────────────────────
        status         = "continue"
        milestone_met  = None
        milestone_bonus = 0

        if self.season == self.next_target:
            if self.total_views >= effective_target:
                milestone_met    = True
                milestone_bonus  = MILESTONE_REWARD
                self.budget      = rnd2(self.budget + milestone_bonus)
                self.next_target += TARGET_INTERVAL
                growth = DifficultyManager.effective_growth_rate(self)
                self.current_target = int(round(self.current_target * growth))
                diff = DIFFICULTY_LEVELS.get(self.difficulty, DIFFICULTY_LEVELS["NORMAL"])
                self.current_target += diff["rival_pressure"]
            else:
                milestone_met = False
                status        = "loss"

        # ── Win condition ─────────────────────────────────────────────────────
        if status == "continue" and self.season >= MAX_SEASONS:
            status = "win"

        # ── Bailout check (Prompt 11.3) ───────────────────────────────────────
        bailout_available = (
            self.seasonal_events_enabled
            and self.budget < 0
            and self.bailouts_used < 2
            and status == "continue"
        )

        # ── (g) Roll next seasonal event ──────────────────────────────────────
        new_seasonal_event: dict | None = None
        if self.seasonal_events_enabled and status == "continue":
            new_ev = seasonal_mod.roll_seasonal_event(
                self.season,
                self.last_seasonal_event_id,
                self._seasonal_rng,
            )
            if new_ev:
                self.last_seasonal_event_id = new_ev["id"]
                self.seasonal_event_log.append(new_ev)
                new_seasonal_event = new_ev
                kind = new_ev.get("kind", "modifier")

                if kind == "modifier":
                    self.active_seasonal_modifiers.append({
                        "event":             new_ev,
                        "remaining_seasons": new_ev.get("duration", 1),
                    })
                    self._seasonal_mods_cache = None  # new modifier added — bust cache
                elif kind == "mandate":
                    self.active_mandates.append({
                        "event":             new_ev,
                        "remaining_seasons": new_ev.get("duration", 1),
                    })
                elif kind == "contract":
                    self.active_contracts.append({
                        "event":             new_ev,
                        "remaining_seasons": new_ev.get("duration", 3),
                        "fulfilled":         False,
                    })
                elif kind == "instant":
                    # Reuse the existing event handler registry
                    result = event_pool.apply_event(new_ev, self, self.generate_shop)
                    seasonal_event_messages.append({
                        "text":  result.get("message", ""),
                        "level": result.get("level", "info"),
                    })

        # ── (h) Refresh offers board ──────────────────────────────────────────
        if self.seasonal_events_enabled and status == "continue":
            active_ids = {
                e.get("event", {}).get("id") for e in self.active_contracts
            }
            self.available_contracts = seasonal_mod.build_offers(
                self.season, active_ids, self._seasonal_rng
            )

        # ── Build season summary ──────────────────────────────────────────────
        self.last_season_summary = {
            "season":            self.season,
            "season_views":      season_views,
            "season_income":     rnd2(season_income),
            "total_views":       self.total_views,
            "target":            effective_target,
            "milestone_season":  milestone_met is not None,
            "milestone_met":     milestone_met,
            "milestone_bonus":   milestone_bonus,
            "monopoly_genre":    monopoly_genre,
            "show_breakdowns":   show_breakdowns,
            "vault_breakdowns":  vault_breakdowns,
            "status":            status,
            # Seasonal additions
            "new_seasonal_event":       new_seasonal_event,
            "seasonal_event_messages":  seasonal_event_messages,
            "active_seasonal_modifiers": [
                {
                    "name": e["event"].get("name", "?"),
                    "desc": e["event"].get("desc", ""),
                    "remaining": e["remaining_seasons"],
                    "kind": e["event"].get("kind", "modifier"),
                }
                for e in self.active_seasonal_modifiers
            ],
            "active_contracts": [
                {
                    "name":      e["event"].get("name", "?"),
                    "req_desc":  describe_requirement(e["event"].get("requirement", {})),
                    "remaining": e["remaining_seasons"],
                    "fulfilled": e["fulfilled"],
                }
                for e in self.active_contracts
            ],
            "active_mandates": [
                {
                    "name":      e["event"].get("name", "?"),
                    "req_desc":  describe_requirement(e["event"].get("requirement", {})),
                    "remaining": e["remaining_seasons"],
                }
                for e in self.active_mandates
            ],
            "bailout_available": bailout_available,
            "bailout_tier":      (self.bailouts_used + 1) if bailout_available else None,
            # Season-level totals — sum of all per-show components plus season events
            "totals": {
                "total_views":           season_views,
                "total_net_income":      rnd2(season_income),
                "total_ad_income":       rnd2(sum(b["ad_income"]       for b in show_breakdowns)),
                "total_star_income":     rnd2(sum(b["star_income"]     for b in show_breakdowns)),
                "total_upgrade_income":  rnd2(sum(b["upgrade_income"]  for b in show_breakdowns)),
                "total_monopoly_income": rnd2(sum(b["monopoly_income"] for b in show_breakdowns)),
                "total_seasonal_income": rnd2(sum(b["seasonal_income"] for b in show_breakdowns)),
                "total_show_upkeep":     rnd2(sum(b["show_upkeep"]     for b in show_breakdowns)),
                "total_star_upkeep":     rnd2(sum(b["star_upkeep"]     for b in show_breakdowns)),
                "total_upkeep":          rnd2(sum(b["upkeep"]          for b in show_breakdowns)),
                "cooking_budget_boost":  cooking_boost_amount,
                "contract_income":       season_contract_income,
                "mandate_penalty":       season_mandate_penalty,
                "milestone_bonus":       milestone_bonus,
            },
        }

        # ── Ledger entries for this season ────────────────────────────────────
        s_num = self.season   # season that just aired (before increment)
        budget_delta = rnd2(season_income)
        self._ledger_append(
            s_num, "AIRED",
            f"Views +{int(season_views)}  Budget Δ${budget_delta:+.0f}  Net ${self.budget:.0f}",
        )
        if self.seasonal_events_enabled:
            for entry in expired_contracts:
                name       = entry["event"].get("name", "?")
                status_str = "WIN" if entry["fulfilled"] else "FAIL"
                pen    = entry["event"].get("penalty", {})
                rew    = entry["event"].get("reward", {})
                amount = int(rew.get("budget_bonus", 0) if entry["fulfilled"]
                             else pen.get("budget_loss", 0))
                self._ledger_append(s_num, "CONTRACT", f"{name}  {status_str}  ${amount}")

        # ── Auto-save after every completed season ─────────────────────────────
        if status == "continue":
            self.season += 1
            self.generate_shop()
            _platform.save_game(0, self._serialize())
        else:
            # Run ended (win or loss) — clear save so RESUME is not offered
            _platform.delete_save(0)

        return {
            "status":                status,
            "season_views":          season_views,
            "season_income":         round(season_income, 2),
            "milestone_met":         milestone_met,
            "milestone_bonus":       milestone_bonus,
            "monopoly_genre":        monopoly_genre,
            "new_seasonal_event":    new_seasonal_event,
            "seasonal_event_messages": seasonal_event_messages,
            "season_summary":        self.last_season_summary,
        }

    # ─── QUERY HELPERS ────────────────────────────────────────────────────────

    def get_lineup_summary(self) -> dict:
        """Return a read-only snapshot of current monopoly and lineup status."""
        live       = show_pool.all_live_shows(self.lineup)
        all_filled = all(s is not None for s in self.lineup)
        genres     = list({s.get("genre") for s in live if s.get("genre")})

        is_mono = False
        mono_g  = None
        mono_b  = None
        if all_filled and len(genres) == 1:
            registry = show_pool.get_genre_registry()
            entry    = registry.get(genres[0], {})
            if entry.get("monopoly"):
                is_mono = True
                mono_g  = genres[0]
                mono_b  = entry["monopoly"]

        return {
            "is_monopoly": is_mono,
            "genre":       mono_g,
            "bonus":       mono_b,
            "all_filled":  all_filled,
            "live_genres": genres,
            "show_count":  len(live),
        }

    def preview_lineup_yield(self) -> tuple:
        """Return (projected_views, projected_income) for the current lineup and vault."""
        key = (
            self.season,
            len(self.active_perks),
            tuple(id(s) for s in self.lineup),
            tuple(id(s) for s in self.reruns),
        )
        if self._proj_cache_key == key:
            return self._proj_cache_pv, self._proj_cache_pi

        pv: int   = 0
        pi: float = 0.0
        for idx, show in enumerate(self.lineup):
            if show and not show.get("is_extension"):
                yld = calculate_yield(show, start_idx=idx,
                                      active_perks=self.active_perks, season=self.season)
                pv += yld["v"]
                pi += yld["i"]
        for show in self.reruns:
            if show:
                yld = calculate_yield(show, is_rerun=True,
                                      active_perks=self.active_perks, season=self.season)
                pv += yld["v"]
                pi += yld["i"]

        self._proj_cache_key = key
        self._proj_cache_pv  = pv
        self._proj_cache_pi  = pi
        return pv, pi

    def preview_lineup_breakdown(self) -> tuple:
        """Return (proj_views, gross_income, total_upkeep) for the three-line budget display."""
        pv: int   = 0
        gross: float = 0.0
        upk:   float = 0.0
        for idx, show in enumerate(self.lineup):
            if show and not show.get("is_extension"):
                yld = calculate_yield(show, start_idx=idx,
                                      active_perks=self.active_perks, season=self.season)
                pv    += yld["v"]
                upk   += yld["upkeep"]
                gross += yld["i"] + yld["upkeep"]   # net + upkeep = gross
        for show in self.reruns:
            if show:
                yld = calculate_yield(show, is_rerun=True,
                                      active_perks=self.active_perks, season=self.season)
                pv    += yld["v"]
                gross += yld["i"]   # reruns have zero upkeep
        return pv, rnd2(gross), rnd2(upk)

    def preview_yield(self, show: dict, slot_idx: int,
                      extra_star: dict = None, extra_ad: dict = None) -> dict | None:
        """Non-destructive yield preview for tooltip display; return calculate_yield() dict or None."""
        if not show or show.get("is_extension"):
            return None

        temp = {
            **show,
            "attached": {
                "star": ([*show["attached"]["star"], extra_star] if extra_star
                         else show["attached"]["star"]),
                "ad":   ([*show["attached"]["ad"],   extra_ad]   if extra_ad
                         else show["attached"]["ad"]),
            },
        }
        return calculate_yield(
            temp,
            is_rerun     = False,
            start_idx    = slot_idx,
            active_perks = self.active_perks,
            season       = self.season,
        )
