"""
yields.py — NETEXEC
===================
Pure per-show season yield pipeline (split out of network.py).

Stateless functions only: the 9-stage view/income math culminating in
``calculate_yield``. ``engine.state.GameState`` and the UI import from here;
``engine.network`` re-exports these names for backward compatibility.
"""

import math
import random

import saves as _platform
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
from content import shows   as show_pool
from content import stars   as star_pool
from content import ads     as ad_pool
from content import upgrades as upg_pool
from content import events   as event_pool


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
