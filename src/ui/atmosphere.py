"""
atmosphere.py — NETEXEC
========================
Subtle drifting "atmosphere" haze rendered over the scene BEFORE the CRT pass,
so the CRT curves and blooms it too (Animal-Well-style ambience).

This is the dependency-free approximation sanctioned by the CRT research notes:
a few large, soft, slowly-drifting additive haze blobs rather than a full
stable-fluids solver — cheap enough to stay at 60 FPS, and gated behind a
settings toggle so low-end machines (or anyone who dislikes it) can switch it
off. Blob sprites are cached; nothing is allocated per frame on the hot path.
"""

import math

import pygame


class Atmosphere:
    """Drifting additive haze, clipped to the screen cutout."""

    # Each blob: (radius_frac, tint, x-amp_frac, y-amp_frac, speed, phase).
    # Tints are intentionally dim — additive blending over a dark UI makes even
    # faint values read clearly, so the haze stays as ambience, not discs.
    _BLOBS = [
        (0.70, (14, 40, 26), 0.20, 0.12, 0.00015, 0.0),
        (0.62, (10, 30, 40), 0.26, 0.16, 0.00021, 2.1),
        (0.66, (20, 36, 20), 0.16, 0.22, 0.00012, 4.0),
    ]

    def __init__(self):
        self._cache: dict = {}   # radius -> soft radial sprite (white, SRCALPHA)

    def _blob_sprite(self, radius: int) -> pygame.Surface:
        radius = max(8, int(radius))
        spr = self._cache.get(radius)
        if spr is None:
            spr = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            # Soft radial falloff built from a few concentric alpha rings.
            steps = 26
            for i in range(steps, 0, -1):
                rr = int(radius * i / steps)
                # Very low per-ring alpha with a gentle falloff so the blobs read
                # as faint haze, never as visible discs.
                a  = int(9 * (1 - i / steps) ** 2.2)    # brightest at centre
                if a <= 0:
                    continue
                pygame.draw.circle(spr, (255, 255, 255, a),
                                   (radius, radius), rr)
            self._cache.clear()      # only ever a handful of radii in play
            self._cache[radius] = spr
        return spr

    def draw(self, surface: pygame.Surface, rect: pygame.Rect,
             tick: int, intensity: float = 1.0) -> None:
        """Blit the drifting haze blobs additively, clipped to ``rect``."""
        if intensity <= 0:
            return
        w, h = rect.width, rect.height
        if w < 8 or h < 8:
            return
        base = min(w, h)
        prev = surface.get_clip()
        surface.set_clip(rect)
        for rfrac, tint, ax, ay, spd, ph in self._BLOBS:
            radius = int(base * rfrac)
            spr = self._blob_sprite(radius)
            # Tint a copy of the cached white sprite (multiply); scale alpha by
            # intensity so the toggle/slider can dial it down.
            tinted = spr.copy()
            tcol = (tint[0], tint[1], tint[2], max(1, int(255 * min(1.0, intensity))))
            tinted.fill(tcol, special_flags=pygame.BLEND_RGBA_MULT)
            cx = rect.centerx + int(math.sin(tick * spd + ph) * w * ax)
            cy = rect.centery + int(math.cos(tick * spd * 1.3 + ph) * h * ay)
            surface.blit(tinted, (cx - radius, cy - radius),
                         special_flags=pygame.BLEND_RGB_ADD)
        surface.set_clip(prev)
