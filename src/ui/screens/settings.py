"""
settings.py — NETEXEC
======================
Tabbed options screen:

  SETTINGS  — volume sliders, resolution, fullscreen, CRT on/off + per-effect
              CRT sliders (curvature / scanline / aberration / vignette),
              replay tutorial, apply.
  CONTROLS  — mouse + keyboard reference (badge column + description).
  RULES     — scrollable game-mechanics reference.
"""

import pygame

from engine.constants import (
    C_GREEN_BRIGHT, C_GREEN_MID, C_GREEN_DIM, C_BORDER, C_BORDER_DIM,
    C_CYAN, C_AMBER, C_WHITE, C_GREY_LIGHT, C_GREY_MID,
)
from ..screen_enum import GameScreen
from ..widgets import (
    draw_button, draw_label, draw_slider, draw_text_wrapped,
    draw_scrollbar, line_step,
)
from .base import Screen


_TABS = ["SETTINGS", "CONTROLS", "RULES"]


class SettingsScreen(Screen):
    def render(self, ctx, state):
        render(ctx, state)


def render(ctx, state):
    cx  = ctx._sw // 2
    hdr = ctx._f("header").render("OPTIONS", True, C_GREEN_BRIGHT)
    ctx.screen.blit(hdr, hdr.get_rect(center=(cx, 40)))

    return_screen = getattr(ctx, "_settings_return_screen", GameScreen.PAUSE)
    back_rect = pygame.Rect(20, 20, 100, 36)
    draw_button(ctx, back_rect, "< BACK", lambda: ctx.set_screen(return_screen))

    # ── Tab bar ───────────────────────────────────────────────────────────────
    tab = getattr(ctx, "_settings_tab", 0)
    tab_w = 150
    total_w = tab_w * len(_TABS)
    tx0 = cx - total_w // 2
    for i, label in enumerate(_TABS):
        tr = pygame.Rect(tx0 + i * tab_w, 66, tab_w - 6, 30)
        active = (i == tab)
        bg = C_GREEN_DIM if active else None
        draw_button(ctx, tr, label, lambda i=i: setattr(ctx, "_settings_tab", i),
                    bg_color=bg,
                    border_color=C_GREEN_BRIGHT if active else C_BORDER_DIM,
                    text_color=C_WHITE if active else C_GREEN_MID)

    pygame.draw.line(ctx.screen, C_BORDER, (40, 104), (ctx._sw - 40, 104), 1)

    if tab == 0:
        _tab_settings(ctx, state, cx)
    elif tab == 1:
        _tab_controls(ctx, cx)
    else:
        _tab_rules(ctx, cx)


# ─── SETTINGS TAB ──────────────────────────────────────────────────────────────

def _tab_settings(ctx, state, cx):
    from engine.constants import RESOLUTIONS

    # Left column — audio / display / tutorial.
    lx = cx - 320
    y  = 130
    draw_label(ctx, "SFX VOLUME", lx, y)
    draw_slider(ctx, pygame.Rect(lx, y + 22, 280, 16), ctx._settings_sfx_vol,
                lambda v: setattr(ctx, "_settings_sfx_vol", v))
    y += 58
    draw_label(ctx, "MUSIC VOLUME", lx, y)
    draw_slider(ctx, pygame.Rect(lx, y + 22, 280, 16), ctx._settings_music_vol,
                lambda v: setattr(ctx, "_settings_music_vol", v))
    y += 58
    draw_label(ctx, "RESOLUTION", lx, y)
    res = RESOLUTIONS[ctx._settings_res_idx % len(RESOLUTIONS)]
    ctx.screen.blit(ctx._f("body").render(f"{res[0]} x {res[1]}", True, C_GREEN_BRIGHT),
                    (lx, y + 22))
    draw_button(ctx, pygame.Rect(lx + 150, y + 18, 60, 26), "<",
                lambda: setattr(ctx, "_settings_res_idx",
                                (ctx._settings_res_idx - 1) % len(RESOLUTIONS)))
    draw_button(ctx, pygame.Rect(lx + 216, y + 18, 60, 26), ">",
                lambda: setattr(ctx, "_settings_res_idx",
                                (ctx._settings_res_idx + 1) % len(RESOLUTIONS)))
    y += 58
    fs_label = "EXIT FULLSCREEN" if ctx._fullscreen else "FULLSCREEN  (F11)"
    draw_button(ctx, pygame.Rect(lx, y, 280, 32), fs_label, ctx._toggle_fullscreen,
                border_color=C_CYAN, text_color=C_CYAN)
    y += 44
    draw_button(ctx, pygame.Rect(lx, y, 280, 32), "REPLAY TUTORIAL",
                lambda: (_replay_tutorial(ctx)),
                border_color=C_BORDER, text_color=C_GREEN_BRIGHT)

    # Right column — CRT toggle + per-effect sliders.
    rx = cx + 30
    ry = 130
    crt_on = getattr(ctx, "_crt_enabled", False)
    draw_button(ctx, pygame.Rect(rx, ry, 290, 32),
                f"CRT FILTER:  {'ON' if crt_on else 'OFF'}",
                lambda: setattr(ctx, "_crt_enabled", not getattr(ctx, "_crt_enabled", False)),
                border_color=C_CYAN if crt_on else C_BORDER,
                text_color=C_CYAN if crt_on else C_GREEN_BRIGHT)
    ry += 44
    params = ctx._crt_params
    for key, label in (("curvature", "CURVATURE"),
                       ("scanline", "SCANLINES"),
                       ("aberration", "ABERRATION"),
                       ("vignette", "VIGNETTE")):
        col = C_GREEN_MID if crt_on else C_GREY_MID
        ctx.screen.blit(ctx._f("small").render(label, True, col), (rx, ry))
        def _set(v, k=key):
            ctx._crt_params[k] = v
        draw_slider(ctx, pygame.Rect(rx, ry + 20, 290, 14), params.get(key, 0.4), _set)
        ry += 44

    atmo_on = getattr(ctx, "_atmosphere_enabled", False)
    draw_button(ctx, pygame.Rect(rx, ry, 290, 32),
                f"ATMOSPHERE:  {'ON' if atmo_on else 'OFF'}",
                lambda: setattr(ctx, "_atmosphere_enabled",
                                not getattr(ctx, "_atmosphere_enabled", False)),
                border_color=C_CYAN if atmo_on else C_BORDER,
                text_color=C_CYAN if atmo_on else C_GREEN_BRIGHT)

    # Apply & close (shared, bottom-centre).
    def _apply():
        if ctx.audio:
            ctx.audio.set_sfx_volume(ctx._settings_sfx_vol)
            ctx.audio.set_music_volume(ctx._settings_music_vol)
        r = RESOLUTIONS[ctx._settings_res_idx % len(RESOLUTIONS)]
        try:
            _gl = (pygame.OPENGL | pygame.DOUBLEBUF) if getattr(ctx, "_gl", None) else 0
            pygame.display.set_mode(r, pygame.RESIZABLE | _gl)
            ctx.screen = pygame.display.get_surface()
            if getattr(ctx, "_gl", None):
                ctx._gl.resize(ctx.screen.get_width(), ctx.screen.get_height())
        except Exception:
            pass
        ctx._toast("SETTINGS APPLIED", "success")
        ctx.set_screen(getattr(ctx, "_settings_return_screen", GameScreen.PAUSE))

    draw_button(ctx, pygame.Rect(cx - 150, ctx._sh - 60, 300, 40),
                "APPLY & CLOSE", _apply)


def _replay_tutorial(ctx):
    ctx._replay_tutorial_requested = True
    ctx._toast("TUTORIAL WILL SHOW ON NEXT GAME START", "info")


# ─── CONTROLS TAB ──────────────────────────────────────────────────────────────

_CONTROLS = [
    ("MOUSE", ""),
    ("Left click", "Select / buy / place items, press buttons"),
    ("Mouse wheel", "Scroll the shop, schedule and ledger lists"),
    ("Drag scrollbar", "Drag the thumb or click the arrows to scroll"),
    ("Right-click", "Pin a tooltip open (or Ctrl-click on laptops)"),
    ("KEYBOARD", ""),
    ("Esc", "Open pause / back out of a modal"),
    ("F11", "Toggle fullscreen"),
    ("Enter", "Confirm name entry (wildcard shows/ads)"),
]


def _tab_controls(ctx, cx):
    x = cx - 300
    y = 130
    f_bd = ctx._f("bold")
    f_sm = ctx._f("small")
    step = line_step(f_sm, 0.95)
    for key, desc in _CONTROLS:
        if desc == "":   # section heading
            ctx.screen.blit(f_bd.render(key, True, C_AMBER), (x, y))
            y += line_step(f_bd, 0.95)
            continue
        # Badge column (left) + description (right).
        kt = f_sm.render(key, True, C_CYAN)
        badge = pygame.Rect(x + 10, y, kt.get_width() + 14, kt.get_height() + 4)
        pygame.draw.rect(ctx.screen, C_BORDER_DIM, badge, 1, border_radius=3)
        ctx.screen.blit(kt, (badge.x + 7, badge.y + 2))
        ctx.screen.blit(f_sm.render(desc, True, C_GREY_LIGHT), (x + 250, y + 2))
        y += step + 6


# ─── RULES TAB (scrollable) ─────────────────────────────────────────────────────

def _rules_content(ctx):
    """Build the RULES sections with real values pulled from the game data so
    the numbers always match what the engine actually does."""
    from engine.constants import (
        MAX_ACTIVE_UPGRADES, MAX_SEASONS, TIME_SLOTS,
    )

    sections = [
        ("SLOTS & QUOTAS",
         f"Each season you fill up to {len(TIME_SLOTS)} time slots, then AIR the "
         f"season. Hit the views QUOTA at each milestone to keep your job. You "
         f"have {MAX_SEASONS} seasons; quotas rise as you go. Clear them all to win."),
        ("BUDGET & UPKEEP",
         "BUDGET (top-right) is your cash. Every scheduled show costs UPKEEP each "
         "season, and stars/ads add costs on top. Run dry and your shows still "
         "air, but you can't buy more. Watch the projected end-of-season net in "
         "the header."),
        ("THE SHOP & REROLL",
         "The right panel (ACQUISITION TERMINAL) has tabs: SHOWS, STARS, ADS, "
         "UPGRADES, EVENTS, CONTRACTS. * REROLL draws a fresh pool for a fee that "
         "rises slightly each use and resets every season; the pool also refills "
         "automatically each new season."),
        ("BUYING & PLACING",
         "Click BUY on a show to queue it, then click an empty slot to place it. "
         "Cards list BASE VIEWS, UPKEEP, STAR and AD slots. 2-SLOT shows take two "
         "adjacent slots for a big view bonus. SELL returns a partial refund "
         "(an already-aired show refunds more than an unaired Age-1 one)."),
        ("WILDCARD SHOWS & ADS",
         "Each cycle offers one WILDCARD show and ad (cyan). Buying one opens a "
         "3-step configurator: name it, pick one of three genres, then pick one "
         "of three generated abilities. Place it like any other card."),
    ]

    # Slot bonuses straight from TIME_SLOTS abilities.
    slot_txt = ".  ".join(f"{s.get('label', s.get('id'))}: {s.get('ability','')}"
                          for s in TIME_SLOTS)
    sections.append(("SLOT BONUSES & PENALTY",
                     slot_txt + ".  Every show lists its recommended slots (REC); "
                     "placing it off-slot applies a -30% views penalty that "
                     "season (a warning marker shows on the card)."))

    sections.append(("MONOPOLIES",
                     f"Fill ALL {len(TIME_SLOTS)} slots with one genre to trigger "
                     "that genre's monopoly bonus. Each genre's effect:"))

    # Per-genre monopoly lines with concrete values from the registry.
    try:
        from content.shows import get_genre_registry
        from .playing_schedule import _mono_short
        reg = get_genre_registry()
        for g, entry in reg.items():
            mono = entry.get("monopoly")
            if not mono:
                continue
            desc = mono.get("desc") or _mono_short(mono)
            sections.append((f"  {g} MONOPOLY", desc))
    except Exception:
        pass

    sections += [
        ("STARS",
         "Attach stars up to a show's STAR SLOTS. Each star has a CONDITION (e.g. "
         "a genre): meet it for the primary effect (views / income / multiplier), "
         "otherwise a weaker FALLBACK applies, often with added upkeep. PRIME TIME "
         "amplifies star view multipliers."),
        ("ADS",
         "SIGN ads up to a show's AD SLOTS. Ads pay twice: UPFRONT cash on signing "
         "plus SEASONAL income each season on air; the SIGN pill shows the net "
         "out-of-pocket. Some ads have genre/slot conditions; MORNING boosts ad "
         "income."),
        ("UPGRADES",
         f"Permanent perks applied to every show — live AND vault reruns — up to "
         f"{MAX_ACTIVE_UPGRADES} active at once. They never expire; stack "
         f"compatible ones. Some carry per-season upkeep. Read each card's EFFECT."),
        ("EVENTS (QUEUED)",
         "Buying an EVENT queues it to fire at the START of next season (shown in "
         "the left status strip). Effects include bonus views, budget injections, "
         "age resets, free rerolls and other trade-offs."),
        ("CONTRACTS & MANDATES",
         "CONTRACTS are optional deals you ACCEPT: hit the requirement within the "
         "window for a budget reward, or pay a penalty if it lapses. MANDATES are "
         "mandatory — miss them and pay an automatic fine each season. Both show "
         "in the left status strip."),
        ("SEASONAL NEWS",
         "At each season's end a SEASONAL EVENT rolls for next season. MODIFIER = "
         "passive multiplier for several seasons; MANDATE = recurring requirement "
         "or fine; CONTRACT = timed target for a reward; INSTANT = one-time effect "
         "next season."),
        ("VAULT / SYNDICATION",
         "Vault a show to earn passive rerun views each season at ~25% of normal "
         "(no upkeep); the Syndication Deal upgrade raises this to ~50%. A vaulted "
         "show's AGE FREEZES, so vault at peak age (around season 2). Only 1-slot "
         "shows fit the vault (holds two)."),
        ("BAILOUTS & PRESTIGE",
         "If your budget ends a season negative you may take up to 2 bailouts: a "
         "LOAN (cash now + a binding contract) or a GRANT (cash now, forfeiting "
         f"some total views). After the limit there's no rescue. Clearing all "
         f"{MAX_SEASONS} seasons earns prestige that carries into your next run "
         "with steeper quotas."),
        ("AGE & DECAY",
         "Shows age each season and most peak around season 2, then decay, so "
         "refresh your lineup over time."),
    ]
    return sections


def _tab_rules(ctx, cx):
    f_bd = ctx._f("bold")
    f_sm = ctx._f("small")
    view = pygame.Rect(cx - 320, 116, 640, ctx._sh - 116 - 20)
    sbar = pygame.Rect(view.right + 4, view.top, 8, view.height)
    rules = _rules_content(ctx)

    # Measure total content height for the scrollbar.
    inner_w = view.width - 16
    line_h  = line_step(f_sm, 0.95)
    total_h = 0
    for head, body in rules:
        total_h += line_step(f_bd, 1.0)
        total_h += _wrapped_line_count(body, f_sm, inner_w) * line_h + 12

    scroll = getattr(ctx, "_settings_scroll", 0)
    scroll = max(0, min(scroll, max(0, total_h - view.height)))
    ctx._settings_scroll = scroll

    old = ctx.screen.get_clip()
    ctx.screen.set_clip(view)
    y = view.y - scroll
    for head, body in rules:
        ctx.screen.blit(f_bd.render(head, True, C_GREEN_BRIGHT), (view.x, y))
        y += line_step(f_bd, 1.0)
        draw_text_wrapped(ctx.screen, body,
                          pygame.Rect(view.x + 8, y, inner_w, view.bottom - y + 200),
                          f_sm, C_GREY_LIGHT)
        y += _wrapped_line_count(body, f_sm, inner_w) * line_h + 12
    ctx.screen.set_clip(old)

    new = draw_scrollbar(ctx, sbar, total_h, view.height, scroll,
                         lambda s: setattr(ctx, "_settings_scroll", max(0, s)))
    if new != scroll:
        ctx._settings_scroll = new


def _wrapped_line_count(text: str, font, width: int) -> int:
    """Count how many wrapped lines ``text`` occupies at ``width`` (matches
    draw_text_wrapped's greedy word wrap)."""
    words = text.split()
    lines, line = 0, ""
    for w in words:
        test = (line + " " + w).strip()
        if font.size(test)[0] <= width:
            line = test
        else:
            lines += 1
            line = w
    if line:
        lines += 1
    return max(1, lines)
