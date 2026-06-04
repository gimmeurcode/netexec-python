"""
playing_shop.py — NETEXEC
=========================
Right panel (Acquisition Terminal): shop cards, tabs, reroll button.

Public entry point
------------------
  _draw_right_panel(ctx, state)
"""

import pygame

# Shop rendering constants — MAX_ACTIVE_UPGRADES used in upgrade slot display.
from engine.constants import (
    PAD,
    C_BG, C_PANEL_BORDER, C_BORDER, C_BORDER_DIM,
    C_AMBER, C_AMBER_DIM, C_AMBER_GLOW,
    C_GREEN_BRIGHT, C_GREEN_MID, C_GREEN_DIM, C_GREEN_PANEL,
    C_BLUE, C_CYAN, C_RED, C_RED_GLOW, C_RED_DIM, C_WHITE,
    C_GREY_LIGHT, C_GREY_MID, C_GREY_DARK,
    C_HOVER_PANEL, C_SELECTED, C_VIEWS_ACCENT,
    C_NET_POS, C_NET_NEG, C_NET_NEUTRAL, C_INCOME_ACCENT, MAX_ACTIVE_UPGRADES, TIME_SLOTS,
)
from ..theme import (
    C_TINT_GREEN_VIVID, C_TINT_GREEN_FILL, C_TINT_GREEN_TAB,
    C_TINT_GREEN_HOVER, C_TINT_GREEN_PILL, C_TINT_SHOW_PILL,
    C_TINT_TEAL_BADGE, C_TINT_RED_BADGE, C_TINT_RED_DARK, C_TINT_RED_PILL,
    C_TINT_SHADOW,
    TAB_COLORS,
)
from content.ads import net_cost as _ad_net_cost
from ..assets import (
    draw_genre_icon, draw_star_icon, draw_ad_icon,
    draw_upgrade_icon, draw_event_icon, draw_genre_badge,
    draw_panel_box, draw_show_thumb,
)
from ..screen_enum import GameScreen
from ..widgets import draw_button, draw_scrollbar, draw_text_wrapped, draw_row, draw_kv, line_step


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
        next_start = (start_tab + n_fit) % len(tab_defs)
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


def _fmt_card_effect(eff: dict) -> str:
    """Format an effect dict as a concise human-readable string for shop cards."""
    parts = []
    if eff.get("v_flat"):              parts.append(f"+{eff['v_flat']} views")
    if eff.get("v_mult", 1.0) != 1.0: parts.append(f"{eff['v_mult']:.2f}x mult")
    if eff.get("income"):              parts.append(f"+${eff['income']}/s")
    if eff.get("upkeep"):              parts.append(f"{eff['upkeep']:+d} upkeep")
    return "  -  ".join(parts) if parts else "--"


# --- SHOP CARD ---

def _draw_shop_card(ctx, rect, item, category, state):
    """Draw a single shop item card."""
    cost     = item.get("cost", 0)
    can_buy  = state.budget >= cost
    selected = (state.selected_item and
                state.selected_item.get("uid") == item.get("uid"))
    hovered  = rect.collidepoint(ctx._mouse_pos)

    if not can_buy:
        bg  = C_TINT_RED_DARK
        bdr = C_RED_DIM
    elif selected:
        bg  = C_TINT_GREEN_FILL
        bdr = C_SELECTED
    elif hovered:
        bg  = C_HOVER_PANEL
        bdr = C_BORDER
    else:
        bg  = C_GREEN_PANEL
        bdr = C_BORDER_DIM

    draw_rect = pygame.Rect(rect.x, rect.y - (1 if hovered and can_buy else 0),
                            rect.w, rect.h)
    if hovered and can_buy:
        shadow = pygame.Rect(rect.x + 2, rect.bottom, rect.w - 4, 2)
        pygame.draw.rect(ctx.screen, C_TINT_SHADOW, shadow, border_radius=2)

    pygame.draw.rect(ctx.screen, bg,  draw_rect, border_radius=4)
    pygame.draw.rect(ctx.screen, bdr, draw_rect, 1 if not selected else 2,
                     border_radius=4)

    if not can_buy:
        dim = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 100))
        ctx.screen.blit(dim, rect.topleft)

    cat_colors = {
        "shows":    C_GREEN_BRIGHT,
        "stars":    C_AMBER,
        "ads":      C_GREEN_MID,
        "upgrades": C_CYAN,
        "events":   C_AMBER,
    }
    stripe_col = cat_colors.get(category, C_BORDER)
    pygame.draw.rect(ctx.screen, stripe_col,
                     pygame.Rect(rect.x, rect.y + 6, 3, rect.h - 12),
                     border_radius=2)

    # SHOWS lead with a broadcast thumbnail (channel preview); other card types
    # keep a small category icon. ``content_x`` is where the text column starts.
    if category == "shows":
        th_h = min(54, rect.h - 14)
        th_w = min(int(th_h * 1.5), rect.w // 3)
        thumb_rect = pygame.Rect(rect.x + 8, rect.y + 8, th_w, th_h)
        draw_show_thumb(ctx.screen, thumb_rect, item.get("genre", ""), ctx._tick_ms)
        content_x = thumb_rect.right + 10
    else:
        ICON_SZ   = 24
        icon_rect = pygame.Rect(rect.x + 6, rect.y + 6, ICON_SZ, ICON_SZ)
        if category == "stars":
            draw_star_icon(ctx.screen, icon_rect, C_AMBER, filled=True)
        elif category == "ads":
            draw_ad_icon(ctx.screen, icon_rect, C_GREEN_MID)
        elif category == "upgrades":
            draw_upgrade_icon(ctx.screen, icon_rect, C_CYAN)
        elif category == "events":
            draw_event_icon(ctx.screen, icon_rect, C_AMBER)
        content_x = rect.x + ICON_SZ + 12

    is_ad     = (category == "ads")
    PILL_W, PILL_H = 136, 22
    pill_rect = pygame.Rect(rect.right - PILL_W - 6, rect.y + 6, PILL_W, PILL_H)

    if is_ad:
        _uf = item.get("upfront_cash", 0)
        _nc = _ad_net_cost(item, state)
        # Positive _nc = you pay; negative = they pay you
        net_positive = _nc <= 0   # you gain money on sign
        if not can_buy:
            cost_col = C_RED
            pill_bg  = C_RED_DIM
        elif net_positive:
            cost_col = C_GREEN_BRIGHT
            pill_bg  = C_TINT_GREEN_PILL
        else:
            cost_col = C_AMBER
            pill_bg  = C_TINT_SHOW_PILL
        pygame.draw.rect(ctx.screen, pill_bg,  pill_rect, border_radius=4)
        pygame.draw.rect(ctx.screen, cost_col, pill_rect, 1, border_radius=4)
        net_sign = "+" if net_positive else "-"
        net_label = f"SIGN  {net_sign}${abs(_nc):.0f}"
        p_surf = ctx._f("small").render(net_label, True, cost_col)
        ctx.screen.blit(p_surf, p_surf.get_rect(center=pill_rect.center))
        # The verbose "upfront - buy = net" breakdown lives in the tooltip; a
        # compact net is shown right-aligned on the econ row below (see ads body)
        # so it can never collide with the left-aligned payout line.
    else:
        cost_col = C_RED if not can_buy else C_AMBER
        pill_bg  = C_RED_DIM if not can_buy else C_TINT_SHOW_PILL
        pygame.draw.rect(ctx.screen, pill_bg,  pill_rect, border_radius=4)
        pygame.draw.rect(ctx.screen, cost_col, pill_rect, 1, border_radius=4)
        btn_label = "EVENT" if category == "events" else "BUY"
        p_surf = ctx._f("small").render(f"{btn_label}  -${cost}", True, cost_col)
        ctx.screen.blit(p_surf, p_surf.get_rect(center=pill_rect.center))

    if category == "events":
        next_s = ctx._f("micro").render("NEXT SEASON", True, C_AMBER_DIM)
        ctx.screen.blit(next_s, (pill_rect.right - next_s.get_width(), pill_rect.bottom + 2))

    def _buy(i=item, c=category):
        result = state.attempt_purchase(i, c)
        if result.get("ok"):
            ctx._toast(result.get("message", ""), result.get("level", "info"))
            if result.get("action") == "wildcard":
                if c == "shows":
                    ctx._wc_name  = ""
                    ctx._wc_genre = None
                    ctx._wc_slots = []
                    ctx.set_screen(GameScreen.WILDCARD_SHOW)
                else:
                    ctx._wc_name  = ""
                    ctx._wc_genre = None
                    ctx.set_screen(GameScreen.WILDCARD_AD)
            elif result.get("action") == "placed":
                if ctx.audio: ctx.audio.play("sfx_buy")
        else:
            ctx._toast(result.get("message", "ERROR"), "error")
            if ctx.audio: ctx.audio.play("sfx_error")

    ctx._add_click(pill_rect, _buy)
    ctx._add_click(rect, _buy)

    tx   = content_x
    ty   = rect.y + 6
    f_mi = ctx._f("micro")
    f_bd = ctx._f("bold")
    f_sm = ctx._f("small")
    lh   = f_mi.get_linesize() + 1

    nc        = C_CYAN if item.get("is_wildcard") else (C_SELECTED if selected else C_WHITE)
    name_str  = item.get("name", "???")
    max_name_px = pill_rect.left - tx - 8
    name_surf = f_bd.render(name_str, True, nc)
    if name_surf.get_width() > max_name_px:
        while name_str and f_bd.render(name_str + "...", True, nc).get_width() > max_name_px:
            name_str = name_str[:-1]
        name_surf = f_bd.render(name_str + "...", True, nc)
    ctx.screen.blit(name_surf, (tx, ty + 2))
    ty += 20

    if category == "shows":
        upk     = item.get("upkeep", 0)
        bv      = item.get("base_views", 0)
        star_s  = item.get("star_slots", item.get("slots", {}).get("star", 0))
        ad_s    = item.get("ad_slots",   item.get("slots", {}).get("ad",  0))
        sz      = item.get("size", 1)
        rec     = item.get("rec_slots") or []
        slot_lbs = [TIME_SLOTS[s]["label"] for s in rec if 0 <= s < len(TIME_SLOTS)]
        rec_str  = "REC: " + (", ".join(slot_lbs) if slot_lbs else "Any")

        badge_r = draw_genre_badge(ctx.screen, item.get("genre") or "", tx, ty, f_mi)
        if sz == 2:
            sz_s = f_mi.render("2-SLOT", True, C_CYAN)
            ctx.screen.blit(sz_s, (badge_r.right + 6, ty + 1))
            rec_x = badge_r.right + sz_s.get_width() + 10
        else:
            rec_x = badge_r.right + 6
        rec_surf = f_mi.render(rec_str, True, C_GREEN_MID)
        ctx.screen.blit(rec_surf, (rec_x, ty + 1))
        ty += lh + 1

        views_surf = f_mi.render(f"VIEWS: {bv:,}/season", True, C_VIEWS_ACCENT)
        ctx.screen.blit(views_surf, (tx, ty))
        ty += lh

        upk_col   = C_RED_GLOW if upk else C_GREY_MID
        slots_str = f"UPKEEP: -{upk}/s" if upk else "UPKEEP: Free"
        upk_surf  = f_mi.render(slots_str, True, upk_col)
        ctx.screen.blit(upk_surf, (tx, ty))
        slots_info = f_mi.render(f"  STARS:{star_s}  ADS:{ad_s}", True, C_GREY_LIGHT)
        _slots_x = tx + upk_surf.get_width()
        if _slots_x + slots_info.get_width() <= pill_rect.left - 4:
            ctx.screen.blit(slots_info, (_slots_x, ty))
        ty += lh

        if ty + lh <= rect.bottom - 2:
            if upk:
                net_str = f"NET: -{upk}/s upkeep  (+ ad income when ads attached)"
                net_col = C_NET_NEG
            else:
                net_str = "NET: $0 upkeep - attach ads for income"
                net_col = C_NET_NEUTRAL
            net_surf = f_mi.render(net_str[:72], True, net_col)
            ctx.screen.blit(net_surf, (tx, ty))
            ty += lh

        desc = item.get("desc", "")
        if desc and ty + lh <= rect.bottom - 3:
            desc_str  = desc[:75] + ("..." if len(desc) > 75 else "")
            desc_surf = f_mi.render(desc_str, True, C_GREY_MID)
            ctx.screen.blit(desc_surf, (tx, ty))

    elif category == "stars":
        eff_obj  = item.get("effect",   {}) if isinstance(item.get("effect"),   dict) else {}
        fall_obj = item.get("fallback", {}) if isinstance(item.get("fallback"), dict) else {}
        eff_upk  = eff_obj.get("upkeep", 0) or fall_obj.get("upkeep", 0)

        upk_str = f"UPKEEP: -{abs(eff_upk)}/s" if eff_upk else "UPKEEP: Free"
        upk_col = C_RED_GLOW if eff_upk > 0 else C_NET_POS
        ctx.screen.blit(f_mi.render(upk_str, True, upk_col), (tx, ty))
        ty += lh

        is_always = not item.get("condition_text")
        if is_always:
            lbl_s = f_mi.render("ALWAYS: ", True, C_CYAN)
            val_s = f_mi.render(_fmt_card_effect(eff_obj)[:56], True, C_GREEN_BRIGHT)
        else:
            lbl_s = f_mi.render("ON MATCH: ", True, C_AMBER)
            val_s = f_mi.render(_fmt_card_effect(eff_obj)[:52], True, C_GREEN_BRIGHT)
        ctx.screen.blit(lbl_s, (tx, ty))
        ctx.screen.blit(val_s, (tx + lbl_s.get_width(), ty))
        ty += lh

        if not is_always:
            fb_str = _fmt_card_effect(fall_obj) if fall_obj else "--"
            fb_lbl = f_mi.render("FALLBACK: ", True, C_GREY_MID)
            fb_val = f_mi.render(fb_str[:52], True, C_GREY_LIGHT)
            ctx.screen.blit(fb_lbl, (tx, ty))
            ctx.screen.blit(fb_val, (tx + fb_lbl.get_width(), ty))
            ty += lh

        cond_obj = item.get("condition") if isinstance(item.get("condition"), dict) else {}
        ctype    = cond_obj.get("type", "always")
        if ctype == "genre":
            genres = cond_obj.get("genres", [])
            scope  = "GENRE: " + "/".join(genres[:4]) if genres else "ANY GENRE"
            ctx.screen.blit(f_mi.render(scope[:60], True, C_AMBER), (tx, ty))
        elif ctype == "slot":
            slots  = cond_obj.get("slots", [])
            lbs    = [TIME_SLOTS[s]["label"] for s in slots if 0 <= s < len(TIME_SLOTS)]
            scope  = "SLOT: " + "/".join(lbs) if lbs else "ANY SLOT"
            ctx.screen.blit(f_mi.render(scope[:60], True, C_AMBER), (tx, ty))

    elif category == "ads":
        uf       = item.get("upfront_cash", 0)
        sea      = item.get("seasonal_income", item.get("income", 0))
        eff_obj  = item.get("effect",   {}) if isinstance(item.get("effect"),   dict) else {}
        fall_obj = item.get("fallback", {}) if isinstance(item.get("fallback"), dict) else {}
        fb_sea   = fall_obj.get("income", 0)

        # Right-aligned net summary on this row; the payout text is clipped so
        # it always stops short of it (no horizontal collision).
        _nc      = _ad_net_cost(item, state)
        net_sign = "+" if _nc <= 0 else "-"
        net_surf = f_mi.render(f"= {net_sign}${abs(_nc):.0f} net", True,
                               C_GREEN_MID if can_buy else C_GREY_MID)
        net_x    = rect.right - net_surf.get_width() - 8
        ctx.screen.blit(net_surf, (net_x, ty))

        inc_parts = [f"+${uf} now"]
        if sea:                         inc_parts.append(f"+${sea}/s on match")
        if fb_sea and fb_sea != sea:    inc_parts.append(f"+${fb_sea}/s otherwise")
        inc_str = "  -  ".join(inc_parts)
        while inc_str and f_mi.size(inc_str)[0] > net_x - tx - 8:
            inc_str = inc_str[:-1]
        ctx.screen.blit(f_mi.render(inc_str, True, C_NET_POS), (tx, ty))
        ty += lh

        v_flat = eff_obj.get("v_flat", 0)
        v_mult = eff_obj.get("v_mult", 1.0)
        if v_flat or v_mult != 1.0:
            vp = []
            if v_flat:       vp.append(f"+{v_flat} views")
            if v_mult != 1.0: vp.append(f"{v_mult:.2f}x mult")
            ctx.screen.blit(
                f_mi.render("VIEW BONUS: " + ", ".join(vp), True, C_VIEWS_ACCENT), (tx, ty))
            ty += lh

        cond_text = item.get("condition_text", "") or "Always active"
        is_always = not item.get("condition_text")
        cond_col  = C_CYAN if is_always else C_AMBER
        cond_lbl  = f_mi.render("CONDITION: ", True, C_GREY_MID)
        cond_val  = f_mi.render(cond_text[:50], True, cond_col)
        ctx.screen.blit(cond_lbl, (tx, ty))
        ctx.screen.blit(cond_val, (tx + cond_lbl.get_width(), ty))

    elif category == "upgrades":
        upk        = item.get("upkeep", 0)
        desc       = item.get("desc", "")
        active_cnt = len(state.active_perks)

        upk_str = f"UPKEEP: -{upk}/season" if upk else "UPKEEP: FREE"
        upk_col = C_RED_GLOW if upk else C_NET_POS
        ctx.screen.blit(f_mi.render(upk_str, True, upk_col), (tx, ty))
        ty += lh

        eff_lbl = f_mi.render("EFFECT: ", True, C_GREY_MID)
        ctx.screen.blit(eff_lbl, (tx, ty))
        eff_x          = tx + eff_lbl.get_width()
        has_line2      = len(desc) > 68
        line2_will_fit = has_line2 and (ty + lh * 2 <= rect.bottom - 16)
        if line2_will_fit:
            ctx.screen.blit(f_mi.render(desc[:68], True, C_GREY_LIGHT), (eff_x, ty))
            ty += lh
            line2 = desc[68:136] + ("..." if len(desc) > 136 else "")
            ctx.screen.blit(f_mi.render(line2, True, C_GREY_LIGHT), (tx, ty))
            ty += lh
        else:
            line1 = desc[:68] + ("..." if has_line2 else "")
            ctx.screen.blit(f_mi.render(line1, True, C_GREY_LIGHT), (eff_x, ty))
            ty += lh

        slots_str  = f"ACTIVE UPGRADES: {active_cnt}/{MAX_ACTIVE_UPGRADES}"
        slots_surf = f_mi.render(slots_str, True, C_CYAN)
        ctx.screen.blit(slots_surf, (tx, ty))
        bar_x  = tx + slots_surf.get_width() + 6
        bar_y  = ty + (lh - 6) // 2
        bar_w  = 70
        pygame.draw.rect(ctx.screen, C_GREY_DARK,
                         pygame.Rect(bar_x, bar_y, bar_w, 6), border_radius=2)
        fill_w = int(bar_w * active_cnt / MAX_ACTIVE_UPGRADES) if MAX_ACTIVE_UPGRADES else 0
        if fill_w > 0:
            fill_col = C_RED if active_cnt >= MAX_ACTIVE_UPGRADES else C_CYAN
            pygame.draw.rect(ctx.screen, fill_col,
                             pygame.Rect(bar_x, bar_y, fill_w, 6), border_radius=2)

    elif category == "events":
        ep = item.get("effect_params", {})
        if "views" in ep:
            eff_desc = f"Instant +{ep['views']} views added to season total"
        elif "amount" in ep:
            eff_desc = f"Instant +${ep['amount']} added to budget"
        else:
            eff_desc = item.get("desc", "One-time effect")

        ctx.screen.blit(
            f_mi.render("ONE-TIME - CONSUMED ON PURCHASE", True, C_AMBER), (tx, ty)
        )
        ty += lh

        ctx.screen.blit(f_mi.render("EFFECT:", True, C_GREY_MID), (tx, ty))
        ty += lh

        avail_w = rect.right - tx - 8
        draw_text_wrapped(ctx.screen, eff_desc,
                          pygame.Rect(tx, ty, avail_w, rect.bottom - ty - lh - 4),
                          f_mi, C_NET_POS)
        ctx.screen.blit(f_mi.render("Cannot be undone.", True, C_GREY_MID),
                        (tx, rect.bottom - lh - 3))

    if not can_buy and hovered:
        ov_surf = f_sm.render("INSUFFICIENT FUNDS", True, C_RED)
        ox = rect.centerx - ov_surf.get_width() // 2
        oy = rect.centery - ov_surf.get_height() // 2
        bg_r = pygame.Rect(ox - 6, oy - 3, ov_surf.get_width() + 12,
                           ov_surf.get_height() + 6)
        pygame.draw.rect(ctx.screen, C_TINT_RED_PILL, bg_r, border_radius=3)
        pygame.draw.rect(ctx.screen, C_RED_DIM, bg_r, 1, border_radius=3)
        ctx.screen.blit(ov_surf, (ox, oy))

    # --- Tooltips ---
    if category == "shows":
        _upk  = item.get("upkeep", 0)
        _bv   = item.get("base_views", 0)
        _ss   = item.get("star_slots", item.get("slots", {}).get("star", 0))
        _ads  = item.get("ad_slots",   item.get("slots", {}).get("ad",  0))
        _sz   = item.get("size", 1)
        _rec  = item.get("rec_slots") or []
        _rlab = [TIME_SLOTS[s]["label"] for s in _rec if 0 <= s < len(TIME_SLOTS)]
        _rstr = ", ".join(_rlab) if _rlab else "Any slot"
        ctx._add_tooltip(rect, {
            "type":     "show",
            "title":    item.get("name", ""),
            "subtitle": f"{item.get('genre','')}  -  {'2-Slot' if _sz == 2 else '1-Slot'}",
            "sections": [
                [
                    {"kind": "kv", "key": "BASE VIEWS",
                     "val": f"{_bv:,} /season",   "val_col": C_VIEWS_ACCENT},
                    {"kind": "kv", "key": "BUY COST",
                     "val": f"${cost}",            "val_col": C_AMBER},
                    {"kind": "kv", "key": "UPKEEP",
                     "val": f"${_upk} /season",   "val_col": C_AMBER_DIM},
                ],
                [
                    {"kind": "kv", "key": "STAR SLOTS",
                     "val": str(_ss),              "val_col": C_AMBER},
                    {"kind": "kv", "key": "AD SLOTS",
                     "val": str(_ads),             "val_col": C_GREEN_MID},
                    {"kind": "kv", "key": "BEST SLOTS",
                     "val": _rstr,                 "val_col": C_GREEN_BRIGHT},
                ],
                [{"kind": "text", "text": item.get("desc", ""), "col": C_GREY_LIGHT}],
            ],
        })

    elif category == "stars":
        _eff_upk = item.get("effect",   {}).get("upkeep", 0)
        _fal_upk = item.get("fallback", {}).get("upkeep", 0)
        _upk = _eff_upk if _eff_upk else _fal_upk
        ctx._add_tooltip(rect, {
            "type":  "star",
            "title": f"STAR: {item.get('name', '')}",
            "sections": [
                [
                    {"kind": "kv", "key": "BUY COST",
                     "val": f"${cost}", "val_col": C_AMBER},
                    {"kind": "kv", "key": "UPKEEP",
                     "val": f"${_upk} /season" if _upk else "Free",
                     "val_col": C_AMBER_DIM if _upk else C_NET_POS},
                ],
                [
                    {"kind": "kv", "key": "CONDITION",
                     "val": item.get("condition_text", "") or "Always active",
                     "val_col": C_AMBER},
                    {"kind": "text", "text": item.get("desc", ""), "col": C_GREY_LIGHT},
                ],
            ],
        })

    elif category == "ads":
        _uf  = item.get("upfront_cash", 0)
        _sea = item.get("seasonal_income", item.get("income", 0))
        _net = _ad_net_cost(item, state)
        ctx._add_tooltip(rect, {
            "type":  "ad",
            "title": f"AD: {item.get('name', '')}",
            "sections": [
                [
                    {"kind": "kv", "key": "BUY COST",
                     "val": f"${cost}",         "val_col": C_AMBER},
                    {"kind": "kv", "key": "UPFRONT BONUS",
                     "val": f"+${_uf}",          "val_col": C_NET_POS},
                    {"kind": "kv", "key": "NET OUT-OF-POCKET",
                     "val": f"${_net:.0f}",      "val_col": C_AMBER_DIM},
                    {"kind": "kv", "key": "SEASONAL EARN",
                     "val": f"+${_sea} /season", "val_col": C_INCOME_ACCENT},
                ],
                [
                    {"kind": "kv", "key": "CONDITION",
                     "val": item.get("condition_text", "") or "Always",
                     "val_col": C_AMBER},
                    {"kind": "text", "text": item.get("desc", ""), "col": C_GREY_LIGHT},
                ],
            ],
        })

    elif category == "upgrades":
        _upk = item.get("upkeep", 0)
        ctx._add_tooltip(rect, {
            "type":  "upgrade",
            "title": f"UPG: {item.get('name', '')}",
            "sections": [
                [
                    {"kind": "kv", "key": "COST",
                     "val": f"${cost} one-time",    "val_col": C_AMBER},
                    {"kind": "kv", "key": "UPKEEP",
                     "val": f"${_upk} /season" if _upk else "Free",
                     "val_col": C_AMBER_DIM if _upk else C_NET_POS},
                    {"kind": "kv", "key": "MAX ACTIVE",
                     "val": str(MAX_ACTIVE_UPGRADES), "val_col": C_GREY_LIGHT},
                ],
                [{"kind": "text", "text": item.get("desc", ""), "col": C_GREY_LIGHT}],
            ],
        })

    elif category == "events":
        _ep = item.get("effect_params", {})
        if "views" in _ep and "budget" in _ep:
            _eff = f"+{_ep['views']} views AND +${_ep['budget']} budget — fires at start of next season"
        elif "views" in _ep:
            _eff = f"+{_ep['views']} lifetime views — fires at start of next season"
        elif "amount" in _ep:
            _eff = f"+${_ep['amount']} budget — fires at start of next season"
        elif "budget_bonus" in _ep:
            _eff = f"-${_ep.get('amount',0)} upkeep per show AND +${_ep['budget_bonus']} budget — fires next season"
        else:
            _eff = "One-time effect — queued, fires at the START of next season"
        ctx._add_tooltip(rect, {
            "type":  "event",
            "title": f"EVT: {item.get('name', '')}",
            "sections": [
                [
                    {"kind": "kv", "key": "COST",
                     "val": f"${cost} (consumed on buy)",    "val_col": C_AMBER},
                    {"kind": "kv", "key": "TIMING",
                     "val": "Queued — fires NEXT SEASON start", "val_col": C_AMBER},
                ],
                [
                    {"kind": "kv", "key": "EFFECT",
                     "val": _eff,                             "val_col": C_NET_POS},
                    {"kind": "text", "text": item.get("desc", ""), "col": C_GREY_LIGHT},
                ],
            ],
        })


# --- CONTRACTS SECTION ---

def _draw_contracts_section(ctx, x, y, w, view_h, scroll, lo, state):
    """Draw the contracts tab: available offers + active contracts."""
    from engine.requirements import describe as describe_req

    f_hd = ctx._f("small")
    f_mi = ctx._f("micro")
    lh   = f_mi.get_linesize() + 1
    card_h = lo.shop_card_h

    iy = y - scroll

    # --- Available contracts ---
    if state.available_contracts:
        hdr = f_hd.render("AVAILABLE CONTRACTS", True, C_VIEWS_ACCENT)
        ctx.screen.blit(hdr, (x + 6, iy + 4))
        iy += 20
        for ev in state.available_contracts:
            card_rect = pygame.Rect(x, iy, w - _SBAR_W - 2, card_h)
            _draw_contract_card(ctx, card_rect, ev, state, available=True)
            iy += card_h + 3
    else:
        no_s = f_mi.render("No contracts available - air a season to receive offers.", True, C_GREEN_DIM)
        ctx.screen.blit(no_s, (x + 10, iy + 10))
        iy += 24

    # --- Active contracts ---
    if state.active_contracts:
        iy += 6
        pygame.draw.line(ctx.screen, C_BORDER_DIM, (x + 4, iy), (x + w - _SBAR_W - 6, iy))
        iy += 6
        hdr2 = f_hd.render("ACTIVE CONTRACTS", True, C_CYAN)
        ctx.screen.blit(hdr2, (x + 6, iy + 2))
        iy += 18
        for entry in state.active_contracts:
            ev   = entry.get("event", {})
            rem  = entry.get("remaining_seasons", 0)
            done = entry.get("fulfilled", False)
            card_rect = pygame.Rect(x, iy, w - _SBAR_W - 2, card_h - 10)
            _draw_active_contract(ctx, card_rect, ev, rem, done)
            iy += card_h - 7


def _draw_contract_card(ctx, rect, ev, state, available=True):
    """Draw a single available-contract card with an ACCEPT button."""
    from engine.requirements import describe as describe_req

    hovered  = rect.collidepoint(ctx._mouse_pos)
    bg       = C_HOVER_PANEL if hovered else C_GREEN_PANEL
    bdr      = C_VIEWS_ACCENT if hovered else C_BORDER_DIM

    pygame.draw.rect(ctx.screen, bg,  rect, border_radius=4)
    pygame.draw.rect(ctx.screen, bdr, rect, 1, border_radius=4)
    pygame.draw.rect(ctx.screen, C_VIEWS_ACCENT,
                     pygame.Rect(rect.x, rect.y + 6, 3, rect.h - 12),
                     border_radius=2)

    f_bd = ctx._f("bold")
    f_mi = ctx._f("micro")
    lh   = f_mi.get_linesize() + 1

    # Accept button pill
    PILL_W, PILL_H = 80, 22
    pill_rect = pygame.Rect(rect.right - PILL_W - 6, rect.y + 6, PILL_W, PILL_H)
    pygame.draw.rect(ctx.screen, C_TINT_GREEN_FILL, pill_rect, border_radius=4)
    pygame.draw.rect(ctx.screen, C_VIEWS_ACCENT,    pill_rect, 1, border_radius=4)
    acc_s = ctx._f("small").render("ACCEPT", True, C_VIEWS_ACCENT)
    ctx.screen.blit(acc_s, acc_s.get_rect(center=pill_rect.center))

    def _accept(eid=ev.get("id", "")):
        r = state.accept_contract(eid)
        ctx._toast(r["message"], r["level"])

    ctx._add_click(pill_rect, _accept)
    ctx._add_click(rect, _accept)

    tx = rect.x + 10
    ty = rect.y + 5

    name_str = ev.get("name", "???")
    name_max = pill_rect.left - tx - 8
    while name_str and f_bd.size(name_str)[0] > name_max:
        name_str = name_str[:-1]
    name_surf = f_bd.render(name_str, True, C_WHITE)
    ctx.screen.blit(name_surf, (tx, ty))
    ty += line_step(f_bd, 0.80)

    req_str = describe_req(ev.get("requirement", {}))
    rew     = ev.get("reward", {})
    pen     = ev.get("penalty", {})
    dur     = ev.get("duration", 3)
    rew_str = f"+${rew.get('budget_bonus', 0)}" if rew.get("budget_bonus") else "Reward on fulfil"
    pen_str = f"-${pen.get('budget_loss', 0)}"  if pen.get("budget_loss")  else "No penalty"

    ctx.screen.blit(f_mi.render(f"REQ: {req_str}", True, C_AMBER),     (tx, ty)); ty += lh
    ctx.screen.blit(f_mi.render(f"REWARD: {rew_str}  |  FAIL: {pen_str}",
                                 True, C_NET_POS), (tx, ty)); ty += lh
    ctx.screen.blit(f_mi.render(f"WINDOW: {dur} seasons",
                                 True, C_GREY_MID), (tx, ty))

    ctx._add_tooltip(rect, {
        "type":  "event",
        "title": f"CONTRACT: {ev.get('name', '')}",
        "sections": [
            [
                {"kind": "kv", "key": "REQUIREMENT", "val": req_str,  "val_col": C_AMBER},
                {"kind": "kv", "key": "REWARD",      "val": rew_str,  "val_col": C_NET_POS},
                {"kind": "kv", "key": "PENALTY",     "val": pen_str,  "val_col": C_RED},
                {"kind": "kv", "key": "WINDOW",
                 "val": f"{dur} season{'s' if dur != 1 else ''}",
                 "val_col": C_GREY_LIGHT},
            ],
            [{"kind": "text", "text": ev.get("desc", ""), "col": C_GREY_LIGHT}],
        ],
    })


def _draw_active_contract(ctx, rect, ev, remaining_seasons, fulfilled):
    """Draw a read-only active contract card showing status."""
    from engine.requirements import describe as describe_req

    done_col = C_NET_POS if fulfilled else C_AMBER
    bg       = C_TINT_GREEN_FILL if fulfilled else C_GREEN_PANEL
    bdr      = done_col

    pygame.draw.rect(ctx.screen, bg,  rect, border_radius=4)
    pygame.draw.rect(ctx.screen, bdr, rect, 1, border_radius=4)

    f_bd = ctx._f("bold")
    f_mi = ctx._f("micro")
    lh   = f_mi.get_linesize() + 1

    tx = rect.x + 10
    ty = rect.y + 4

    status_txt = "FULFILLED" if fulfilled else f"{remaining_seasons}s LEFT"
    status_col = C_NET_POS  if fulfilled else C_AMBER
    st_s = f_mi.render(status_txt, True, status_col)
    st_x = rect.right - st_s.get_width() - 8
    ctx.screen.blit(st_s, (st_x, ty + 1))

    name_str = ev.get("name", "???")
    name_max = st_x - tx - 8
    while name_str and f_bd.size(name_str)[0] > name_max:
        name_str = name_str[:-1]
    name_surf = f_bd.render(name_str, True, C_WHITE)
    ctx.screen.blit(name_surf, (tx, ty)); ty += line_step(f_bd, 0.80)

    req_str = describe_req(ev.get("requirement", {}))
    ctx.screen.blit(f_mi.render(f"REQ: {req_str}", True, C_GREY_LIGHT), (tx, ty))
