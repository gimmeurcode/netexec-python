"""
cards.py — NETEXEC
==================
Shop item card rendering for the Acquisition Terminal (right panel). Draws one
card per shop item across every category (shows / stars / ads / upgrades /
events): the BUY/SIGN pill, stats, condition lines, the insufficient-funds
overlay, and the hover tooltip. Called by ``shop.py``'s ``_draw_right_panel``
for each visible item in the scroll viewport.

Public entry points
-------------------
  _fmt_card_effect(eff) -> str
  _draw_shop_card(ctx, rect, item, category, state)
"""

import pygame

from engine.constants import (
    C_BORDER, C_BORDER_DIM,
    C_AMBER, C_AMBER_DIM,
    C_GREEN_BRIGHT, C_GREEN_MID, C_GREEN_PANEL,
    C_CYAN, C_RED, C_RED_GLOW, C_RED_DIM, C_WHITE,
    C_GREY_LIGHT, C_GREY_MID, C_GREY_DARK,
    C_HOVER_PANEL, C_SELECTED, C_VIEWS_ACCENT,
    C_NET_POS, C_NET_NEG, C_NET_NEUTRAL, C_INCOME_ACCENT,
    MAX_ACTIVE_UPGRADES, TIME_SLOTS,
)
from ...theme import (
    C_TINT_GREEN_FILL, C_TINT_GREEN_PILL, C_TINT_SHOW_PILL,
    C_TINT_RED_DARK, C_TINT_RED_PILL, C_TINT_SHADOW,
)
from content.ads import net_cost as _ad_net_cost
from ...assets import (
    draw_star_icon, draw_ad_icon, draw_upgrade_icon,
    draw_event_icon, draw_show_thumb,
)
from ...widgets import draw_text_wrapped, draw_genre_badge
from ...screen_enum import GameScreen


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
