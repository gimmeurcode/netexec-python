"""
events.py — NETEXEC
====================
Event pool management and event effect execution.

Events are one-off cards: purchased immediately, consumed on use, and applied
instantly via apply_event(). No placement step is needed.

Each event in events.json has an 'effect_type' string and an 'effect_params'
dict. apply_event() looks up the effect_type in the handler registry and
calls the registered function.

Adding a new event type:
  1. Add an entry to data/events.json with the new effect_type string.
  2. Add a @event_handler("your_effect_type") decorated function here.
  3. No other files need touching.
"""

from engine.cards import load_events
from .cardpool import CardPool

# load_events() returns a plain list — no wildcard
_pool = CardPool(load_events)


# ─── HANDLER REGISTRY ────────────────────────────────────────────────────────

_REGISTRY: dict = {}


def event_handler(effect_type: str):
    """
    Decorator that registers a callable as the handler for an event effect_type.

    Each handler receives (event, state, generate_shop_fn) and must return a
    dict with keys {ok (bool), message (str), level (str)}.  generate_shop_fn
    may be None; most handlers ignore it (only free_reroll uses it).

    Usage:
        @event_handler("my_type")
        def _handle_my_type(event, state, generate_shop_fn):
            ...
            return {"ok": True, "message": "...", "level": "success"}
    """
    def decorator(fn):
        _REGISTRY[effect_type] = fn
        return fn
    return decorator


def get_registered_effect_types() -> set:
    """Return all effect_type strings that have a registered handler."""
    return set(_REGISTRY.keys())


# ─── POOL MANAGEMENT ─────────────────────────────────────────────────────────

def build_pool() -> list:
    """
    Build a shuffled pool of all available events.

    Returns
    -------
    list  Shuffled event dicts (copies).
    """
    return _pool.build()


def pop_for_shop(pool: list, count: int) -> list:
    """
    Pop up to `count` events from the pool with unique shop UIDs.

    Parameters
    ----------
    pool  : list  Mutable event pool.
    count : int   Maximum items to pop.

    Returns
    -------
    list  Events with 'uid' added.
    """
    return _pool.pop_for_shop(pool, count)


# ─── EVENT HANDLERS ───────────────────────────────────────────────────────────

@event_handler("add_views")
def _handle_add_views(event, state, generate_shop_fn):
    params = event.get("effect_params", {})
    name   = event.get("name", "Event")
    views  = params.get("views", 0)
    state.total_views += views
    return {"ok": True, "message": f"{name}: +{views} VIEWS", "level": "success"}


@event_handler("add_budget")
def _handle_add_budget(event, state, generate_shop_fn):
    params = event.get("effect_params", {})
    name   = event.get("name", "Event")
    amount = params.get("amount", 0)
    state.budget += amount
    return {"ok": True, "message": f"{name}: +${amount} BUDGET", "level": "success"}


@event_handler("add_budget_and_views")
def _handle_add_budget_and_views(event, state, generate_shop_fn):
    params = event.get("effect_params", {})
    name   = event.get("name", "Event")
    budget = params.get("budget", 0)
    views  = params.get("views", 0)
    state.budget      += budget
    state.total_views += views
    return {
        "ok": True,
        "message": f"{name}: +{views} VIEWS & +${budget} BUDGET",
        "level": "success",
    }


@event_handler("free_reroll")
def _handle_free_reroll(event, state, generate_shop_fn):
    name = event.get("name", "Event")
    if generate_shop_fn:
        generate_shop_fn()
    return {"ok": True, "message": f"{name}: SHOP REFRESHED", "level": "info"}


@event_handler("reduce_lineup_age")
def _handle_reduce_lineup_age(event, state, generate_shop_fn):
    params  = event.get("effect_params", {})
    name    = event.get("name", "Event")
    amount  = params.get("amount", 1)
    min_age = params.get("min_age", 1)
    affected = 0
    for show in state.lineup:
        if show and not show.get("is_extension"):
            old = show["age"]
            show["age"] = max(min_age, show["age"] - amount)
            if show["age"] < old:
                affected += 1
    if affected == 0:
        return {"ok": True, "message": f"{name}: NO SHOWS TO RETOOL", "level": "warn"}
    return {"ok": True, "message": f"{name}: {affected} SHOW(S) REJUVENATED", "level": "success"}


@event_handler("boost_lineup_base_views")
def _handle_boost_lineup_base_views(event, state, generate_shop_fn):
    params   = event.get("effect_params", {})
    name     = event.get("name", "Event")
    amount   = params.get("amount", 0)
    affected = 0
    for show in state.lineup:
        if show and not show.get("is_extension"):
            show["base_views"] += amount
            affected += 1
    if affected == 0:
        return {"ok": True, "message": f"{name}: NO SHOWS IN LINEUP", "level": "warn"}
    return {
        "ok": True,
        "message": f"{name}: +{amount} BASE VIEWS TO {affected} SHOW(S)",
        "level": "success",
    }


@event_handler("budget_boost_views_penalty")
def _handle_budget_boost_views_penalty(event, state, generate_shop_fn):
    params         = event.get("effect_params", {})
    name           = event.get("name", "Event")
    budget         = params.get("budget", 0)
    views_loss     = params.get("base_views_loss", 0)
    min_base_views = params.get("min_base_views", 10)
    state.budget  += budget
    affected       = 0
    for show in state.lineup:
        if show and not show.get("is_extension"):
            show["base_views"] = max(min_base_views, show["base_views"] - views_loss)
            affected += 1
    return {
        "ok": True,
        "message": (
            f"{name}: +${budget} BUDGET"
            + (f" / -{views_loss} BASE VIEWS ON {affected} SHOW(S)" if affected else "")
        ),
        "level": "warn",
    }


@event_handler("reduce_all_upkeep")
def _handle_reduce_all_upkeep(event, state, generate_shop_fn):
    params     = event.get("effect_params", {})
    name       = event.get("name", "Event")
    amount     = params.get("amount", 0)
    min_upkeep = params.get("min_upkeep", 0)
    affected   = 0
    for show in state.lineup:
        if show and not show.get("is_extension"):
            old = show.get("upkeep", 0)
            show["upkeep"] = max(min_upkeep, old - amount)
            if show["upkeep"] < old:
                affected += 1
    if affected == 0:
        return {"ok": True, "message": f"{name}: NOTHING TO REDUCE", "level": "warn"}
    return {
        "ok": True,
        "message": f"{name}: UPKEEP -${amount} ON {affected} SHOW(S)",
        "level": "success",
    }


@event_handler("reduce_upkeep_and_budget")
def _handle_reduce_upkeep_and_budget(event, state, generate_shop_fn):
    params       = event.get("effect_params", {})
    name         = event.get("name", "Event")
    amount       = params.get("amount", 0)
    min_upkeep   = params.get("min_upkeep", 0)
    budget_bonus = params.get("budget_bonus", 0)
    affected     = 0
    for show in state.lineup:
        if show and not show.get("is_extension"):
            old = show.get("upkeep", 0)
            show["upkeep"] = max(min_upkeep, old - amount)
            if show["upkeep"] < old:
                affected += 1
    if budget_bonus:
        state.budget += budget_bonus
    parts = []
    if affected:
        parts.append(f"UPKEEP -${amount} ON {affected} SHOW(S)")
    if budget_bonus:
        parts.append(f"+${budget_bonus} BUDGET")
    msg = f"{name}: " + " & ".join(parts) if parts else f"{name}: NO EFFECT"
    return {"ok": True, "message": msg, "level": "success"}


@event_handler("age_show_and_boost_views")
def _handle_age_show_and_boost_views(event, state, generate_shop_fn):
    params       = event.get("effect_params", {})
    name         = event.get("name", "Event")
    age_increase = params.get("age_increase", 1)
    views_bonus  = params.get("views_bonus", 0)
    target       = params.get("target", "oldest_lineup")

    live = [s for s in state.lineup if s and not s.get("is_extension")]
    if not live:
        return {"ok": True, "message": f"{name}: NO SHOWS IN LINEUP", "level": "warn"}

    if target == "oldest_lineup":
        show = max(live, key=lambda s: s.get("age", 1))
    else:
        show = live[0]

    show["age"]       += age_increase
    state.total_views += views_bonus
    return {
        "ok": True,
        "message": f"{name}: {show['name']} AGED +{age_increase} / +{views_bonus} VIEWS",
        "level": "info",
    }


@event_handler("add_views_cost_budget")
def _handle_add_views_cost_budget(event, state, generate_shop_fn):
    """TRADEOFF: a big immediate view injection paid for in cash."""
    params = event.get("effect_params", {})
    name   = event.get("name", "Event")
    views  = params.get("views", 0)
    cost   = params.get("budget_cost", 0)
    state.total_views += views
    state.budget      -= cost
    return {
        "ok": True,
        "message": f"{name}: +{views} VIEWS / -${cost} BUDGET",
        "level": "warn",
    }


@event_handler("swap_budget_for_views")
def _handle_swap_budget_for_views(event, state, generate_shop_fn):
    """UNIQUE: convert a chunk of cash into views at a favourable rate.

    Spends up to `max_spend` (capped by available budget) and converts it to
    views at `views_per_dollar`. A net-positive money sink for cash-rich runs.
    """
    params  = event.get("effect_params", {})
    name    = event.get("name", "Event")
    rate    = params.get("views_per_dollar", 8)
    desired = params.get("max_spend", 40)
    spend   = int(max(0, min(desired, state.budget)))
    if spend <= 0:
        return {"ok": True, "message": f"{name}: NO BUDGET TO SPEND", "level": "warn"}
    gained = spend * rate
    state.budget      -= spend
    state.total_views += gained
    return {
        "ok": True,
        "message": f"{name}: -${spend} BUDGET → +{gained} VIEWS",
        "level": "success",
    }


@event_handler("multiply_total_views")
def _handle_multiply_total_views(event, state, generate_shop_fn):
    """UNIQUE/TRADEOFF: scale current lifetime views by a factor, paid in cash.

    The reward scales with how far along the run is — strongest late-game — and
    is offset by a flat budget cost so it is not free.
    """
    params = event.get("effect_params", {})
    name   = event.get("name", "Event")
    factor = params.get("factor", 1.15)
    cost   = params.get("budget_cost", 0)
    before = state.total_views
    gained = int(before * factor) - before
    state.total_views += gained
    state.budget      -= cost
    return {
        "ok": True,
        "message": f"{name}: +{gained} VIEWS (x{factor}) / -${cost} BUDGET",
        "level": "warn",
    }


@event_handler("genre_surge")
def _handle_genre_surge(event, state, generate_shop_fn):
    """TRADEOFF/UNIQUE: supercharge one genre's base views, at the expense of the rest."""
    params   = event.get("effect_params", {})
    name     = event.get("name", "Event")
    genre    = params.get("genre", "")
    boost    = params.get("boost", 0)
    penalty  = params.get("penalty", 0)
    min_base = params.get("min_base_views", 10)
    up = down = 0
    for show in state.lineup:
        if not show or show.get("is_extension"):
            continue
        if show.get("genre") == genre:
            show["base_views"] += boost
            up += 1
        elif penalty:
            show["base_views"] = max(min_base, show["base_views"] - penalty)
            down += 1
    if up == 0 and down == 0:
        return {"ok": True, "message": f"{name}: NO SHOWS IN LINEUP", "level": "warn"}
    return {
        "ok": True,
        "message": f"{name}: {genre} +{boost} BASE ({up}) / -{penalty} OTHERS ({down})",
        "level": "warn",
    }


@event_handler("boost_views_per_ad")
def _handle_boost_views_per_ad(event, state, generate_shop_fn):
    """UNIQUE: a view payout that scales with how ad-saturated your lineup is."""
    params  = event.get("effect_params", {})
    name    = event.get("name", "Event")
    per_ad  = params.get("views_per_ad", 30)
    total_ads = 0
    for show in state.lineup:
        if show and not show.get("is_extension"):
            total_ads += len(show.get("attached", {}).get("ad", []))
    gained = per_ad * total_ads
    state.total_views += gained
    if total_ads == 0:
        return {"ok": True, "message": f"{name}: NO ADS ATTACHED (+0 VIEWS)", "level": "warn"}
    return {
        "ok": True,
        "message": f"{name}: +{gained} VIEWS ({total_ads} ADS x{per_ad})",
        "level": "success",
    }


@event_handler("retool_lineup_for_views")
def _handle_retool_lineup_for_views(event, state, generate_shop_fn):
    """TRADEOFF: rejuvenate the whole lineup (reset ages) — but burn lifetime views to do it."""
    params     = event.get("effect_params", {})
    name       = event.get("name", "Event")
    reset_to   = params.get("reset_age_to", 1)
    views_cost = params.get("views_cost", 0)
    affected = 0
    for show in state.lineup:
        if show and not show.get("is_extension"):
            if show.get("age", 1) > reset_to:
                show["age"] = reset_to
                affected += 1
    state.total_views = max(0, state.total_views - views_cost)
    return {
        "ok": True,
        "message": f"{name}: {affected} SHOW(S) RETOOLED / -{views_cost} VIEWS",
        "level": "warn",
    }


# ─── DISPATCHER ───────────────────────────────────────────────────────────────

def apply_event(event: dict, state, generate_shop_fn=None) -> dict:
    """
    Execute a one-off event's effect against the current game state.

    Looks up the handler for event['effect_type'] in the registry and calls it.
    Returns a summary dict the UI can use for toast messages.

    Parameters
    ----------
    event           : dict  The event card being purchased.
    state           : GameState  The mutable game state.
    generate_shop_fn: callable or None  Passed to handlers that refresh the shop.

    Returns
    -------
    dict with keys:
      ok      (bool)   True if the event applied successfully.
      message (str)    Human-readable result for the toast notification.
      level   (str)    Toast level: 'success', 'info', 'warn', 'error'.
    """
    etype   = event.get("effect_type", "")
    handler = _REGISTRY.get(etype)
    if handler is None:
        return {
            "ok": False,
            "message": f"UNKNOWN EVENT TYPE: {etype}",
            "level": "error",
        }
    return handler(event, state, generate_shop_fn)
