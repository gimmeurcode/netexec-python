"""
cardpool.py — NETEXEC
=====================
Generic lazy-loading shuffleable card pool.

Eliminates the duplicated _DB / _ensure_loaded / build_pool / pop_for_shop
boilerplate that was repeated in shows.py, stars.py, ads.py, upgrades.py,
and events.py.

Loader return conventions
-------------------------
  list                    items only, no wildcard
  (list, wildcard)        items + optional wildcard (None is fine)
  (list, extra, wildcard) items + side data (stored in .extra) + optional wildcard
"""

import random
from engine.cards import stamp_uids


class CardPool:
    """
    Lazy-loading, shuffle-on-build card pool parameterised by a loader function.

    The loader is called exactly once per process (cached on ``_db``).
    Three return-value shapes are detected automatically:

    * ``list``                 — items only, no wildcard
    * ``(list, wildcard)``     — items + wildcard (``None`` wildcard is skipped)
    * ``(list, extra, wildcard)`` — items + side data exposed as ``.extra``
    """

    def __init__(self, loader_fn):
        self._loader   = loader_fn
        self._db       = None
        self._wildcard = None
        self.extra     = None  # populated when loader returns a 3-tuple

    def _ensure_loaded(self):
        if self._db is not None:
            return
        result = self._loader()
        if isinstance(result, tuple):
            if len(result) == 3:
                self._db, self.extra, self._wildcard = result
            else:
                self._db, self._wildcard = result
        else:
            self._db = result

    def build(self) -> list:
        """
        Return a new shuffled pool list (shallow dict-copies of all items).
        The wildcard template, if present, is appended once before shuffling.
        """
        self._ensure_loaded()
        pool = [dict(item) for item in self._db]
        if self._wildcard:
            pool.append(dict(self._wildcard))
        random.shuffle(pool)
        return pool

    def pop_for_shop(self, pool: list, count: int) -> list:
        """
        Pop up to *count* items from *pool* (mutates it) and stamp them with
        unique shop UIDs.
        """
        items = []
        for _ in range(count):
            if pool:
                items.append(pool.pop())
        return stamp_uids(items)

    def wildcard(self):
        """Return the raw wildcard template dict, or ``None``."""
        self._ensure_loaded()
        return self._wildcard
