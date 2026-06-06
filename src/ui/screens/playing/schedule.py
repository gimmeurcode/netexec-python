"""
playing/schedule.py — NETEXEC
=============================
Left panel: broadcast schedule, vault, upgrades, and seasonal events.

Public entry point
------------------
  _draw_left_panel(ctx, state)
"""

import pygame

from engine.constants import (
    PAD,
    C_BG, C_BORDER, C_BORDER_DIM,
    C_AMBER, C_AMBER_DIM,
    C_GREEN_BRIGHT, C_GREEN_MID, C_GREEN_DIM, C_GREEN_PANEL,
    C_BLUE, C_BLUE_DIM, C_CYAN, C_RED, C_RED_DIM, C_WHITE,
    C_GREY_LIGHT, C_GREY_MID,
    C_HOVER_PANEL, C_SELECTED, C_VIEWS_ACCENT,
    C_NET_POS, C_NET_NEG, C_INCOME_ACCENT,
    TIME_SLOTS, MAX_ACTIVE_UPGRADES, GENRE_COLORS, BLINK_PERIOD_MS,
)
from ...theme import (
    C_TINT_GREEN_DEEP, C_TINT_GREEN_FILL,
    C_TINT_GREEN_TILE,
    C_TINT_TEAL_BADGE,
    SLOT_COLORS,
)
from engine.network import calculate_yield
from content.shows import get_genre_registry
from ...assets import (
    draw_upgrade_icon, draw_event_icon,
    draw_signal_bars, draw_blink_dot, draw_show_thumb,
)
from ...widgets import (
    draw_button, draw_scrollbar, draw_row, line_step,
    draw_genre_badge, draw_panel_box,
)


_SBAR_W = 8   # scrollbar track width (px)
# --- LEFT PANEL ---


def _draw_left_panel(ctx, state):
    """Draw the broadcast schedule, vault, upgrades and monopoly bar."""
    lo = ctx.layout
    x  = PAD
    y0 = lo.hud_h + PAD
    panel_w = lo.left_w - PAD * 2

    panel = pygame.Rect(x, y0, panel_w, ctx._sh - y0 - PAD)
    draw_panel_box(ctx.screen, panel, title="BROADCAST SCHEDULE",
                   title_font=ctx._f("small"), bg_color=C_BG)
    title_h = 26

    # --- Compute total scrollable content height ---
    has_seasonal = bool(
        state.active_seasonal_modifiers or state.active_contracts
        or state.active_mandates or state.available_contracts
    )
    has_active_contracts = bool(state.active_contracts or state.pending_events)
    contract_bar_h = max(22, lo.seasonal_strip_h // 2) * (len(state.active_contracts) + len(getattr(state, 'pending_events', [])) + 1) if has_active_contracts else 0
    # Monopoly bar is tall enough to list all genre bonuses (7 rows + header + padding)
    _mono_lh    = ctx._f("micro").get_linesize() + 2
    mono_bar_h  = max(lo.monopoly_bar_h, _mono_lh * 9 + 6)
    total_content_h = (
        len(TIME_SLOTS) * (lo.slot_h + 3) + 4   # slots
        + 26 + lo.vault_h + 6                     # vault header + slots
        + 26 + lo.upgrade_row_h + 4               # upgrades header + row
        + mono_bar_h + 4                           # monopoly bar (dynamic)
        + (26 + contract_bar_h + 4 if has_active_contracts else 0)  # active contracts bar
        + (lo.seasonal_strip_h + 4 if has_seasonal else 0)
    )

    # --- Scrollable view region (reserves space for "PENDING" indicator) ---
    pending_reserve = 26 if state.selected_item else 0
    view_h  = panel.height - title_h - pending_reserve
    view_top = y0 + title_h
    view_rect = pygame.Rect(x + 2, view_top, panel_w - 2 - _SBAR_W, view_h)
    sbar_rect = pygame.Rect(x + panel_w - _SBAR_W, view_top, _SBAR_W, view_h)

    # Clamp and update scroll offset
    max_scroll = max(0, total_content_h - view_h)
    ctx._schedule_scroll = max(0, min(max_scroll, ctx._schedule_scroll))
    scroll = ctx._schedule_scroll

    # --- Clip to view and render content ---
    old_clip = ctx.screen.get_clip()
    ctx.screen.set_clip(view_rect)

    content_w = view_rect.width - 2
    y = view_top - scroll

    for i, slot_def in enumerate(TIME_SLOTS):
        slot_rect = pygame.Rect(x + 2, y, content_w, lo.slot_h)
        _draw_time_slot(ctx, slot_rect, i, slot_def, state)
        y += lo.slot_h + 3
    y += 4

    vx, vy = x + 4, y
    cw, ch = 16, 10
    pygame.draw.rect(ctx.screen, C_GREEN_MID, (vx, vy + 3, cw, ch), 1, border_radius=1)
    for sx in (vx + cw // 3, vx + 2 * cw // 3):
        pygame.draw.circle(ctx.screen, C_GREEN_MID, (sx, vy + 3 + ch // 2), ch // 4, 1)
    pygame.draw.line(ctx.screen, C_GREEN_MID,
                     (vx + cw // 3, vy + 3 + ch - 1),
                     (vx + 2 * cw // 3, vy + 3 + ch - 1))
    vault_label = ctx._f("bold").render("SYNDICATION VAULT", True, C_GREEN_MID)
    ctx.screen.blit(vault_label, (vx + cw + 4, vy))
    pygame.draw.line(ctx.screen, C_BORDER_DIM,
                     (vx + cw + 4 + vault_label.get_width() + 6, vy + 7),
                     (x + content_w - 6, vy + 7))
    y += line_step(ctx._f("bold"), 0.85)

    vault_w = (content_w - 8) // 2
    for vi in range(2):
        vr = pygame.Rect(x + 2 + vi * (vault_w + 4), y, vault_w, lo.vault_h)
        _draw_vault_slot(ctx, vr, vi, state)
    y += lo.vault_h + 6

    upg_label = ctx._f("small").render("ACTIVE UPGRADES", True, C_GREEN_MID)
    ctx.screen.blit(upg_label, (x + 4, y))
    pygame.draw.line(ctx.screen, C_BORDER_DIM,
                     (x + 4 + upg_label.get_width() + 6, y + 7),
                     (x + content_w - 6, y + 7))
    y += line_step(ctx._f("small"), 0.85)
    upg_row = pygame.Rect(x + 2, y, content_w, lo.upgrade_row_h)
    _draw_upgrades(ctx, upg_row, state)
    y += lo.upgrade_row_h + 4

    mono_rect = pygame.Rect(x + 2, y, content_w, mono_bar_h)
    _draw_monopoly_bar(ctx, mono_rect, state)
    y += mono_bar_h + 4

    if has_active_contracts:
        con_label = ctx._f("small").render("CONTRACTS & QUEUED EVENTS", True, C_VIEWS_ACCENT)
        ctx.screen.blit(con_label, (x + 4, y))
        pygame.draw.line(ctx.screen, C_BORDER_DIM,
                         (x + 4 + con_label.get_width() + 6, y + 7),
                         (x + content_w - 6, y + 7))
        y += line_step(ctx._f("small"), 0.85)
        con_rect = pygame.Rect(x + 2, y, content_w, contract_bar_h)
        _draw_active_contracts_bar(ctx, con_rect, state)
        y += contract_bar_h + 4

    if has_seasonal:
        seas_rect = pygame.Rect(x + 2, y, content_w, lo.seasonal_strip_h)
        _draw_seasonal_strip(ctx, seas_rect, state)

    ctx.screen.set_clip(old_clip)

    # --- Scrollbar ---
    new_scroll = draw_scrollbar(
        ctx, sbar_rect, total_content_h, view_h, scroll,
        lambda s: setattr(ctx, '_schedule_scroll', max(0, s)),
    )
    if new_scroll != scroll:
        ctx._schedule_scroll = new_scroll

    # --- Pending item indicator (always visible at panel bottom) ---
    if state.selected_item:
        ind_y = panel.bottom - pending_reserve
        sel_info = f"PENDING: {state.selected_item.get('name','???')[:20]}"
        si_txt = ctx._f("small").render(sel_info, True, C_SELECTED)
        ctx.screen.blit(si_txt, (x + 4, ind_y))
        cancel_rect = pygame.Rect(ctx._L - 120, ind_y - 2, 110, 20)
        draw_button(ctx, cancel_rect, "CANCEL", state.clear_selection,
                    text_color=C_RED, border_color=C_RED_DIM)


# --- TIME SLOT CARD ---

def _draw_time_slot(ctx, rect, idx, slot_def, state):
    """Draw one time-slot card styled as a hardware channel input selector."""
    # High-contrast slot identity colors from theme.SLOT_COLORS (R3)
    _sc          = SLOT_COLORS[idx % len(SLOT_COLORS)]
    slot_accent  = _sc["accent"]
    slot_bg_base = _sc["bg"]

    show    = state.lineup[idx] if idx < len(state.lineup) else None
    is_ext  = show and show.get("is_extension")
    hovered = rect.collidepoint(ctx._mouse_pos) and bool(show) and not is_ext

    if hovered:
        bg = C_HOVER_PANEL
    elif state.selected_item and not is_ext:
        bg = C_TINT_GREEN_DEEP
    else:
        bg = slot_bg_base
    pygame.draw.rect(ctx.screen, bg, rect, border_radius=3)

    if hovered:
        border_col = C_GREEN_BRIGHT
    elif show and not is_ext:
        border_col = slot_accent
    elif state.selected_item:
        border_col = C_GREEN_MID
    else:
        border_col = C_BORDER_DIM
    pygame.draw.rect(ctx.screen, border_col, rect, 1, border_radius=3)

    pygame.draw.rect(ctx.screen, slot_accent,
                     pygame.Rect(rect.x + 1, rect.y + 1, 5, rect.height - 2),
                     border_radius=2)

    HDR_H = 24
    tx    = rect.x + 9

    name_surf = ctx._f("bold").render(slot_def["label"].upper(), True, C_WHITE)
    ctx.screen.blit(name_surf, (tx, rect.y + 4))

    # Signal bars drawn FIRST so the ability label plate renders on top
    draw_signal_bars(ctx.screen,
                     rect.right - 10, rect.y + 4,
                     filled=1 if (show and not is_ext) else 0,
                     total=1)

    ability_surf = ctx._f("micro").render(slot_def["ability"], True, C_CYAN)
    _ab_x   = rect.right - ability_surf.get_width() - 18
    _ab_pad = 3
    _ab_bg  = pygame.Rect(_ab_x - _ab_pad, rect.y + 3,
                           ability_surf.get_width() + _ab_pad * 2,
                           ability_surf.get_height() + 4)
    pygame.draw.rect(ctx.screen, C_BG, _ab_bg)
    ctx.screen.blit(ability_surf, (_ab_x, rect.y + 5))

    pygame.draw.line(ctx.screen, slot_accent,
                     (rect.x + 7, rect.y + HDR_H),
                     (rect.right - 4, rect.y + HDR_H))

    slot_ability_descs = {
        "MORNING":    "Ad income on this show is multiplied by 1.20x. Great for ad-heavy reality builds.",
        "AFTERNOON":  "Base views for this show is multiplied by 1.10x before all other calculations.",
        "PRIME TIME": "Star view multiplier bonuses are amplified by 1.5x. A 1.5x star becomes 1.75x.",
        "LATE NIGHT": "This show's upkeep cost is halved. Ideal for expensive shows with high maintenance.",
    }
    ctx._add_tooltip(pygame.Rect(rect.x, rect.y, rect.width, HDR_H), {
        "type":   "generic",
        "accent": slot_accent,
        "title":  f"{slot_def['label']} - {slot_def['ability']}",
        "sections": [[
            {"kind": "text",
             "text": slot_ability_descs.get(slot_def["id"], ""),
             "col":  C_GREY_LIGHT},
        ]],
    })

    content_y = rect.y + HDR_H + 1

    if is_ext:
        ext_surf = ctx._f("small").render("^ 2-SLOT EXTENSION", True, C_GREEN_DIM)
        ctx.screen.blit(ext_surf, (tx, content_y + 4))
    elif show is None:
        _draw_empty_slot_content(ctx, rect, content_y, tx, slot_def, state, idx)
    else:
        _draw_show_in_slot(ctx, rect, content_y, tx, show, idx, state, hovered)



def _draw_empty_slot_content(ctx, rect, content_y, tx, slot_def, state, idx):
    """Draw instruction text for an unscheduled slot."""
    inner = pygame.Rect(tx, content_y + 3,
                        rect.right - tx - 6, rect.bottom - content_y - 8)

    cy = inner.centery
    if state.selected_item and state.selected_item.get("shop_type") == "shows":
        hint_txt = "+ CLICK TO PLACE HERE"
        hint_col = C_GREEN_BRIGHT
        ctx._add_click(rect, lambda i=idx: ctx._place_on_slot("lineup", i, state))
    else:
        hint_txt = "CLICK SHOP > BUY SHOW"
        hint_col = C_GREEN_DIM

    hint_surf = ctx._f("small").render(hint_txt, True, hint_col)
    ctx.screen.blit(hint_surf,
                    (rect.centerx - hint_surf.get_width() // 2, cy - 2))


def _draw_show_in_slot(ctx, rect, content_y, tx, show, idx, state, hovered=False):
    """Render show name, financials, attachments, action buttons inside a slot card."""
    rec    = show.get("rec_slots") or []
    in_rec = not rec or idx in rec
    # Pass monopoly bonus and seasonal modifiers so projected values are accurate
    mono_bonus  = state.get_lineup_summary().get("bonus") if state.get_lineup_summary().get("is_monopoly") else None
    s_mods      = state.aggregate_seasonal_mods() if state.seasonal_events_enabled else None
    yld    = calculate_yield(show, start_idx=idx,
                             active_perks=state.active_perks, season=state.season,
                             monopoly_bonus=mono_bonus, seasonal_mods=s_mods)

    ty    = content_y + 2
    btn_y = rect.bottom - 18
    # Clip content area so no text row bleeds into the SELL/VAULT button strip
    _sc_prev = ctx.screen.get_clip()
    ctx.screen.set_clip(_sc_prev.clip(pygame.Rect(rect.x, rect.y, rect.width, rect.height - 18)))

    f_mi   = ctx._f("micro")
    step_b = line_step(ctx._f("bold"), 0.80)   # ink-safe step for the name row
    step_m = line_step(f_mi, 0.80)             # ink-safe step for micro rows
    net_val = yld["i"]
    net_col = C_NET_POS if net_val >= 0 else C_NET_NEG

    # Broadcast thumbnail (channel preview) in the top-right of the slot.
    th_h = min(38, max(22, rect.height - 60))
    th_w = min(int(th_h * 1.6), rect.width // 4)
    icon_rect = pygame.Rect(rect.right - th_w - 6, ty, th_w, th_h)
    draw_show_thumb(ctx.screen, icon_rect, show.get("genre", ""), ctx._tick_ms)

    age = show.get("age", 1)
    age_col = C_AMBER if age == 2 else (C_RED if age >= 6 else C_GREEN_DIM)

    # Row 1 — show name (left), AGE dot + label right-aligned before the thumb.
    name_col  = (C_SELECTED
                 if (state.selected_item and
                     state.selected_item.get("shop_type") in ("stars", "ads"))
                 else C_WHITE)
    age_surf  = f_mi.render(f"AGE {age}", True, C_GREY_LIGHT)
    age_x     = icon_rect.x - age_surf.get_width() - 8
    pygame.draw.circle(ctx.screen, age_col, (age_x - 7, ty + 8), 3)
    ctx.screen.blit(age_surf, (age_x, ty + 2))
    name_max  = max(40, age_x - 12 - tx)
    nm = show.get("name", "???")
    while nm and ctx._f("bold").size(nm)[0] > name_max:
        nm = nm[:-1]
    name_surf = ctx._f("bold").render(nm, True, name_col)
    ctx.screen.blit(name_surf, (tx, ty))
    ty += step_b

    # Row 2 — genre badge, then projected views and net income on one measured
    # line (draw_row spaces each segment so nothing collides with the badge).
    vx = tx
    if show.get("genre"):
        badge_rect = draw_genre_badge(ctx.screen, show["genre"], tx, ty, f_mi)
        vx = badge_rect.right + 6
    seg = [(f"{yld['v']:,}v", C_VIEWS_ACCENT)]
    if not in_rec and rec:
        seg.append(("[!]-30%", C_RED))
    seg.append((f"${net_val:+.0f}/s", net_col))
    draw_row(ctx, seg, vx, ty + 1, f_mi, gap=8)
    ty += step_m

    # Row 3 — one-time cost and per-second upkeep on one measured line.
    draw_row(ctx, [
        (f"COST ${show.get('cost', 0)}",    C_AMBER),
        (f"UPK ${show.get('upkeep', 0)}/s", C_AMBER_DIM),
    ], tx, ty, f_mi, gap=10)
    ty += step_m

    stars    = show.get("attached", {}).get("star", [])
    star_max = show.get("star_slots", show.get("slots", {}).get("star", 0))
    ads_att  = show.get("attached", {}).get("ad", [])
    ad_max   = show.get("ad_slots",  show.get("slots", {}).get("ad", 0))

    if star_max > 0 or ad_max > 0:
        pygame.draw.line(ctx.screen, C_BORDER_DIM, (tx, ty), (rect.right - 8, ty))
        ty += 4
        _fmi = ctx._f("micro")
        _ax  = tx
        star_filled = (255, 200, 50)   # bright gold - very visible
        star_empty  = (200, 150, 30)   # medium amber - still visible
        ad_filled   = (100, 255, 240)  # bright cyan - very visible
        ad_empty    = (80, 180, 200)   # medium cyan-blue - still visible
        # Star slots: filled amber star or hollow dot
        for _i in range(star_max):
            if _ax + 12 > rect.right - 8:
                break
            filled = _i < len(stars)
            col = star_filled if filled else star_empty
            pygame.draw.circle(ctx.screen, col, (_ax + 5, ty + 5), 5,
                               0 if filled else 1)
            if filled:
                _nt = _fmi.render(stars[_i].get("name", "?")[:6], True, star_filled)
                ctx.screen.blit(_nt, (_ax + 13, ty))
                _ax += 13 + _nt.get_width() + 3
            else:
                _nt = _fmi.render("o", True, star_empty)
                ctx.screen.blit(_nt, (_ax + 12, ty))
                _ax += 22
        if star_max > 0 and ad_max > 0:
            _ax += 4
        # Ad slots: filled cyan diamond or hollow outline
        for _i in range(ad_max):
            if _ax + 12 > rect.right - 8:
                break
            filled = _i < len(ads_att)
            col = ad_filled if filled else ad_empty
            # Diamond shape via rotated rect
            pts = [(_ax + 5, ty), (_ax + 10, ty + 5), (_ax + 5, ty + 10), (_ax, ty + 5)]
            pygame.draw.polygon(ctx.screen, col, pts, 0 if filled else 1)
            if filled:
                _nt = _fmi.render(ads_att[_i].get("name", "?")[:6], True, ad_filled)
                ctx.screen.blit(_nt, (_ax + 13, ty))
                _ax += 13 + _nt.get_width() + 3
            else:
                _nt = _fmi.render("o", True, ad_empty)
                ctx.screen.blit(_nt, (_ax + 12, ty))
                _ax += 22

    ctx.screen.set_clip(_sc_prev)
    bw, gap = 60, 4

    sell_rect = pygame.Rect(tx, btn_y, bw, 14)

    def _sell(i=idx):
        r = state.sell_show("lineup", i)
        ctx._toast(r["message"], r["level"])
        if ctx.audio: ctx.audio.play("sfx_click")

    draw_button(ctx, sell_rect, "SELL", _sell, text_color=C_RED, border_color=C_RED_DIM)

    if show.get("size", 1) == 1:
        vault_rect = pygame.Rect(tx + bw + gap, btn_y, bw, 14)

        def _vault(i=idx):
            r = state.move_to_vault(i)
            ctx._toast(r["message"], r["level"])
            if ctx.audio: ctx.audio.play("sfx_place")

        draw_button(ctx, vault_rect, "VAULT >", _vault, border_color=C_GREEN_MID)

    if hovered:
        hint = ctx._f("micro").render("CLICK FOR DETAILS", True, C_GREY_LIGHT)
        ctx.screen.blit(hint, (rect.right - hint.get_width() - 6, btn_y + 1))

    # Handle clicking on the show card
    if state.selected_item and state.selected_item.get("shop_type") in ("stars", "ads"):
        # When placing stars/ads, clicking places the item
        ctx._add_click(rect, lambda i=idx: ctx._place_on_slot("lineup", i, state))
    else:
        # Otherwise, clicking shows the detail modal
        def _open_detail(s=show, i=idx):
            ctx._show_detail  = {"show": s, "slot_idx": i}
            ctx._detail_scroll = 0
        ctx._add_click(rect, _open_detail)

    # Tooltip
    rec_names = [TIME_SLOTS[s]["label"] for s in rec if 0 <= s < len(TIME_SLOTS)]
    rec_str   = ", ".join(rec_names) if rec_names else "Any slot"
    ad_income = yld.get("ad_income", 0.0)
    att_stars = show.get("attached", {}).get("star", [])
    att_ads   = show.get("attached", {}).get("ad",  [])
    ad_max2   = show.get("ad_slots", show.get("slots", {}).get("ad", 0))

    tt_sections = [
        [
            {"kind": "kv", "key": "BASE VIEWS",
             "val": f"{show.get('base_views',0):,} /season", "val_col": C_VIEWS_ACCENT},
            {"kind": "kv", "key": "PROJECTED",
             "val": f"~{yld['v']:,} views this season",      "val_col": C_VIEWS_ACCENT},
            {"kind": "kv", "key": "UPKEEP",
             "val": f"${show.get('upkeep',0)} /season",      "val_col": C_AMBER_DIM},
            {"kind": "kv", "key": "AD INCOME",
             "val": f"${ad_income:.0f} /season",              "val_col": C_INCOME_ACCENT},
            {"kind": "kv", "key": "NET INCOME",
             "val": f"${net_val:+.0f} /season",
             "val_col": C_NET_POS if net_val >= 0 else C_NET_NEG},
        ],
        [
            {"kind": "kv", "key": "BEST SLOTS",
             "val": rec_str,
             "val_col": C_GREEN_BRIGHT if in_rec else C_RED},
            {"kind": "kv", "key": "AD SLOTS",  "val": str(ad_max2), "val_col": C_GREEN_MID},
            {"kind": "kv", "key": "AGE",
             "val": f"{age} seasons",
             "val_col": C_AMBER if age == 2 else (C_RED if age >= 6 else C_GREY_LIGHT)},
        ],
    ]

    if att_stars:
        star_rows = []
        for st in att_stars:
            star_rows.append({"kind": "text",
                               "text": f">> {st.get('name','?')} - {st.get('desc','')[:38]}",
                               "col": C_AMBER})
            cond = st.get("condition_text", "")
            if cond:
                star_rows.append({"kind": "text", "text": f"   - {cond}", "col": C_AMBER_DIM})
        tt_sections.append(star_rows)

    if att_ads:
        ad_rows = []
        for ad in att_ads:
            s_earn = ad.get("seasonal_income", ad.get("income", 0))
            ad_rows.append({"kind": "text",
                             "text": (f">> {ad.get('name','?')} - "
                                      f"+${ad.get('upfront_cash',0)} upfront, "
                                      f"+${s_earn} /season"),
                             "col": C_CYAN})
            if ad.get("desc"):
                ad_rows.append({"kind": "text",
                                 "text": f"   - {ad['desc'][:40]}", "col": C_GREY_LIGHT})
        tt_sections.append(ad_rows)

    if show.get("desc"):
        tt_sections.append([
            {"kind": "text", "text": show["desc"], "col": C_GREY_LIGHT}
        ])

    ctx._add_tooltip(rect, {
        "type":     "show",
        "title":    show.get("name", ""),
        "subtitle": f"{show.get('genre','')} | AGE {age}",
        "sections": tt_sections,
    })


# --- VAULT SLOT ---

def _draw_vault_slot(ctx, rect, idx, state):
    """Draw a syndication vault slot - AGE FROZEN badge, financial preview."""
    show = state.reruns[idx] if idx < len(state.reruns) else None

    pygame.draw.rect(ctx.screen, C_GREEN_PANEL, rect, border_radius=3)
    pygame.draw.rect(ctx.screen, C_BORDER if show else C_BORDER_DIM,
                     rect, 1, border_radius=3)

    pygame.draw.rect(ctx.screen, C_AMBER_DIM,
                     pygame.Rect(rect.x + 1, rect.y + 1, 4, rect.height - 2),
                     border_radius=2)

    f_mi  = ctx._f("micro")
    step  = line_step(f_mi, 0.82)
    ty    = rect.y + 3
    lbl = f_mi.render(f"VAULT {idx + 1}", True, C_GREEN_DIM)
    ctx.screen.blit(lbl, (rect.x + 8, ty))
    ty += step

    if show is None:
        pygame.draw.line(ctx.screen, C_BORDER_DIM,
                         (rect.x + 7, ty), (rect.right - 4, ty))
        ty += 3
        empty  = f_mi.render("EMPTY - vault a show", True, C_GREEN_DIM)
        empty2 = f_mi.render("to earn passive reruns", True, C_BORDER_DIM)
        ctx.screen.blit(empty,  (rect.x + 8, ty))
        ctx.screen.blit(empty2, (rect.x + 8, ty + step))
        ctx._add_tooltip(rect, {
            "type":   "generic",
            "accent": C_AMBER_DIM,
            "title":  "Syndication Vault",
            "sections": [[
                {"kind": "text", "text": "Shows earn rerun views each season (25% of normal).", "col": C_GREY_LIGHT},
                {"kind": "text", "text": "Syndication Deal upgrade raises this to 50%.",         "col": C_GREY_LIGHT},
                {"kind": "text", "text": "Syndicate at peak age (Season 2) for best value.",    "col": C_AMBER},
            ]],
        })
        if state.selected_item and state.selected_item.get("shop_type") == "shows":
            ctx._add_click(rect, lambda i=idx: ctx._place_on_slot("reruns", i, state))
    else:
        age = show.get("age", 1)
        yld = calculate_yield(show, is_rerun=True,
                              active_perks=state.active_perks, season=state.season)

        _vc_prev = ctx.screen.get_clip()
        ctx.screen.set_clip(_vc_prev.clip(pygame.Rect(rect.x, rect.y, rect.width, rect.height - 20)))
        name_s = ctx._f("small").render(show.get("name", "???")[:16], True, C_WHITE)
        ctx.screen.blit(name_s, (rect.x + 8, ty))
        ty += line_step(ctx._f("small"), 0.80)

        badge_txt  = f"AGE {age} - FROZEN"
        badge_surf = f_mi.render(badge_txt, True, C_CYAN)
        badge_bg   = pygame.Rect(rect.x + 8, ty,
                                 badge_surf.get_width() + 8, badge_surf.get_height() + 2)
        pygame.draw.rect(ctx.screen, C_TINT_TEAL_BADGE, badge_bg, border_radius=3)
        pygame.draw.rect(ctx.screen, C_CYAN,             badge_bg, 1, border_radius=3)
        ctx.screen.blit(badge_surf, (rect.x + 12, ty + 1))
        ty += step

        net_col = C_NET_POS if yld["i"] >= 0 else C_NET_NEG
        yv = f_mi.render(
            f"~{yld['v']} views  NET ${yld['i']:+.0f}/s", True, net_col
        )
        ctx.screen.blit(yv, (rect.x + 8, ty))
        ctx.screen.set_clip(_vc_prev)

        rem_rect = pygame.Rect(rect.x + 8, rect.bottom - 18, rect.width - 16, 14)

        def _rem(i=idx):
            r = state.sell_show("reruns", i)
            ctx._toast(r["message"], r["level"])

        draw_button(ctx, rem_rect, "REMOVE", _rem,
                    text_color=C_RED, border_color=C_RED_DIM)

        ctx._add_tooltip(rect, {
            "type":     "show",
            "title":    show.get("name", ""),
            "subtitle": f"VAULT RERUN | AGE {age} FROZEN",
            "sections": [[
                {"kind": "kv", "key": "RERUN VIEWS",
                 "val": f"~{yld['v']} /season", "val_col": C_VIEWS_ACCENT},
                {"kind": "kv", "key": "NET INCOME",
                 "val": f"${yld['i']:+.0f} /season",
                 "val_col": C_NET_POS if yld["i"] >= 0 else C_NET_NEG},
                {"kind": "text", "text": "Upkeep is waived for vaulted shows.", "col": C_GREY_LIGHT},
            ]],
        })

        if not state.selected_item:
            def _open_vault_detail(s=show):
                ctx._show_detail   = {"show": s, "slot_idx": -1, "is_vault": True}
                ctx._detail_scroll = 0
            ctx._add_click(rect, _open_vault_detail)



# --- ACTIVE CONTRACTS BAR ---

def _draw_active_contracts_bar(ctx, rect, state):
    """Draw accepted contracts with status, requirement, and remaining seasons."""
    from engine.requirements import describe as desc_req

    pygame.draw.rect(ctx.screen, C_GREEN_PANEL, rect, border_radius=3)
    pygame.draw.rect(ctx.screen, C_VIEWS_ACCENT, rect, 1, border_radius=3)

    f  = ctx._f("micro")
    lh = max(20, rect.height // max(1, len(state.active_contracts) + 1))
    x  = rect.x + 6
    y  = rect.y + 4

    for entry in state.active_contracts:
        if y + lh > rect.bottom - 2:
            break
        ev      = entry.get("event", {})
        name    = ev.get("name", "?")
        req_d   = desc_req(ev.get("requirement", {}))
        rem     = entry.get("remaining_seasons", 0)
        done    = entry.get("fulfilled", False)
        rew     = ev.get("reward", {})
        pen     = ev.get("penalty", {})
        rew_str = f"+${rew.get('budget_bonus', 0)}" if rew.get("budget_bonus") else ""
        pen_str = f"-${pen.get('budget_loss', 0)}"  if pen.get("budget_loss")  else ""

        col  = C_NET_POS if done else C_VIEWS_ACCENT
        tick = "[DONE]" if done else f"[{rem}s LEFT]"

        # Contract seal: outer ring + filled centre.
        seal_col = C_NET_POS if done else C_VIEWS_ACCENT
        pygame.draw.circle(ctx.screen, seal_col, (x + 4, y + lh // 2), 5, 1)
        pygame.draw.circle(ctx.screen, seal_col, (x + 4, y + lh // 2), 2)

        name_s = f.render(f"{tick} {name[:22]}", True, col)
        ctx.screen.blit(name_s, (x + 13, y + 1))

        req_s = f.render(f"  REQ: {req_d[:28]}", True, C_AMBER_DIM)
        ctx.screen.blit(req_s, (x + 10, y + f.get_linesize() + 2))

        if rew_str or pen_str:
            rp_str = ""
            if rew_str: rp_str += f"WIN:{rew_str} "
            if pen_str: rp_str += f"FAIL:{pen_str}"
            rp_s = f.render(rp_str, True, C_GREY_MID)
            ctx.screen.blit(rp_s, (rect.right - rp_s.get_width() - 6, y + 1))

        ctx._add_tooltip(pygame.Rect(x, y, rect.width - 8, lh), {
            "type":  "event",
            "title": f"CONTRACT: {name}",
            "sections": [[
                {"kind": "kv", "key": "STATUS",
                 "val": "FULFILLED" if done else f"{rem} season(s) remaining",
                 "val_col": C_NET_POS if done else C_VIEWS_ACCENT},
                {"kind": "kv", "key": "REQUIREMENT", "val": req_d,           "val_col": C_AMBER},
                {"kind": "kv", "key": "REWARD",       "val": rew_str or "None", "val_col": C_NET_POS},
                {"kind": "kv", "key": "PENALTY",      "val": pen_str or "None", "val_col": C_RED},
            ]],
        })
        y += lh

    # Show queued shop events (fire at start of next season)
    pending = getattr(state, 'pending_events', [])
    for entry in pending:
        if y + lh > rect.bottom - 2:
            break
        ev   = entry.get("event", {})
        name = ev.get("name", "?")
        # Queued-event bolt icon.
        draw_event_icon(ctx.screen, pygame.Rect(x - 1, y + lh // 2 - 6, 12, 12), C_AMBER)
        ev_s = f.render(f"[QUEUED] {name[:26]}  — fires next season", True, C_AMBER)
        ctx.screen.blit(ev_s, (x + 13, y + 1))
        ctx._add_tooltip(pygame.Rect(x, y, rect.width - 8, lh), {
            "type":  "event",
            "title": f"QUEUED EVENT: {name}",
            "sections": [[
                {"kind": "kv", "key": "TIMING", "val": "Fires at START of next season", "val_col": C_AMBER},
                {"kind": "text", "text": ev.get("desc", "")[:80], "col": C_GREY_LIGHT},
            ]],
        })
        y += lh

    if not state.active_contracts and not pending:
        empty = f.render("No accepted contracts or queued events.", True, C_GREEN_DIM)
        ctx.screen.blit(empty, (x, rect.centery - 6))


# --- UPGRADES ROW ---

def _draw_upgrades(ctx, rect, state):
    """Draw active upgrades as labelled gear chips + empty slot boxes + count,
    matching the status strip in netexec_reference.py."""
    f_mi   = ctx._f("micro")
    chip_h = min(rect.height - 4, line_step(f_mi) + 4)
    top    = rect.y + (rect.height - chip_h) // 2
    cx     = rect.x + 4
    perks  = state.active_perks

    # Equipped upgrades: a coloured pill with a gear icon and the name.
    for perk in perks:
        name = perk.get("name", "?")[:14]
        nw   = f_mi.size(name)[0]
        chip = pygame.Rect(cx, top, nw + 26, chip_h)
        if chip.right > rect.right - 46:
            break
        hov  = chip.collidepoint(ctx._mouse_pos)
        col  = C_GREEN_BRIGHT if hov else C_CYAN
        pygame.draw.rect(ctx.screen, C_TINT_GREEN_TILE, chip, border_radius=3)
        pygame.draw.rect(ctx.screen, col, chip, 1, border_radius=3)
        gicon = pygame.Rect(chip.x + 4, chip.centery - 6, 12, 12)
        draw_upgrade_icon(ctx.screen, gicon, col)
        ctx.screen.blit(f_mi.render(name, True, C_WHITE),
                        (chip.x + 19, chip.centery - f_mi.get_height() // 2))
        cx = chip.right + 5

        upk_p = perk.get("upkeep", 0)
        ctx._add_tooltip(chip, {
            "type":  "upgrade",
            "title": f"Gear {perk.get('name', '')}",
            "sections": [
                [
                    {"kind": "kv", "key": "UPKEEP",
                     "val": f"${upk_p} /season" if upk_p else "Free",
                     "val_col": C_AMBER_DIM if upk_p else C_NET_POS},
                    {"kind": "kv", "key": "MAX ACTIVE",
                     "val": str(MAX_ACTIVE_UPGRADES), "val_col": C_GREY_LIGHT},
                ],
                [{"kind": "text", "text": perk.get("desc", ""), "col": C_GREY_LIGHT}],
            ],
        })

    # Empty slot boxes for the remaining capacity.
    empty_n = max(0, MAX_ACTIVE_UPGRADES - len(perks))
    sq_y    = top + (chip_h - 11) // 2
    for i in range(empty_n):
        sq = pygame.Rect(cx + i * 15, sq_y, 11, 11)
        if sq.right > rect.right - 34:
            break
        pygame.draw.rect(ctx.screen, C_BORDER_DIM, sq, 1)

    # n / MAX count, right-aligned.
    cnt = f_mi.render(f"{len(perks)}/{MAX_ACTIVE_UPGRADES}", True, C_GREY_LIGHT)
    ctx.screen.blit(cnt, (rect.right - cnt.get_width() - 4,
                          top + (chip_h - cnt.get_height()) // 2))


# --- MONOPOLY BAR ---

def _mono_short(bonus: dict) -> str:
    """One-line summary of a monopoly bonus for display in the bar and tooltips."""
    t     = bonus.get("type", "")
    parts = []
    vm    = bonus.get("views_mult", 1.0)
    ib    = bonus.get("income_bonus", 0)
    if t == "upkeep_halved":
        parts.append("Upkeep -50%")
    elif t == "star_amplifier":
        amp = bonus.get("star_prime_mult", 2.5)
        parts.append(f"Stars x{amp} all slots")
    elif t == "ad_multiplier":
        adm = bonus.get("ad_mult", 1.5)
        parts.append(f"Ad income x{adm:.2f}")
    elif t == "target_reduction":
        tm = bonus.get("target_mult", 0.88)
        parts.append(f"Quota x{tm:.2f} (easier)")
    elif t == "budget_boost":
        bp = bonus.get("budget_per_season", 0)
        parts.append(f"+${bp} budget/season")
    if vm != 1.0:
        parts.append(f"x{vm:.2f} Views")
    if ib:
        parts.append(f"+${ib} Income/s")
    return "  |  ".join(parts) if parts else "Bonus active"


_GENRE_ORDER = ["DRAMA", "SITCOM", "SCIFI", "REALITY", "SPORTS", "NEWS", "COOKING"]


def _draw_monopoly_bar(ctx, rect, state):
    """Draw the genre monopoly reference panel.

    Always shows all 7 genre bonuses so players know what to aim for.
    Active monopoly is highlighted and announced at the top.
    """
    summary  = state.get_lineup_summary()
    registry = get_genre_registry()
    f_mi     = ctx._f("micro")
    lh       = f_mi.get_linesize() + 2
    is_mono  = summary["is_monopoly"]
    active_g = summary.get("genre")
    live_genres = summary.get("live_genres", [])
    single_genre = live_genres[0] if len(live_genres) == 1 else None

    # Panel background
    bg_col  = C_TINT_GREEN_DEEP if is_mono else C_GREEN_PANEL
    bd_col  = (GENRE_COLORS.get(active_g, (C_GREEN_BRIGHT, C_GREEN_DIM))[0]
               if is_mono else C_BORDER_DIM)
    pygame.draw.rect(ctx.screen, bg_col, rect, border_radius=3)
    pygame.draw.rect(ctx.screen, bd_col, rect, 2 if is_mono else 1, border_radius=3)

    x  = rect.x + 6
    y  = rect.y + 3

    # ── Status line ───────────────────────────────────────────────────────────
    if is_mono:
        gcol  = GENRE_COLORS.get(active_g, (C_GREEN_BRIGHT, C_GREEN_DIM))[0]
        bonus = summary.get("bonus", {})
        draw_blink_dot(ctx.screen, x + 3, y + lh // 2, 4, gcol, ctx._tick_ms, BLINK_PERIOD_MS)
        status_txt = f" ★ {active_g} MONOPOLY ACTIVE — {_mono_short(bonus)}"
        st = f_mi.render(status_txt[:90], True, gcol)
        ctx.screen.blit(st, (x + 10, y))
        y += lh + 2
    elif single_genre:
        gcol  = GENRE_COLORS.get(single_genre, (C_GREEN_BRIGHT, C_GREEN_DIM))[0]
        entry = registry.get(single_genre, {})
        mono  = entry.get("monopoly", {})
        short = _mono_short(mono) if mono else "?"
        hint  = f"→ {single_genre} MONOPOLY IF ALL 4 SLOTS FILLED: {short}"
        ht    = f_mi.render(hint[:90], True, gcol)
        ctx.screen.blit(ht, (x, y))
        y += lh + 2
    else:
        status_col = C_GREEN_DIM if not summary["all_filled"] else C_AMBER_DIM
        msg = ("FILL ALL 4 SLOTS WITH ONE GENRE FOR A MONOPOLY BONUS"
               if not summary["all_filled"] else "NO MONOPOLY — MIX OF GENRES ON AIR")
        ms  = f_mi.render(msg, True, status_col)
        ctx.screen.blit(ms, (x, y))
        y += lh + 2

    # ── Divider + "ALL GENRE BONUSES" header ─────────────────────────────────
    pygame.draw.line(ctx.screen, C_BORDER_DIM, (x, y), (rect.right - 6, y))
    y += 2
    hdr = f_mi.render("ALL GENRE MONOPOLY BONUSES:", True, C_GREEN_MID)
    ctx.screen.blit(hdr, (x, y))
    y += lh

    # ── One row per genre ─────────────────────────────────────────────────────
    for g in _GENRE_ORDER:
        entry = registry.get(g, {})
        mono  = entry.get("monopoly")
        if not mono or y + lh > rect.bottom:
            continue
        gcol = GENRE_COLORS.get(g, (C_GREEN_BRIGHT, C_GREEN_DIM))[0]
        # Highlight the active monopoly genre; dim genres not on air
        if is_mono and g == active_g:
            row_col = gcol
        elif single_genre and g == single_genre:
            row_col = gcol
        elif live_genres and g not in live_genres:
            row_col = tuple(max(0, int(c * 0.45)) for c in gcol)
        else:
            row_col = gcol

        label = f_mi.render(f"{g:<8}", True, row_col)
        ctx.screen.blit(label, (x, y))
        bonus_txt = _mono_short(mono)
        bt = f_mi.render(bonus_txt[:72], True, row_col)
        ctx.screen.blit(bt, (x + label.get_width() + 4, y))

        # Active monopoly gets a blink dot
        if is_mono and g == active_g:
            draw_blink_dot(ctx.screen, rect.right - 10, y + lh // 2,
                           3, gcol, ctx._tick_ms, BLINK_PERIOD_MS)
        y += lh

    # Tooltip still available for the full desc on hover
    tooltip_rows = []
    for g in _GENRE_ORDER:
        entry = registry.get(g, {})
        mono  = entry.get("monopoly")
        if not mono:
            continue
        gcol = GENRE_COLORS.get(g, (C_GREEN_BRIGHT, C_GREEN_DIM))[0]
        tooltip_rows.append({"kind": "kv", "key": g,
                              "val": mono.get("desc", _mono_short(mono))[:80],
                              "val_col": gcol})
    ctx._add_tooltip(rect, {
        "type":     "generic",
        "accent":   C_AMBER,
        "title":    "GENRE MONOPOLY BONUSES — full descriptions",
        "sections": [tooltip_rows],
    })


# --- SEASONAL STATUS STRIP ---

def _draw_seasonal_strip(ctx, rect, state):
    """
    Compact strip listing active seasonal events, contracts, and mandates.
    Offers on the offers board show an ACCEPT button.
    """
    from engine.requirements import describe as desc_req

    pygame.draw.rect(ctx.screen, C_GREEN_PANEL, rect, border_radius=3)
    pygame.draw.rect(ctx.screen, C_BLUE_DIM,    rect, 1, border_radius=3)

    f  = ctx._f("micro")
    lh = f.get_linesize() + 1
    x  = rect.x + 6
    y  = rect.y + 3

    # Header
    hdr = f.render("SEASONAL EVENTS", True, C_BLUE)
    ctx.screen.blit(hdr, (x, y))
    y += lh + 1

    items_shown = 0

    for entry in state.active_seasonal_modifiers:
        if y + lh > rect.bottom - 2:
            break
        name = entry.get("event", {}).get("name", "?")
        rem  = entry.get("remaining_seasons", 0)
        line = f.render(f">> {name[:30]}  [{rem}s]", True, C_CYAN)
        ctx.screen.blit(line, (x, y))
        y += lh
        items_shown += 1

    for entry in state.active_mandates:
        if y + lh > rect.bottom - 2:
            break
        ev      = entry.get("event", {})
        name    = ev.get("name", "?")
        req_d   = desc_req(ev.get("requirement", {}))
        rem     = entry.get("remaining_seasons", 0)
        line    = f.render(f"[!] {name[:22]}  {req_d[:24]}  [{rem}s]", True, C_AMBER)
        ctx.screen.blit(line, (x, y))
        y += lh
        items_shown += 1

    for entry in state.active_contracts:
        if y + lh > rect.bottom - 2:
            break
        ev      = entry.get("event", {})
        name    = ev.get("name", "?")
        req_d   = desc_req(ev.get("requirement", {}))
        rem     = entry.get("remaining_seasons", 0)
        done    = entry.get("fulfilled", False)
        col     = C_NET_POS if done else C_VIEWS_ACCENT
        tick    = "[x]" if done else "[ ]"
        line    = f.render(f"{tick} {name[:22]}  {req_d[:24]}  [{rem}s]", True, col)
        ctx.screen.blit(line, (x, y))
        y += lh
        items_shown += 1

    # Offers board - show one accept button per offer
    for offer in state.available_contracts:
        if y + lh > rect.bottom - 2:
            break
        name     = offer.get("name", "?")
        req_d    = desc_req(offer.get("requirement", {}))
        offer_id = offer.get("id", "")
        line     = f.render(f"+ {name[:22]}  {req_d[:22]}", True, C_SELECTED)
        ctx.screen.blit(line, (x, y))
        btn_w    = 50
        btn_r    = pygame.Rect(rect.right - btn_w - 4, y - 1, btn_w, lh + 2)
        pygame.draw.rect(ctx.screen, C_TINT_GREEN_FILL, btn_r, border_radius=2)
        pygame.draw.rect(ctx.screen, C_NET_POS,          btn_r, 1, border_radius=2)
        accept_s = f.render("ACCEPT", True, C_NET_POS)
        ctx.screen.blit(accept_s, accept_s.get_rect(center=btn_r.center))

        def _accept(oid=offer_id):
            r = state.accept_contract(oid)
            ctx._toast(r["message"], r["level"])

        ctx._add_click(btn_r, _accept)
        y += lh
        items_shown += 1

    if items_shown == 0:
        none_s = f.render("No active seasonal events this season.", True, C_GREEN_DIM)
        ctx.screen.blit(none_s, (x, y))