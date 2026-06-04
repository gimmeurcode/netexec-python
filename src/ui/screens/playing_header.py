"""
playing_header.py — NETEXEC
=============================
HUD bar and end-of-season projection counter for the PLAYING screen.

Public entry point
------------------
  _draw_header(ctx, state)
"""

import math
import pygame

from engine.constants import (
    C_PANEL, C_PANEL_BORDER,
    C_GREEN_BRIGHT, C_AMBER, C_AMBER_DIM, C_RED, C_WHITE,
    C_GREY_LIGHT, C_GREY_MID, C_GREY_DARK,
    C_NET_NEG, C_VIEWS_ACCENT, C_INCOME_ACCENT,
    BLINK_PERIOD_MS, MAX_SEASONS,
)
from ..theme import (
    C_TINT_GREEN_VIVID, C_TINT_GREEN_BADGE, C_TINT_RED_BADGE,
)
from ..assets import draw_blink_dot
from ..screen_enum import GameScreen
from ..widgets import draw_button, draw_row, line_step


def _draw_header(ctx, state):
    """
    Broadcast master control room header — four blocks left to right.

    [ON-AIR + NETEXEC logo] | [SEASON N/12 + progress + quota] |
    [PROJECTED VIEWS + INCOME + badge]  |  [BUDGET + upkeep + PAUSE]  | [AIR SEASON ▶]
    """
    hud_h = ctx.layout.hud_h
    hdr = pygame.Rect(0, 0, ctx._sw, hud_h)
    pygame.draw.rect(ctx.screen, C_PANEL, hdr)
    pygame.draw.line(ctx.screen, C_PANEL_BORDER, (0, 0), (ctx._sw, 0))
    pygame.draw.line(ctx.screen, C_PANEL_BORDER,
                     (0, hud_h - 1), (ctx._sw, hud_h - 1), 2)

    # Clip all header drawing to the HUD rect so nothing bleeds into panels below
    _hud_clip = pygame.Rect(0, 0, ctx._sw, hud_h)
    _old_clip = ctx.screen.get_clip()
    ctx.screen.set_clip(_hud_clip)

    # ── Ink-safe three-row stack ─────────────────────────────────────────────
    # Each HUD block lays its content on at most THREE text rows whose vertical
    # step is derived from the real font line height (never a magic constant),
    # so rows can never collide even at the minimum hud_h (68 px). The two-colour
    # econ lines are merged onto a single draw_row line to stay within 3 rows.
    f_mi   = ctx._f("micro")
    _top   = 5
    # Largest safe step that fits 3 rows + one line of ink inside the plate.
    _usable = (hud_h - 4) - _top
    _row_step = max(line_step(f_mi, 0.78),            # ink-safe minimum (~19 px)
                    min(line_step(f_mi), _usable // 2))
    _r1 = _top
    _r2 = _r1 + _row_step
    _r3 = _r2 + _row_step
    _r4 = _r3                                    # legacy alias: 4th line folds onto r3
    _btn_h = max(12, min(_row_step + 2, hud_h - _r3 - 2))

    # ── Block geometry (proportional, adaptive) ───────────────────────────────
    air_w = 158
    air_x = ctx._sw - air_w - 6
    gap   = 12
    avail = air_x - 8

    lb_w = max(176, int(avail * 0.167))
    cl_w = max(200, int(avail * 0.210))
    cr_w = max(268, int(avail * 0.294))
    rb_w = avail - lb_w - cl_w - cr_w - gap * 3

    lb_x = 8
    cl_x = lb_x + lb_w + gap
    cr_x = cl_x + cl_w + gap
    rb_x = cr_x + cr_w + gap

    # ── High-contrast plate backgrounds for each HUD block ───────────────────
    _plate_h = hud_h - 8
    _plate_r = 4
    for px, pw in ((lb_x, lb_w), (cl_x, cl_w), (cr_x, cr_w), (rb_x, rb_w)):
        pygame.draw.rect(ctx.screen, C_GREY_DARK,
                         pygame.Rect(px, 4, pw, _plate_h), border_radius=_plate_r)

    # ── Block 1: Network Identity ─────────────────────────────────────────────
    draw_blink_dot(ctx.screen, lb_x + 8, _r1 + 5, 5, C_RED, ctx._tick_ms, BLINK_PERIOD_MS)
    on_lbl = ctx._f("micro").render("ON AIR", True, C_RED)
    ctx.screen.blit(on_lbl, (lb_x + 17, _r1))

    logo = ctx._f("header").render("NETEXEC", True, C_GREEN_BRIGHT)
    ctx.screen.blit(logo, (lb_x + 4, _r2))

    sub_str  = f"RUN {state.run}  PRESTIGE {state.network_prestige}"
    _lb_clip = pygame.Rect(lb_x, 0, lb_w, hud_h)
    ctx.screen.set_clip(_lb_clip)
    sub      = ctx._f("micro").render(sub_str, True, C_GREY_LIGHT)
    ctx.screen.blit(sub, (lb_x + 4, _r4))
    ctx.screen.set_clip(_hud_clip)

    # ── Block 2: Season Status ────────────────────────────────────────────────
    ctx.screen.set_clip(_hud_clip.clip(pygame.Rect(cl_x, 0, cl_w, hud_h)))
    s_col  = C_AMBER if state.season >= MAX_SEASONS else C_WHITE
    s_surf = ctx._f("bold").render(f"SEASON {state.season} / {MAX_SEASONS}", True, s_col)
    ctx.screen.blit(s_surf, (cl_x, _r1))

    bar_w    = cl_w - 6
    bar_rect = pygame.Rect(cl_x, _r2, bar_w, 9)
    pygame.draw.rect(ctx.screen, C_GREY_DARK, bar_rect, border_radius=3)
    progress = min(state.total_views / max(state.current_target, 1), 1.0)
    fill_w   = int(bar_w * progress)
    if fill_w > 0:
        if progress >= 1.0:
            fill_col = C_GREEN_BRIGHT
        elif progress >= 0.8:
            fill_col = C_AMBER
        else:
            fill_col = C_RED
        pygame.draw.rect(ctx.screen, fill_col,
                         pygame.Rect(cl_x, _r2, fill_w, 9), border_radius=3)
    pygame.draw.rect(ctx.screen, C_PANEL_BORDER, bar_rect, 1, border_radius=3)

    # Row 3 — current/target views and the next-season quota on ONE measured
    # line (draw_row spaces each coloured segment so they can't collide).
    v_col = C_GREEN_BRIGHT if state.total_views >= state.current_target else C_RED
    _tgt = state.current_target
    _tgt_str = f"{_tgt // 1000}k" if _tgt >= 1000 else str(_tgt)
    draw_row(ctx, [
        (f"{state.total_views:,}/{_tgt_str}", v_col),
        (f"NEXT S{state.next_target}", C_GREY_MID),
    ], cl_x, _r3, f_mi, gap=10)
    ctx.screen.set_clip(_hud_clip)

    # ── Block 3: End-of-Season Projection ────────────────────────────────────
    ctx.screen.set_clip(_hud_clip.clip(pygame.Rect(cr_x, 0, cr_w, hud_h)))
    proj_views, proj_income = state.preview_lineup_yield()

    proj_lbl = f_mi.render("PROJECTED END OF SEASON", True, C_GREY_LIGHT)
    ctx.screen.blit(proj_lbl, (cr_x, _r1))

    # Row 2 — projected views and income on one measured line.
    v_col2 = C_VIEWS_ACCENT if proj_views > 0 else C_NET_NEG
    i_col  = C_INCOME_ACCENT if proj_income >= 0 else C_NET_NEG
    draw_row(ctx, [
        (f"+{proj_views:,}v", v_col2),
        (f"${proj_income:+.0f}", i_col),
    ], cr_x, _r2, f_mi, gap=12)

    views_needed = max(0, state.current_target - state.total_views)
    if proj_views >= views_needed:
        badge_txt = "[+] ON TRACK"
        badge_col = C_GREEN_BRIGHT
        badge_bg  = C_TINT_GREEN_BADGE
    else:
        shortfall = views_needed - proj_views
        badge_txt = f"[-] SHORT BY {shortfall:,}"
        badge_col = C_RED
        badge_bg  = C_TINT_RED_BADGE
    badge_surf = ctx._f("micro").render(badge_txt, True, badge_col)
    badge_rect = pygame.Rect(cr_x, _r4, badge_surf.get_width() + 14, _btn_h)
    pygame.draw.rect(ctx.screen, badge_bg,  badge_rect, border_radius=3)
    pygame.draw.rect(ctx.screen, badge_col, badge_rect, 1, border_radius=3)
    ctx.screen.blit(badge_surf, (cr_x + 7, _r4 + 2))
    ctx.screen.set_clip(_hud_clip)

    # ── Block 4: Budget & Controls ────────────────────────────────────────────
    # Three financial lines + LEDGER toggle + PAUSE button
    ctx.screen.set_clip(_hud_clip.clip(pygame.Rect(rb_x, 0, rb_w, hud_h)))
    _, gross_income, total_upkeep = state.preview_lineup_breakdown()
    proj_net = gross_income - total_upkeep

    b_col  = C_RED if state.budget < 0 else C_AMBER
    b_surf = ctx._f("bold").render(f"BUDGET: ${state.budget:.2f}", True, b_col)
    ctx.screen.blit(b_surf, (rb_x, _r1))

    # Row 2 — upkeep and gross income on one measured line.
    inc_col = C_GREEN_BRIGHT if gross_income > 0 else C_GREY_MID
    draw_row(ctx, [
        (f"UPK -${total_upkeep:.0f}", C_RED),
        (f"INC +${gross_income:.0f}", inc_col),
    ], rb_x, _r2, f_mi, gap=12)

    # LEDGER / SHOP toggle button (right-aligned in block 4, row 1)
    tog_label = "[SHOP]" if getattr(ctx, "_show_ledger", False) else "[LOG]"
    tog_w     = min(72, rb_w - 6)
    tog_rect  = pygame.Rect(rb_x + rb_w - tog_w - 2, _r1, tog_w, _btn_h)
    draw_button(ctx, tog_rect, tog_label,
                lambda: setattr(ctx, "_show_ledger", not getattr(ctx, "_show_ledger", False)),
                bg_color=C_GREY_DARK, border_color=C_GREY_MID, text_color=C_GREY_LIGHT)

    # PAUSE + projected-net row: button on the left, net text to its right
    pause_w    = min(rb_w - 6, 100)
    pause_rect = pygame.Rect(rb_x, _r4, pause_w, _btn_h)
    draw_button(ctx, pause_rect, "PAUSE",
                lambda: ctx.set_screen(GameScreen.PAUSE),
                bg_color=C_GREY_DARK, border_color=C_GREY_MID, text_color=C_GREY_LIGHT)

    net_col  = C_GREEN_BRIGHT if proj_net > 0 else (C_AMBER_DIM if proj_net == 0 else C_RED)
    net_sign = "+" if proj_net >= 0 else ""
    net_surf = ctx._f("micro").render(
        f"END: {net_sign}${proj_net:.0f}/s", True, net_col
    )
    net_y = _r4 + max(0, (_btn_h - net_surf.get_height()) // 2)
    ctx.screen.blit(net_surf, (rb_x + pause_w + 6, net_y))
    ctx.screen.set_clip(_hud_clip)

    # ── AIR SEASON button (full header height, far right) ─────────────────────
    air_rect  = pygame.Rect(air_x, 4, air_w, hud_h - 8)
    has_shows = any(s for s in state.lineup if s and not s.get("is_extension"))

    def _air_season():
        if state.selected_item:
            ctx._toast("DESELECT ITEM FIRST", "warn")
            return
        if ctx.audio:
            ctx.audio.play("sfx_season")
        result = state.advance_season()
        ctx._handle_season_result(result, state)

    if has_shows:
        pulse    = 0.5 + 0.5 * math.sin(ctx._tick_ms * 0.004)
        ring_exp = int(4 + pulse * 5)
        ring_a   = int(70 + pulse * 90)
        ring_s   = pygame.Surface(
            (air_w + ring_exp * 2, hud_h - 8 + ring_exp * 2), pygame.SRCALPHA
        )
        pygame.draw.rect(ring_s, (*C_GREEN_BRIGHT, ring_a),
                         (0, 0, ring_s.get_width(), ring_s.get_height()),
                         ring_exp, border_radius=ring_exp + 4)
        ctx.screen.blit(ring_s, (air_x - ring_exp, 4 - ring_exp))
        draw_button(ctx, air_rect, ">> AIR SEASON", _air_season,
                    bg_color=C_TINT_GREEN_VIVID, border_color=C_GREEN_BRIGHT,
                    text_color=C_GREEN_BRIGHT)
    else:
        draw_button(ctx, air_rect, "ADD SHOWS", _air_season,
                    bg_color=C_GREY_DARK, border_color=C_GREY_MID, text_color=C_GREY_MID)

    # Vertical dividers between blocks
    for dx in (cl_x - gap // 2, cr_x - gap // 2, rb_x - gap // 2, air_x - 4):
        pygame.draw.line(ctx.screen, C_PANEL_BORDER, (dx, 6), (dx, hud_h - 6))

    # Restore previous clip region
    ctx.screen.set_clip(_old_clip)
