"""
playing/detail.py — NETEXEC
===========================
Show detail modal: comprehensive info panel for a scheduled show.

Public entry point
------------------
  _draw_show_detail_modal(ctx, state)
"""

import pygame

from engine.constants import (
    C_BG, C_PANEL, C_BORDER_DIM,
    C_AMBER, C_AMBER_DIM, C_AMBER_GLOW,
    C_CYAN,
    C_GREEN_BRIGHT, C_GREEN_MID, C_GREEN_DIM,
    C_RED, C_WHITE,
    C_GREY_LIGHT, C_GREY_MID,
    C_VIEWS_ACCENT, C_INCOME_ACCENT,
    C_NET_POS, C_NET_NEG,
    TIME_SLOTS, GENRE_COLORS,
)
from engine.network import calculate_yield
from engine.cards import check_condition, evaluate_star, evaluate_ad
from content.ads import net_cost as _ad_net_cost
from ...widgets import (
    draw_button, draw_modal_overlay, draw_text_wrapped, draw_kv,
    draw_genre_badge,
)

# --- SHOW DETAIL MODAL ---


def _draw_show_detail_modal(ctx, state):
    """Full-detail panel for a scheduled show — opened by clicking a slot card."""
    info = ctx._show_detail
    if not info:
        return

    show     = info.get("show", {})
    slot_idx = info.get("slot_idx", -1)
    is_vault = info.get("is_vault", False)

    genre     = show.get("genre", "")
    age       = show.get("age", 1)
    att_stars = show.get("attached", {}).get("star", [])
    att_ads   = show.get("attached", {}).get("ad",  [])
    star_max  = show.get("star_slots", show.get("slots", {}).get("star", 0))
    ad_max    = show.get("ad_slots",   show.get("slots", {}).get("ad",  0))

    yld = calculate_yield(
        show,
        is_rerun     = is_vault,
        start_idx    = max(0, slot_idx),
        active_perks = state.active_perks,
        season       = state.season,
    )

    rec       = show.get("rec_slots") or []
    in_rec    = is_vault or not rec or slot_idx in rec or slot_idx < 0
    rec_names = [TIME_SLOTS[s]["label"] for s in rec if 0 <= s < len(TIME_SLOTS)]
    slot_name = TIME_SLOTS[slot_idx]["label"] if 0 <= slot_idx < len(TIME_SLOTS) else (
        "VAULT (FROZEN)" if is_vault else "--"
    )
    rec_str = ", ".join(rec_names) if rec_names else "Any slot"

    base_v     = show.get("base_views", 0)
    upkeep_val = 0 if is_vault else show.get("upkeep", 0)
    ad_income  = yld.get("ad_income", 0.0)
    net_val    = yld.get("i", 0)

    v_st    = float(base_v)
    st_mult = 1.0
    for star in att_stars:
        eff = evaluate_star(star, show)
        v_st += eff["v_flat"]
        vm = eff["v_mult"]
        if vm > 1.0:
            st_mult *= vm
    with_stars_v = int(v_st * st_mult)

    def _cond_text(cond):
        if not cond or cond.get("type", "always") == "always":
            return "Always active"
        t = cond.get("type", "")
        if t == "genre":
            return "Genre: " + ", ".join(cond.get("genres", []))
        if t == "size_min":
            return f"Show size >= {cond.get('value', 2)}"
        if t == "ad_slots_min":
            return f"Ad slots >= {cond.get('value', 2)}"
        if t == "age_min":
            return f"Age >= {cond.get('value', 1)} seasons"
        return "Special condition"

    def _fmt_effect(eff: dict) -> str:
        parts = []
        if eff.get("v_flat"):
            parts.append(f"+{eff['v_flat']} views")
        if eff.get("v_mult", 1.0) != 1.0:
            parts.append(f"{eff['v_mult']:.2f}x mult")
        if eff.get("income"):
            parts.append(f"+${eff['income']}/season")
        if eff.get("upkeep"):
            parts.append(f"{eff['upkeep']:+d} upkeep")
        return " - ".join(parts) if parts else "No effect"

    f_hdr = ctx._f("header")
    f_bd  = ctx._f("bold")
    f_sm  = ctx._f("small")
    f_mi  = ctx._f("micro")
    lh    = f_mi.get_linesize() + 2
    lh_sm = f_sm.get_linesize() + 2

    MPAD      = 14
    mw        = 580
    INNER_W   = mw - MPAD * 2
    HDR_STRIP = 44
    DIV_H     = 10

    def _star_card_h(): return lh * 4 + 8
    def _ad_card_h():   return lh * 5 + 8

    stars_body_h = (len(att_stars) * (_star_card_h() + 3)) if att_stars else lh
    ads_body_h   = (len(att_ads)   * (_ad_card_h()  + 3)) if att_ads   else lh
    warn_h       = 36 if (not in_rec and rec) else 0

    total_h = (
        HDR_STRIP + MPAD
        + lh + lh_sm + 4
        + DIV_H
        + lh_sm + 2 + 64
        + DIV_H
        + lh_sm + 2 + lh * 5
        + DIV_H
        + lh_sm + 2 + stars_body_h
        + DIV_H
        + lh_sm + 2 + ads_body_h
        + warn_h
        + 48 + MPAD
    )
    mh    = min(total_h, ctx._sh - 80)
    cx    = ctx._sw // 2
    modal = pygame.Rect(cx - mw // 2, (ctx._sh - mh) // 2, mw, mh)

    draw_modal_overlay(ctx, alpha=180)

    pygame.draw.rect(ctx.screen, C_PANEL,        modal, border_radius=8)
    pygame.draw.rect(ctx.screen, C_GREEN_BRIGHT, modal, 2, border_radius=8)

    g_text_col, g_bg_col = GENRE_COLORS.get(genre, (C_GREEN_BRIGHT, C_GREEN_DIM))

    header_rect = pygame.Rect(modal.x + 2, modal.y + 2, modal.width - 4, HDR_STRIP - 2)
    pygame.draw.rect(ctx.screen, g_bg_col, header_rect, border_radius=6)
    show_name = show.get("name", "???")
    title = f_hdr.render(show_name[:36], True, g_text_col)
    ctx.screen.blit(title, (header_rect.x + 10, header_rect.y + 8))

    slot_col = C_GREEN_BRIGHT if in_rec else C_RED
    slot_s = f_sm.render(slot_name, True, slot_col)
    ctx.screen.blit(slot_s, (header_rect.right - slot_s.get_width() - 10, header_rect.y + 12))

    # Scrollable content area (below header strip, above close button)
    CLOSE_H      = 48
    content_top  = modal.y + HDR_STRIP
    content_bot  = modal.bottom - CLOSE_H
    content_view = content_bot - content_top
    max_scroll   = max(0, total_h - HDR_STRIP - CLOSE_H - 8)
    ctx._detail_scroll = max(0, min(max_scroll, ctx._detail_scroll))
    scroll = ctx._detail_scroll

    old_clip = ctx.screen.get_clip()
    ctx.screen.set_clip(pygame.Rect(modal.x, content_top, modal.width, content_view))

    x = modal.x + MPAD
    y = modal.y + HDR_STRIP + 6 - scroll

    slot_line = f_sm.render(f"SLOT: {slot_name}", True, slot_col)
    ctx.screen.blit(slot_line, (x, y))
    y += lh_sm

    badge_rect = None
    if genre:
        badge_rect = draw_genre_badge(ctx.screen, genre, x, y, f_sm)
    age_col = C_AMBER if age == 2 else (C_RED if age >= 6 else C_GREEN_DIM)
    age_x = badge_rect.right + 8 if badge_rect else x
    age_s = f_sm.render(f"AGE {age}", True, age_col)
    ctx.screen.blit(age_s, (age_x, y))
    size_s = f_sm.render(f"SIZE {show.get('size', 1)}", True, C_GREY_LIGHT)
    ctx.screen.blit(size_s, (age_x + age_s.get_width() + 10, y))

    slots_text = f"STARS {len(att_stars)}/{star_max}  ADS {len(att_ads)}/{ad_max}"
    slots_s = f_sm.render(slots_text, True, C_GREY_LIGHT)
    ctx.screen.blit(slots_s, (modal.right - MPAD - slots_s.get_width(), y))
    y += lh_sm + 4

    def _section_header(label: str, y_pos: int, color: tuple = C_GREEN_MID) -> int:
        hdr = f_sm.render(label, True, color)
        ctx.screen.blit(hdr, (x, y_pos))
        line_y = y_pos + hdr.get_height() // 2 + 2
        pygame.draw.line(ctx.screen, C_BORDER_DIM,
                         (x + hdr.get_width() + 6, line_y),
                         (modal.right - MPAD, line_y))
        return y_pos + lh_sm + 2

    y = _section_header("SUMMARY", y)
    desc = show.get("desc", "") or "No description available."
    draw_text_wrapped(
        ctx.screen,
        desc,
        pygame.Rect(x, y, INNER_W, 64),
        f_sm,
        C_GREY_LIGHT,
    )
    y += 64 + DIV_H

    y = _section_header("PERFORMANCE", y)
    col_w = INNER_W // 2
    left_x = x
    right_x = x + col_w + 10

    # Column width = widest label in either grid + gap, so the value column is
    # aligned AND can never overlap a wide label (draw_kv measures the label).
    _kv_keys = ["BASE VIEWS", "WITH STARS", "PROJECTED", "UPKEEP", "AD INCOME",
                "NET", "CURRENT SLOT", "RECOMMENDED", "AGE", "SIZE", "SLOTS"]
    _kv_col_w = max(f_mi.size(f"{k}:")[0] for k in _kv_keys) + 10

    def _draw_kv(x_pos: int, y_pos: int, key: str, value: str, val_col: tuple):
        draw_kv(ctx, f"{key}:", value, x_pos, y_pos, f_mi,
                C_GREY_LIGHT, val_col, col_w=_kv_col_w, gap=8)

    net_col = C_NET_POS if net_val >= 0 else C_NET_NEG
    upkeep_col = C_AMBER_DIM if upkeep_val else C_NET_POS

    left_rows = [
        ("BASE VIEWS", f"{base_v:,}/season", C_VIEWS_ACCENT),
        ("WITH STARS", f"{with_stars_v:,}/season", C_VIEWS_ACCENT),
        ("PROJECTED", f"{yld.get('v', 0):,}/season", C_VIEWS_ACCENT),
    ]
    right_rows = [
        ("UPKEEP", f"${upkeep_val}/season" if upkeep_val else "Free", upkeep_col),
        ("AD INCOME", f"${ad_income:.0f}/season", C_INCOME_ACCENT),
        ("NET", f"${net_val:+.0f}/season", net_col),
    ]

    for i, (key, val, col) in enumerate(left_rows):
        _draw_kv(left_x, y + i * lh, key, val, col)
    for i, (key, val, col) in enumerate(right_rows):
        _draw_kv(right_x, y + i * lh, key, val, col)
    y += lh * 3 + DIV_H

    y = _section_header("DETAILS", y)
    detail_rows = [
        ("CURRENT SLOT", slot_name, slot_col),
        ("RECOMMENDED", rec_str, C_GREEN_BRIGHT if in_rec else C_RED),
        ("AGE", f"{age} seasons", age_col),
        ("SIZE", str(show.get("size", 1)), C_GREY_LIGHT),
        ("SLOTS", f"Stars {len(att_stars)}/{star_max}  Ads {len(att_ads)}/{ad_max}", C_GREY_LIGHT),
    ]
    for key, val, col in detail_rows:
        _draw_kv(x, y, key, val, col)
        y += lh
    y += DIV_H

    star_hdr = f"STARS ({len(att_stars)}/{star_max})" if star_max else "STARS"
    y = _section_header(star_hdr, y, C_AMBER)
    if not att_stars:
        none_s = f_mi.render("No stars attached.", True, C_GREY_MID)
        ctx.screen.blit(none_s, (x, y))
        y += lh
    else:
        for star in att_stars:
            card = pygame.Rect(x, y, INNER_W, _star_card_h())
            active = check_condition(star.get("condition"), show)
            card_col = C_AMBER_GLOW if active else C_AMBER_DIM
            pygame.draw.rect(ctx.screen, C_BG, card, border_radius=4)
            pygame.draw.rect(ctx.screen, card_col, card, 1, border_radius=4)

            nm = f_bd.render(star.get("name", "?")[:28], True, card_col)
            ctx.screen.blit(nm, (card.x + 6, card.y + 4))

            eff_txt = _fmt_effect(evaluate_star(star, show))
            eff_col = C_GREEN_BRIGHT if active else C_GREY_LIGHT
            ctx.screen.blit(f_mi.render(eff_txt[:70], True, eff_col),
                            (card.x + 6, card.y + 4 + lh))

            cond_txt = star.get("condition_text") or _cond_text(star.get("condition"))
            ctx.screen.blit(f_mi.render(f"Condition: {cond_txt}"[:70], True, C_GREY_MID),
                            (card.x + 6, card.y + 4 + lh * 2))

            desc_txt = star.get("desc", "")
            if desc_txt:
                ctx.screen.blit(f_mi.render(desc_txt[:72], True, C_GREY_LIGHT),
                                (card.x + 6, card.y + 4 + lh * 3))
            y += card.height + 3

    y += DIV_H

    ad_hdr = f"ADS ({len(att_ads)}/{ad_max})" if ad_max else "ADS"
    y = _section_header(ad_hdr, y, C_CYAN)
    if not att_ads:
        none_s = f_mi.render("No ads attached.", True, C_GREY_MID)
        ctx.screen.blit(none_s, (x, y))
        y += lh
    else:
        for ad in att_ads:
            card = pygame.Rect(x, y, INNER_W, _ad_card_h())
            active = check_condition(ad.get("condition"), show)
            card_col = C_CYAN if active else C_GREY_MID
            pygame.draw.rect(ctx.screen, C_BG, card, border_radius=4)
            pygame.draw.rect(ctx.screen, card_col, card, 1, border_radius=4)

            nm = f_bd.render(ad.get("name", "?")[:28], True, card_col)
            ctx.screen.blit(nm, (card.x + 6, card.y + 4))

            eff_txt = _fmt_effect(evaluate_ad(ad, show))
            eff_col = C_NET_POS if active else C_GREY_LIGHT
            ctx.screen.blit(f_mi.render(eff_txt[:70], True, eff_col),
                            (card.x + 6, card.y + 4 + lh))

            cond_txt = ad.get("condition_text") or _cond_text(ad.get("condition"))
            ctx.screen.blit(f_mi.render(f"Condition: {cond_txt}"[:70], True, C_GREY_MID),
                            (card.x + 6, card.y + 4 + lh * 2))

            upfront = ad.get("upfront_cash", 0)
            net_cost = _ad_net_cost(ad, state)
            money_line = f"Upfront +${upfront}, Net cost ${net_cost:.0f}"
            ctx.screen.blit(f_mi.render(money_line[:70], True, C_INCOME_ACCENT),
                            (card.x + 6, card.y + 4 + lh * 3))

            desc_txt = ad.get("desc", "")
            if desc_txt:
                ctx.screen.blit(f_mi.render(desc_txt[:72], True, C_GREY_LIGHT),
                                (card.x + 6, card.y + 4 + lh * 4))
            y += card.height + 3

    if not in_rec and rec:
        warn = f_mi.render("Not in recommended slot: -30% views", True, C_RED)
        ctx.screen.blit(warn, (x, y))
        y += lh + 2

    # Restore clip and draw fixed-position close button + scroll indicator
    ctx.screen.set_clip(old_clip)

    # Scroll bar on right edge of modal
    if max_scroll > 0:
        sbar_x   = modal.right - 8
        sbar_top = content_top + 2
        sbar_h   = content_view - 4
        pygame.draw.rect(ctx.screen, C_BG,
                         pygame.Rect(sbar_x, sbar_top, 6, sbar_h), border_radius=3)
        thumb_h   = max(20, int(sbar_h * content_view / total_h))
        thumb_y   = sbar_top + int((sbar_h - thumb_h) * scroll / max_scroll)
        pygame.draw.rect(ctx.screen, C_GREEN_MID,
                         pygame.Rect(sbar_x + 1, thumb_y, 4, thumb_h), border_radius=2)
        scroll_hint = f_mi.render("SCROLL", True, C_GREEN_DIM)
        ctx.screen.blit(scroll_hint, (modal.x + MPAD, content_bot - f_mi.get_linesize() - 2))

    btn_w, btn_h = 120, 32
    close_rect = pygame.Rect(modal.centerx - btn_w // 2,
                             modal.bottom - MPAD - btn_h,
                             btn_w, btn_h)

    def _close():
        ctx._show_detail   = None
        ctx._detail_scroll = 0

    draw_button(ctx, close_rect, "CLOSE", _close,
                border_color=C_GREEN_BRIGHT, text_color=C_WHITE)
