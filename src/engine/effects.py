"""
effects.py — NETEXEC
====================
Data-driven upgrade effect resolver.

Every upgrade in upgrades.json carries an "effects" list.  Each entry has:
  "when":  condition that must hold for this effect to fire
  "scope": "any" | "live" | "vault"  (default: "any")
  "apply": dict with one or more effect keys

Condition types (for "when"):
  {"type": "always"}
  {"type": "genre",    "genres":     [...]}   show.genre in list
  {"type": "age_min",  "value":      N}       show.age >= N
  {"type": "slot",     "slots":      [...]}   any of show's slot_indices in list
  {"type": "has_stars"}                        show has >= 1 attached star
  {"type": "has_ads"}                          show has >= 1 attached ad
  {"type": "and",      "conditions": [...]}   all sub-conditions must hold

Apply keys (all optional; combine freely in one dict):
  "v_flat":        int    add flat views
  "v_mult":        float  multiply into mult accumulator
  "income_flat":   int    add flat income
  "income_per_ad": int    add (num_attached_ads * value) to income
  "v_per_season":  int    add (season * value) to views
  "rerun_vmult":   float  add to rerun view multiplier (vault scope only)

Scope semantics:
  "any"   — fires for both live and vault shows
  "live"  — fires only for live (non-rerun) shows
  "vault" — handled exclusively by resolve_vault_rerun(); intentionally
             skipped in resolve_upgrade_effects() to avoid double-counting
             vault income in the normal accumulation loop
"""


def _check_condition(when: dict, show: dict, slot_indices: list, season: int = 1) -> bool:
    ctype = when.get("type", "always")
    if ctype == "always":
        return True
    if ctype == "genre":
        return show.get("genre") in when.get("genres", [])
    if ctype == "genre_not":
        return show.get("genre") not in when.get("genres", [])
    if ctype == "age_min":
        return show.get("age", 1) >= when.get("value", 1)
    if ctype == "age_max":
        return show.get("age", 1) <= when.get("value", 1)
    if ctype == "size_min":
        return show.get("size", 1) >= when.get("value", 2)
    if ctype == "slot":
        return any(s in slot_indices for s in when.get("slots", []))
    if ctype == "has_stars":
        return bool(show.get("attached", {}).get("star", []))
    if ctype == "has_ads":
        return bool(show.get("attached", {}).get("ad", []))
    if ctype == "star_count_min":
        return len(show.get("attached", {}).get("star", [])) >= when.get("value", 1)
    if ctype == "ad_count_min":
        return len(show.get("attached", {}).get("ad", [])) >= when.get("value", 1)
    if ctype == "season_min":
        return season >= when.get("value", 1)
    if ctype == "season_max":
        return season <= when.get("value", 1)
    if ctype == "and":
        return all(
            _check_condition(c, show, slot_indices, season)
            for c in when.get("conditions", [])
        )
    if ctype == "or":
        return any(
            _check_condition(c, show, slot_indices, season)
            for c in when.get("conditions", [])
        )
    if ctype == "not":
        return not _check_condition(when.get("condition", {"type": "always"}),
                                    show, slot_indices, season)
    return True  # unknown type → fail-safe (don't silently drop bonuses)


def resolve_upgrade_effects(
    perk: dict,
    show: dict,
    slot_indices: list,
    is_rerun: bool,
    season: int,
) -> tuple[float, float, float]:
    """Interpret a perk's effects list; return (v_add, mult_factor, income_add)."""
    v_add = 0.0
    mult_factor = 1.0
    income_add = 0.0

    ads   = show.get("attached", {}).get("ad", [])
    stars = show.get("attached", {}).get("star", [])
    age   = show.get("age", 1)

    for eff in perk.get("effects", []):
        scope = eff.get("scope", "any")
        if scope == "vault":
            continue              # vault path handled by resolve_vault_rerun
        if scope == "live" and is_rerun:
            continue

        when = eff.get("when", {"type": "always"})
        if not _check_condition(when, show, slot_indices, season):
            continue

        ap = eff.get("apply", {})
        v_add += ap.get("v_flat", 0)
        v_add += ap.get("v_per_season", 0) * season
        v_add += ap.get("v_per_ad", 0) * len(ads)
        v_add += ap.get("v_flat_per_age", 0) * age

        vm = ap.get("v_mult", 1.0)
        if vm != 1.0:
            mult_factor *= vm

        income_add += ap.get("income_flat", 0)
        income_add += ap.get("income_per_ad", 0) * len(ads)
        income_add += ap.get("income_per_star", 0) * len(stars)

    return v_add, mult_factor, income_add


def resolve_vault_rerun(
    active_perks: list,
    show: dict,
    slot_indices: list,
) -> tuple[float, float]:
    """Compute rerun view multiplier and income for a vault show; return (view_mult, income)."""
    rerun_view_mult = 0.25
    rerun_income = 0.0

    for perk in active_perks:
        for eff in perk.get("effects", []):
            if eff.get("scope") != "vault":
                continue
            when = eff.get("when", {"type": "always"})
            if not _check_condition(when, show, slot_indices):
                continue
            ap = eff.get("apply", {})
            rerun_view_mult += ap.get("rerun_vmult", 0.0)
            rerun_income    += ap.get("income_flat", 0)

    return rerun_view_mult, rerun_income
