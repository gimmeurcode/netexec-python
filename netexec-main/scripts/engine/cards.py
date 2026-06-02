"""
cards.py — NETEXEC
==================
Card data models and condition evaluation engine.

All card data lives in the JSON files under data/. This module provides:
  - load_*()         Functions to load each card type from JSON.
  - check_condition()  Evaluate a JSON-encoded condition against a show.
  - evaluate_star()    Apply star condition → return effective stats dict.
  - evaluate_ad()      Apply ad condition → return effective stats dict.
  - normalize_effect() Fill defaults so callers always get all fields.
  - make_show_instance() Clone a show template into a live show with age/attachments.
  - make_uid()         Generate a short unique ID for shop items.

The condition encoding scheme (stored in JSON):
  {"type": "always"}                  → always fires
  {"type": "genre", "genres": [...]}  → show.genre in genres
  {"type": "size_min", "value": N}    → show.size >= N
  {"type": "ad_slots_min","value": N} → show.ad_slots >= N
  {"type": "age_min", "value": N}     → show.age >= N

Effect/fallback dicts (all fields optional, defaults shown):
  {"v_flat": 0, "v_mult": 1.0, "income": 0, "upkeep": 0}
"""

import json
import os
import sys
import uuid


def _get_data_dir() -> str:
    # When packaged by PyInstaller (--onefile), all bundled files are extracted
    # to a temp directory stored in sys._MEIPASS. data/ lands there directly.
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'data')
    # Development: cards.py is in scripts/engine/, data/ is two levels up.
    return os.path.join(os.path.dirname(__file__), '..', '..', 'data')


_DATA_DIR = _get_data_dir()


# ─── JSON LOADERS ─────────────────────────────────────────────────────────────

def _load_json(filename: str) -> dict:
    """Load and parse a JSON file from the data/ directory."""
    path = os.path.join(_DATA_DIR, filename)
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Data file not found: {path}\n"
            f"Make sure the data/ folder is next to the netexec-main/ directory."
        )
    with open(path, "r", encoding="utf-8") as fh:
        # Strip // line comments before parsing — JSON doesn't support them
        # natively, but our data files use them for readability.
        lines   = fh.readlines()
        cleaned = [l for l in lines if not l.strip().startswith("//")]
        return json.loads("".join(cleaned))


def load_shows() -> tuple[list, dict, dict]:
    """Load the show database, genre registry, and wildcard template from shows.json."""
    data = _load_json("shows.json")
    return (
        data["shows"],
        data.get("genre_registry", {}),
        data.get("wildcard", None),
    )


def load_stars() -> tuple[list, None]:
    """Load the star database from stars.json."""
    data = _load_json("stars.json")
    return data["stars"], None


def load_ads() -> tuple[list, dict]:
    """Load the ad database and wildcard template from ads.json."""
    data = _load_json("ads.json")
    return data["ads"], data.get("wildcard", None)


def load_upgrades() -> list:
    """Load the upgrade database from upgrades.json."""
    data = _load_json("upgrades.json")
    return data["upgrades"]


def load_events() -> list:
    """Load the event database from events.json."""
    data = _load_json("events.json")
    return data["events"]


def load_wildcards() -> dict:
    """Load the wildcard configuration options from wildcards.json."""
    return _load_json("wildcards.json")


def load_seasonal_events() -> list:
    """Load the seasonal events database from seasonal_events.json."""
    data = _load_json("seasonal_events.json")
    return data["events"]


def load_bailouts() -> list:
    """Load bailout tier definitions from bailouts.json."""
    data = _load_json("bailouts.json")
    return data["tiers"]


# ─── CONDITION EVALUATION ─────────────────────────────────────────────────────

def check_condition(condition: dict | None, show: dict) -> bool:
    """Evaluate a JSON-encoded condition against a live show instance; return bool."""
    if condition is None:
        return True

    ctype = condition.get("type", "always")

    if ctype == "always":
        return True

    elif ctype == "genre":
        genres = condition.get("genres", [])
        return show.get("genre") in genres

    elif ctype == "size_min":
        return show.get("size", 1) >= condition.get("value", 2)

    elif ctype == "ad_slots_min":
        # Support both new 'ad_slots' field and legacy 'slots.ad' dict form
        ad_slots = show.get("ad_slots", show.get("slots", {}).get("ad", 0))
        return ad_slots >= condition.get("value", 2)

    elif ctype == "age_min":
        return show.get("age", 1) >= condition.get("value", 1)

    # Unknown condition type — fail safe (fires effect so player doesn't
    # silently lose a card's bonus without explanation).
    return True


def normalize_effect(effect: dict) -> dict:
    """Return a complete effect dict with all fields filled to their defaults."""
    return {
        "v_flat":  int(effect.get("v_flat",  0)),
        "v_mult":  float(effect.get("v_mult",  1.0)),
        "income":  int(effect.get("income",  0)),
        "upkeep":  int(effect.get("upkeep",  0)),
    }


def evaluate_star(star: dict, show: dict) -> dict:
    """Apply a star's condition against a show and return the active normalized effect dict."""
    condition = star.get("condition")
    if check_condition(condition, show):
        raw = star.get("effect", {})
    else:
        raw = star.get("fallback", {})
    return normalize_effect(raw)


def evaluate_ad(ad: dict, show: dict) -> dict:
    """Apply an ad's condition against a show and return the active normalized effect dict."""
    condition = ad.get("condition")
    if check_condition(condition, show):
        raw = ad.get("effect", {})
    else:
        raw = ad.get("fallback", {})
    eff = normalize_effect(raw)
    eff["upkeep"] = 0   # ads never add upkeep
    return eff


# ─── SHOW INSTANCE FACTORY ────────────────────────────────────────────────────

def make_show_instance(template: dict) -> dict:
    """Clone a show template into a live show instance with age=1 and empty attachments."""
    instance = dict(template)          # shallow copy — don't mutate the template
    instance["age"]      = 1
    instance["attached"] = {"star": [], "ad": []}
    return instance


# ─── UID GENERATION ───────────────────────────────────────────────────────────

def make_uid() -> str:
    """Generate an 8-character hex unique identifier for shop items."""
    return uuid.uuid4().hex[:8]


def stamp_uids(items: list) -> list:
    """Return a new list where each item dict has a fresh uid field added."""
    return [{**item, "uid": make_uid()} for item in items]
