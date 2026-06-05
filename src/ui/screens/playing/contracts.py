"""
contracts.py — NETEXEC
======================
Contracts tab for the Acquisition Terminal (right panel): the available-offer
board (ACCEPT) plus the active-contract tracker. Rendered inside the shop's
scroll viewport by ``shop.py``'s ``_draw_right_panel`` when the CONTRACTS tab
is the active tab.

Public entry points
-------------------
  _draw_contracts_section(ctx, x, y, w, view_h, scroll, lo, state)
  _draw_contract_card(ctx, rect, ev, state, available=True)
  _draw_active_contract(ctx, rect, ev, remaining_seasons, fulfilled)
"""

import pygame

from engine.constants import (
    C_BORDER_DIM, C_GREEN_PANEL, C_GREEN_DIM, C_HOVER_PANEL,
    C_VIEWS_ACCENT, C_CYAN, C_WHITE, C_AMBER, C_RED,
    C_NET_POS, C_GREY_LIGHT, C_GREY_MID,
)
from ...theme import C_TINT_GREEN_FILL
from ...widgets import line_step

_SBAR_W = 8   # scrollbar track width (px) — must match shop.py


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
