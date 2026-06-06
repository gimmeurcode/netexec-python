"""
shop.py — NETEXEC
=================
Right panel (Acquisition Terminal): the tab bar, the scrollable shop-item
viewport, and the reroll button. Individual item cards are drawn by
``cards.py`` and the contracts tab by ``contracts.py``; this module owns the
panel shell, tab overflow logic, scroll clipping, and the reroll control.

Public entry point
------------------
  _draw_right_panel(ctx, state)
"""

import pygame

from engine.constants import (
    PAD,
    C_BG, C_BORDER_DIM,
    C_AMBER, C_RED_DIM,
    C_GREEN_BRIGHT, C_GREEN_MID, C_GREEN_DIM, C_GREY_MID,
)
from ...theme import C_TINT_GREEN_TAB, TAB_COLORS
from ...widgets import draw_button, draw_scrollbar, draw_panel_box, line_step
from .cards import _draw_shop_card
from .contracts import _draw_contracts_section

_SBAR_W = 8   # scrollbar track width (px)

# --- RIGHT PANEL (SHOP) ---

def _draw_right_panel(ctx, state):
    """Draw the shop: tabs, item cards, and reroll button."""
    lo    = ctx.layout
    # Use the layout's pre-computed shop rect so padding is not applied twice.
    # lo.shop already includes inner PAD offsets from compute_layout().
    panel = pygame.Rect(lo.shop.x, lo.shop.y,
                        lo.shop.width, ctx._sh - lo.shop.y - PAD)
    x     = panel.x
    y0    = panel.y
    w     = panel.width
    draw_panel_box(ctx.screen, panel, title="ACQUISITION TERMINAL",
                   title_font=ctx._f("small"), bg_color=C_BG)
    y = y0 + 26

    # --- Tab bar with overflow affordance ---
    # Accent colors come from TAB_COLORS; active tab uses full color, inactive dimmed to 40%.
    tab_defs = [
        ("SHOWS",     "shows"),
        ("STARS",     "stars"),
        ("ADS",       "ads"),
        ("UPGRADES",  "upgrades"),
        ("EVENTS",    "events"),
        ("CONTRACTS", "contracts"),
    ]
    # Compute how many tabs fit at minimum tab_w=56; show overflow › if needed.
    min_tab_w  = 56
    overflow_w = 20
    n_fit      = min(len(tab_defs), max(1, (w - overflow_w) // min_tab_w))
    has_overflow = n_fit < len(tab_defs)
    tab_area_w = w - (overflow_w if has_overflow else 0)
    tab_w = tab_area_w // n_fit

    # Find which tabs to show: always include active tab
    active_idx = next(
        (i for i, (_, k) in enumerate(tab_defs) if k == state.current_tab), 0
    )
    start_tab = max(0, min(active_idx, len(tab_defs) - n_fit))
    visible_tabs = tab_defs[start_tab: start_tab + n_fit]

    for vi, (label, key) in enumerate(visible_tabs):
        tr      = pygame.Rect(x + vi * tab_w, y, tab_w - 1, lo.tab_row_h - 4)
        active  = state.current_tab == key
        count   = (len(state.available_contracts) + len(state.active_contracts)
                   if key == "contracts" else len(state.shop.get(key, [])))
        accent  = TAB_COLORS.get(key, C_GREEN_BRIGHT)
        # Inactive tabs dim to 40% so the active tab pops clearly (R3)
        dim_accent = tuple(int(c * 0.4) for c in accent)

        bg_col = C_TINT_GREEN_TAB if active else C_BG
        pygame.draw.rect(ctx.screen, bg_col, tr, border_radius=3)
        bd_col = accent if active else dim_accent
        pygame.draw.rect(ctx.screen, bd_col, tr, 1 if not active else 2, border_radius=3)
        if active:
            pygame.draw.rect(ctx.screen, accent,
                             pygame.Rect(tr.x + 2, tr.y, tr.width - 4, 3),
                             border_radius=2)
        tc = accent if active else dim_accent
        # Ellipsize label if tab is narrow
        lbl = label if tab_w >= 72 else label[:3]
        # Pick a label font that lets the label and its count stack on two
        # separated lines inside the tab cell; fall back to micro when short.
        tab_h    = lo.tab_row_h - 4
        lbl_font = ctx._f("small") if tab_h >= 46 else ctx._f("micro")
        label_surf = lbl_font.render(lbl, True, tc)
        if count > 0:
            cnt_col = tuple(int(c * 0.7) for c in tc)
            cnt_s   = ctx._f("micro").render(str(count), True, cnt_col)
            step    = line_step(lbl_font, 0.74)
            block_h = step + cnt_s.get_bounding_rect().height
            y1      = tr.y + max(2, (tab_h - block_h) // 2)
            ctx.screen.blit(label_surf, (tr.centerx - label_surf.get_width() // 2, y1))
            ctx.screen.blit(cnt_s, (tr.centerx - cnt_s.get_width() // 2, y1 + step))
        else:
            ctx.screen.blit(label_surf,
                            label_surf.get_rect(center=tr.center))

        def _tab(k=key):
            state.set_tab(k)
            ctx._shop_scroll = 0
        ctx._add_click(tr, _tab)

    if has_overflow:
        ov_r = pygame.Rect(x + tab_area_w, y, overflow_w - 2, lo.tab_row_h - 4)
        pygame.draw.rect(ctx.screen, C_BG, ov_r, border_radius=3)
        pygame.draw.rect(ctx.screen, C_BORDER_DIM, ov_r, 1, border_radius=3)
        ov_s = ctx._f("micro").render(">", True, C_GREEN_MID)
        ctx.screen.blit(ov_s, (ov_r.centerx - ov_s.get_width() // 2,
                                ov_r.centery - ov_s.get_height() // 2))
        def _overflow(s=start_tab):
            ns = (s + n_fit) % len(tab_defs)
            state.set_tab(tab_defs[ns][1])
            ctx._shop_scroll = 0
        ctx._add_click(ov_r, _overflow)

    y += lo.tab_row_h

    # --- Scrollable shop item list ---
    if state.current_tab == "contracts":
        items = list(state.available_contracts)
    else:
        items = state.shop.get(state.current_tab, [])
    item_stride   = lo.shop_card_h + 3
    if state.current_tab == "contracts":
        total_items_h = (
            (len(state.available_contracts) * item_stride + 20 if state.available_contracts else 34)
            + (len(state.active_contracts) * (lo.shop_card_h - 7) + 44 if state.active_contracts else 0)
        )
    else:
        total_items_h = len(items) * item_stride
    reroll_h      = lo.reroll_h + PAD
    view_h        = panel.bottom - y - (reroll_h if state.current_tab != "contracts" else 0)
    view_rect     = pygame.Rect(x, y, w - _SBAR_W, view_h)
    sbar_rect     = pygame.Rect(x + w - _SBAR_W, y, _SBAR_W, view_h)

    max_scroll = max(0, total_items_h - view_h)
    ctx._shop_scroll = max(0, min(max_scroll, ctx._shop_scroll))
    scroll = ctx._shop_scroll

    old_clip = ctx.screen.get_clip()
    ctx.screen.set_clip(view_rect)

    if state.current_tab == "contracts":
        _draw_contracts_section(ctx, x, y, w, view_h, scroll, lo, state)
    elif not items:
        empty = ctx._f("small").render("POOL EXHAUSTED - REROLL TO CONTINUE", True, C_GREEN_DIM)
        ctx.screen.blit(empty, (x + 10, y + 20))
    else:
        iy = y - scroll
        for item in items:
            card_rect = pygame.Rect(x, iy, w - _SBAR_W - 2, lo.shop_card_h)
            _draw_shop_card(ctx, card_rect, item, state.current_tab, state)
            iy += item_stride

    ctx.screen.set_clip(old_clip)

    new_scroll = draw_scrollbar(
        ctx, sbar_rect, total_items_h, view_h, scroll,
        lambda s: setattr(ctx, '_shop_scroll', max(0, s)),
    )
    if new_scroll != scroll:
        ctx._shop_scroll = new_scroll

    # --- Reroll button (hidden on contracts tab) ---
    if state.current_tab != "contracts":
        rr_rect = pygame.Rect(x, panel.bottom - lo.reroll_h - PAD // 2, w, lo.reroll_h)

        def _reroll():
            r = state.reroll_shop()
            ctx._toast(r["message"], r["level"])
            ctx._shop_scroll = 0
            if ctx.audio: ctx.audio.play("sfx_reroll")

        can_reroll = state.budget >= state.reroll_cost
        rr_label   = f"* REROLL (${state.reroll_cost})" if can_reroll else f"NEED ${state.reroll_cost} TO REROLL"
        rr_border  = C_AMBER if can_reroll else C_RED_DIM
        rr_text    = C_AMBER if can_reroll else C_GREY_MID
        draw_button(ctx, rr_rect, rr_label, _reroll,
                    border_color=rr_border, text_color=rr_text)

