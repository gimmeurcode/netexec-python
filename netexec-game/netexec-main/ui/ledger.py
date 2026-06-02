"""
ledger.py — NETEXEC
====================
Terminal ledger panel — read-only financial history log.

Renders `state.ledger_log` in the right panel area with mouse-wheel scroll.
The Ledger class also provides serialize/deserialize helpers for save system
integration; the actual log list lives on GameState to avoid UI→engine imports.
"""

import pygame

from scripts.engine.constants import (
    C_PANEL, C_PANEL_BORDER, C_GREEN_BRIGHT, C_GREEN_MID, C_GREEN_DIM,
    C_AMBER, C_RED, C_WHITE, C_GREY_LIGHT, C_GREY_MID, C_GREY_DARK, PAD,
)


# ─── CATEGORY COLOUR MAP ──────────────────────────────────────────────────────

_CAT_COLORS = {
    "BUY":      C_AMBER,
    "AIRED":    C_GREEN_BRIGHT,
    "CONTRACT": C_WHITE,
    "BAILOUT":  C_RED,
}


class Ledger:
    """Wraps state.ledger_log to provide rendering and save-serialisation."""

    # ── Serialisation ──────────────────────────────────────────────────────────

    @staticmethod
    def serialize(state) -> list:
        """Return a JSON-serialisable copy of the ledger log for save integration."""
        return list(getattr(state, "ledger_log", []))

    @staticmethod
    def deserialize(data: list, state) -> None:
        """Restore ledger_log on state from a loaded save dict."""
        state.ledger_log = list(data) if isinstance(data, list) else []

    # ── Rendering ─────────────────────────────────────────────────────────────

    @staticmethod
    def draw(ctx, state) -> None:
        """Render the read-only terminal ledger in the right panel area."""
        lo  = ctx.layout
        rx  = lo.right_x
        rw  = lo.right_w
        ry  = lo.hud_h + PAD
        rh  = ctx._sh - ry - PAD

        # Panel background
        panel = pygame.Rect(rx, ry, rw, rh)
        pygame.draw.rect(ctx.screen, C_PANEL,        panel, border_radius=4)
        pygame.draw.rect(ctx.screen, C_PANEL_BORDER, panel, 1, border_radius=4)

        # Header row
        f_bold = ctx._f("bold")
        f_mi   = ctx._f("micro")
        f_sm   = ctx._f("small")

        header_surf = f_bold.render("LEDGER — FINANCIAL HISTORY", True, C_GREEN_BRIGHT)
        ctx.screen.blit(header_surf, (rx + 8, ry + 6))
        pygame.draw.line(ctx.screen, C_PANEL_BORDER,
                         (rx + 4, ry + 24), (rx + rw - 4, ry + 24))

        entries: list[str] = getattr(state, "ledger_log", [])
        if not entries:
            empty = f_mi.render("No entries yet — make purchases or air a season.", True, C_GREY_MID)
            ctx.screen.blit(empty, (rx + 8, ry + 34))
            return

        # Scroll clamp: auto-scroll to bottom when a new entry arrived
        line_h   = f_mi.get_linesize() + 2
        content_h = len(entries) * line_h
        visible_h = rh - 30
        max_scroll = max(0, content_h - visible_h)

        # Track entry count to auto-scroll when new entries appear
        prev_count = getattr(ctx, "_ledger_prev_count", 0)
        if len(entries) != prev_count:
            ctx._ledger_scroll      = max_scroll
            ctx._ledger_prev_count  = len(entries)
        ctx._ledger_scroll = max(0, min(ctx._ledger_scroll, max_scroll))

        # Clip rendering to the content area
        clip = pygame.Rect(rx + 2, ry + 28, rw - 4, visible_h)
        ctx.screen.set_clip(clip)

        y = ry + 30 - ctx._ledger_scroll
        for entry in entries:
            if y + line_h < clip.top:
                y += line_h
                continue
            if y > clip.bottom:
                break

            # Parse category from entry (format: "S01  CAT         text")
            parts = entry.split("  ", 2)
            cat   = parts[1].strip() if len(parts) >= 2 else ""
            col   = _CAT_COLORS.get(cat, C_GREY_LIGHT)

            # Season tag in dim green, rest in category colour
            tag  = parts[0] if parts else ""
            rest = "  ".join(parts[1:]) if len(parts) > 1 else entry
            tag_surf  = f_mi.render(tag, True, C_GREEN_DIM)
            rest_surf = f_mi.render(rest, True, col)
            ctx.screen.blit(tag_surf,  (rx + 8, y))
            ctx.screen.blit(rest_surf, (rx + 8 + tag_surf.get_width() + 4, y))
            y += line_h

        ctx.screen.set_clip(None)

        # Scrollbar when content overflows
        if content_h > visible_h:
            sb_x = rx + rw - 6
            sb_h = int(visible_h * visible_h / content_h)
            sb_y = ry + 28 + int(ctx._ledger_scroll / max(max_scroll, 1)
                                  * (visible_h - sb_h))
            pygame.draw.rect(ctx.screen, C_GREY_DARK,
                             pygame.Rect(sb_x, ry + 28, 4, visible_h), border_radius=2)
            pygame.draw.rect(ctx.screen, C_GREEN_MID,
                             pygame.Rect(sb_x, sb_y, 4, max(sb_h, 16)), border_radius=2)
