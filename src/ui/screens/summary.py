"""
summary.py — NETEXEC
=====================
Season-summary overlay (rendered on top of the game background).

Shows:
- Per-show breakdown (views, income, etc.)
- Seasonal event messages (mandate/contract results)
- Newly rolled seasonal event announcement
- Bailout modal when budget < 0 and bailouts remain
"""

import pygame

from engine.constants import (
    C_BG, C_PANEL, C_PANEL_BORDER, C_GREEN_BRIGHT, C_GREEN_DIM,
    C_AMBER, C_AMBER_DIM, C_RED, C_RED_DIM, C_WHITE, C_BORDER,
    C_CYAN, C_BLUE, C_GREY_LIGHT, C_GREY_MID, C_GREY_DARK,
    C_NET_POS, C_NET_NEG, C_VIEWS_ACCENT,
)
from ..theme import C_TINT_RED_DARK, C_TINT_BLUE_DARK
from ..screen_enum import GameScreen
from ..widgets import draw_button, draw_modal_overlay, line_step
from .base import Screen


class SummaryScreen(Screen):
    def render(self, ctx, state):
        render(ctx, state)


def render(ctx, state):
    draw_modal_overlay(ctx, alpha=200)
    s = state.last_season_summary
    if not s:
        ctx.set_screen(GameScreen.PLAYING)
        return

    # ── Bailout modal takes priority over everything else ─────────────────────
    if s.get("bailout_available"):
        _draw_bailout_modal(ctx, state, s)
        return

    cx, cy = ctx._sw // 2, ctx._sh // 2
    mw, mh = 700, 560
    modal  = pygame.Rect(cx - mw // 2, cy - mh // 2, mw, mh)
    pygame.draw.rect(ctx.screen, C_BG,          modal, border_radius=8)
    pygame.draw.rect(ctx.screen, C_GREEN_BRIGHT, modal, 2, border_radius=8)

    y    = modal.y + 10
    head = f"SEASON {s['season']} RATINGS REPORT"
    ht   = ctx._f("header").render(head, True, C_GREEN_BRIGHT)
    ctx.screen.blit(ht, ht.get_rect(center=(cx, y + 10)))
    y += 34

    lines = [
        (f"SEASON VIEWS:  {s['season_views']:,}", C_WHITE),
        (f"NET INCOME:   ${s['season_income']:+.0f}",
         C_AMBER if s["season_income"] >= 0 else C_RED),
        (f"TOTAL VIEWS:   {s['total_views']:,}", C_WHITE),
    ]
    if s.get("monopoly_genre"):
        lines.append((f"MONOPOLY:      {s['monopoly_genre']} ACTIVE", C_GREEN_BRIGHT))
    if s.get("milestone_met") is True:
        lines.append((f"MILESTONE MET! +${s.get('milestone_bonus', 0)} BONUS", C_GREEN_BRIGHT))
    elif s.get("milestone_met") is False:
        lines.append(("MILESTONE MISSED - RUN OVER", C_RED))

    _body_step = line_step(ctx._f("body"), 0.82)
    _mi_step   = line_step(ctx._f("micro"), 0.82)
    for text, col in lines:
        t = ctx._f("body").render(text, True, col)
        ctx.screen.blit(t, (modal.x + 16, y))
        y += _body_step
    y += 6

    pygame.draw.line(ctx.screen, C_BORDER, (modal.x + 8, y), (modal.right - 8, y), 1)
    y += 6

    # ── Seasonal event messages ────────────────────────────────────────────────
    messages = s.get("seasonal_event_messages", [])
    if messages:
        for msg_dict in messages[:3]:  # show at most 3 inline
            text  = msg_dict.get("text", "")
            level = msg_dict.get("level", "info")
            col   = (
                C_NET_POS  if level == "success" else
                C_RED      if level == "error"   else
                C_AMBER    if level == "warn"     else
                C_GREY_LIGHT
            )
            ms = ctx._f("micro").render(text[:90], True, col)
            ctx.screen.blit(ms, (modal.x + 10, y))
            y += _mi_step
            if y > modal.bottom - 100:
                break
        y += 4
        pygame.draw.line(ctx.screen, C_BORDER, (modal.x + 8, y), (modal.right - 8, y), 1)
        y += 6

    # ── Per-show breakdown ────────────────────────────────────────────────────
    col_hdr = ctx._f("micro").render(
        f"{'SHOW':<22} {'SLOT':<12} {'VIEWS':>6} {'AD$':>5} {'STR$':>5} {'UPK':>5} {'NET$':>6}",
        True, C_GREEN_BRIGHT,
    )
    ctx.screen.blit(col_hdr, (modal.x + 10, y))
    y += _mi_step + 2

    for bd in s.get("show_breakdowns", []):
        row_str = (
            f"{bd['name'][:20]:<22} "
            f"{bd['slot'][:10]:<12} "
            f"{bd['views']:>6} "
            f"{bd['ad_income']:>5.0f} "
            f"{bd['star_income']:>5.0f} "
            f"{bd['upkeep']:>5.0f} "
            f"{bd['net_income']:>+6.0f}"
        )
        rc = C_GREEN_BRIGHT if bd["net_income"] >= 0 else C_RED
        rt = ctx._f("micro").render(row_str, True, rc)
        ctx.screen.blit(rt, (modal.x + 10, y))
        y += _mi_step
        if y > modal.bottom - 80:
            break

    if s.get("vault_breakdowns"):
        y += 4
        vhdr = ctx._f("micro").render("VAULT RERUNS:", True, C_GREEN_DIM)
        ctx.screen.blit(vhdr, (modal.x + 10, y))
        y += _mi_step
        for vb in s["vault_breakdowns"]:
            vt = ctx._f("micro").render(
                f"  {vb['name'][:24]:<24} +{vb['views']}V  +${vb['net_income']}",
                True, C_GREEN_DIM,
            )
            ctx.screen.blit(vt, (modal.x + 10, y))
            y += _mi_step

    # ── New seasonal event announcement ───────────────────────────────────────
    new_ev = s.get("new_seasonal_event")
    if new_ev and y < modal.bottom - 90:
        y += 4
        pygame.draw.line(ctx.screen, C_BORDER, (modal.x + 8, y), (modal.right - 8, y), 1)
        y += 6
        kind      = new_ev.get("kind", "modifier")
        kind_col  = (
            C_CYAN   if kind == "modifier"  else
            C_RED    if kind == "mandate"   else
            C_VIEWS_ACCENT if kind == "contract" else
            C_AMBER
        )
        ev_hdr = ctx._f("small").render(
            f"INCOMING: {new_ev.get('name', '?')}  [{kind.upper()}]",
            True, kind_col,
        )
        ctx.screen.blit(ev_hdr, (modal.x + 10, y))
        y += line_step(ctx._f("small"), 0.82)
        if y < modal.bottom - 60:
            ev_desc = ctx._f("micro").render(
                new_ev.get("desc", "")[:95], True, C_GREY_LIGHT
            )
            ctx.screen.blit(ev_desc, (modal.x + 10, y))
            y += _mi_step
        dur = new_ev.get("duration", 1)
        dur_s = ctx._f("micro").render(
            f"Duration: {dur} season{'s' if dur > 1 else ''}  "
            f"| active next season onward",
            True, C_GREY_MID,
        )
        if y < modal.bottom - 55:
            ctx.screen.blit(dur_s, (modal.x + 10, y))

    # ── Continue / Game-over button ───────────────────────────────────────────
    status = s.get("status", "continue")
    if status in ("win", "loss"):
        ctx._gameover_state = status
        btn_rect = pygame.Rect(cx - 90, modal.bottom - 46, 180, 38)
        _final = GameScreen.WIN if status == "win" else GameScreen.GAME_OVER
        def _end(scr=_final): ctx.set_screen(scr)
        draw_button(ctx, btn_rect, "VIEW FINAL SCREEN >", _end, border_color=C_GREEN_BRIGHT)
    else:
        btn_rect = pygame.Rect(cx - 80, modal.bottom - 46, 160, 38)
        def _cont(): ctx.set_screen(GameScreen.PLAYING)
        draw_button(ctx, btn_rect, "CONTINUE >", _cont, border_color=C_GREEN_BRIGHT)


# ─── BAILOUT MODAL ────────────────────────────────────────────────────────────

def _draw_bailout_modal(ctx, state, s):
    """
    Show the bailout offer when budget < 0 and bailouts remain.
    Player picks LOAN (binding contract) or GRANT (upfront views loss).
    """
    from engine.cards import load_bailouts
    from engine.requirements import describe as desc_req

    tiers    = load_bailouts()
    tier_idx = state.bailouts_used
    tier     = tiers[tier_idx]

    cx, cy = ctx._sw // 2, ctx._sh // 2
    mw, mh = 620, 400
    modal  = pygame.Rect(cx - mw // 2, cy - mh // 2, mw, mh)
    pygame.draw.rect(ctx.screen, C_BG,    modal, border_radius=8)
    pygame.draw.rect(ctx.screen, C_RED,   modal, 2, border_radius=8)

    y = modal.y + 12
    f_hdr = ctx._f("header")
    f_bd  = ctx._f("bold")
    f_sm  = ctx._f("small")
    f_mi  = ctx._f("micro")
    _mb_bd = line_step(f_bd, 0.82)
    _mb_sm = line_step(f_sm, 0.82)
    _mb_mi = line_step(f_mi, 0.82)

    # Header
    title_s = f_hdr.render("NETWORK IN THE RED", True, C_RED)
    ctx.screen.blit(title_s, title_s.get_rect(center=(cx, y + 10)))
    y += 32

    tier_s = f_sm.render(
        f"BAILOUT {tier_idx + 1}/2 - {tier['name']}  |  Budget: ${state.budget}",
        True, C_AMBER,
    )
    ctx.screen.blit(tier_s, tier_s.get_rect(center=(cx, y)))
    y += 20

    desc_s = f_mi.render(tier.get("desc", "")[:90], True, C_GREY_LIGHT)
    ctx.screen.blit(desc_s, desc_s.get_rect(center=(cx, y)))
    y += 20

    pygame.draw.line(ctx.screen, C_RED_DIM, (modal.x + 8, y), (modal.right - 8, y))
    y += 10

    # Two side-by-side options
    half_w  = (mw - 36) // 2
    loan_r  = pygame.Rect(modal.x + 8,          y, half_w, 210)
    grant_r = pygame.Rect(modal.x + 8 + half_w + 10, y, half_w, 210)

    # Loan box
    loan_cfg = tier["loan"]
    pygame.draw.rect(ctx.screen, C_TINT_RED_DARK, loan_r, border_radius=6)
    pygame.draw.rect(ctx.screen, C_RED_DIM,     loan_r, 1, border_radius=6)

    ly = loan_r.y + 8
    ctx.screen.blit(f_bd.render(loan_cfg["name"], True, C_WHITE),
                    (loan_r.x + 6, ly)); ly += _mb_bd
    ctx.screen.blit(f_sm.render(f"+${tier['grant_amount']} BUDGET NOW", True, C_NET_POS),
                    (loan_r.x + 6, ly)); ly += _mb_sm
    req_d = desc_req(loan_cfg["requirement"])
    ctx.screen.blit(f_mi.render(f"Req: {req_d}", True, C_AMBER),
                    (loan_r.x + 6, ly)); ly += _mb_mi
    ctx.screen.blit(f_mi.render(f"Window: {loan_cfg['window_seasons']} seasons", True, C_GREY_LIGHT),
                    (loan_r.x + 6, ly)); ly += _mb_mi
    pen = loan_cfg["penalty"]
    ctx.screen.blit(f_mi.render(f"Failure: -${pen.get('budget_loss', 0)}", True, C_RED),
                    (loan_r.x + 6, ly)); ly += _mb_mi

    # Wrap description text
    desc_words = loan_cfg.get("desc", "").split()
    line = ""
    for w in desc_words:
        test = (line + " " + w).strip()
        if f_mi.size(test)[0] < half_w - 14:
            line = test
        else:
            s = f_mi.render(line, True, C_GREY_LIGHT)
            ctx.screen.blit(s, (loan_r.x + 6, ly)); ly += _mb_mi
            line = w
    if line:
        ctx.screen.blit(f_mi.render(line, True, C_GREY_LIGHT), (loan_r.x + 6, ly))

    loan_btn = pygame.Rect(loan_r.x + 8, loan_r.bottom - 32, half_w - 16, 26)
    def _loan():
        r = state.accept_bailout("loan")
        ctx._toast(r["message"], r["level"])
        s = state.last_season_summary
        if s:
            s["bailout_available"] = False

    draw_button(ctx, loan_btn, f"TAKE LOAN  +${tier['grant_amount']}", _loan,
                border_color=C_AMBER, text_color=C_AMBER)

    # Grant box
    grant_cfg = tier["grant"]
    pygame.draw.rect(ctx.screen, C_TINT_BLUE_DARK, grant_r, border_radius=6)
    pygame.draw.rect(ctx.screen, C_BLUE,        grant_r, 1, border_radius=6)

    gy = grant_r.y + 8
    ctx.screen.blit(f_bd.render(grant_cfg["name"], True, C_WHITE),
                    (grant_r.x + 6, gy)); gy += _mb_bd
    ctx.screen.blit(f_sm.render(f"+${tier['grant_amount']} BUDGET NOW", True, C_NET_POS),
                    (grant_r.x + 6, gy)); gy += _mb_sm
    ctx.screen.blit(f_mi.render(f"-{grant_cfg['views_loss']} total views (upfront)", True, C_RED),
                    (grant_r.x + 6, gy)); gy += _mb_mi
    ctx.screen.blit(f_mi.render("No ongoing contract.", True, C_GREY_LIGHT),
                    (grant_r.x + 6, gy)); gy += _mb_mi

    desc_words2 = grant_cfg.get("desc", "").split()
    line2 = ""
    for w in desc_words2:
        test = (line2 + " " + w).strip()
        if f_mi.size(test)[0] < half_w - 14:
            line2 = test
        else:
            s2 = f_mi.render(line2, True, C_GREY_LIGHT)
            ctx.screen.blit(s2, (grant_r.x + 6, gy)); gy += _mb_mi
            line2 = w
    if line2:
        ctx.screen.blit(f_mi.render(line2, True, C_GREY_LIGHT), (grant_r.x + 6, gy))

    grant_btn = pygame.Rect(grant_r.x + 8, grant_r.bottom - 32, half_w - 16, 26)
    def _grant():
        r = state.accept_bailout("grant")
        ctx._toast(r["message"], r["level"])
        su = state.last_season_summary
        if su:
            su["bailout_available"] = False

    draw_button(ctx, grant_btn, f"TAKE GRANT  -{grant_cfg['views_loss']}V", _grant,
                border_color=C_BLUE, text_color=C_BLUE)

    # Continue button (skip bailout — allowed if player prefers)
    skip_rect = pygame.Rect(cx - 70, modal.bottom - 36, 140, 28)
    def _skip():
        su = state.last_season_summary
        if su:
            su["bailout_available"] = False

    draw_button(ctx, skip_rect, "DECLINE (NO BAILOUT)", _skip,
                text_color=C_GREY_MID, border_color=C_GREY_DARK)
