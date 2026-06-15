"""Chromatic — cascading chromatic aberration wave rings.

Each beat spawns an expanding ring that splits red, green, and blue channels
outward by a small pixel offset proportional to wave intensity, creating
prismatic rainbow halos as rings overlap and interfere.

  Bass   → wave expansion speed + intensity
  Mid    → hue drift speed
  Treble → RGB split radius (aberration amount)
  Beat   → spawn new ring
"""
import math
import random

import pygame

import config
from .base import Effect

_MAX_RINGS = 14


class Chromatic(Effect):
    TRAIL_ALPHA = 0
    RES_DIV     = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        W = config.WIDTH  // self.RES_DIV
        H = config.HEIGHT // self.RES_DIV
        self._trail = pygame.Surface((W, H))
        self._trail.fill((0, 0, 0))
        # Ring: [cx, cy, r, max_r, speed, intensity]
        self._rings: list = []
        self._hue  = 0.0
        self._t    = 0
        self._beat_prev = 0.0
        self._auto_cd   = 45

    def draw(self, surf, waveform, fft, beat, tick):
        RD   = self.RES_DIV
        W    = config.WIDTH  // RD
        H    = config.HEIGHT // RD
        bass = beat
        mid  = config.MID_ENERGY
        high = config.TREBLE_ENERGY

        if self._trail.get_width() != W or self._trail.get_height() != H:
            self._trail = pygame.Surface((W, H))
            self._trail.fill((0, 0, 0))

        self._hue = (self._hue + 0.004 + mid * 0.003) % 1.0
        self._t  += 1

        # Spawn ring on beat
        if bass > 0.60 and self._beat_prev <= 0.60:
            self._spawn(bass, W, H)
        self._beat_prev = bass

        # Auto-spawn so screen is never empty
        self._auto_cd -= 1
        if self._auto_cd <= 0 and len(self._rings) < 3:
            self._spawn(mid * 0.5, W, H)
            self._auto_cd = 55

        # Trail decay
        self._trail.fill((226, 222, 226), special_flags=pygame.BLEND_RGB_MULT)

        # Chromatic split amount driven by treble
        split = max(1, int(3 + high * 14))

        for ring in self._rings[:]:
            cx, cy, r, max_r, speed, intensity = ring
            if r > max_r:
                self._rings.remove(ring)
                continue
            ring[2] += speed + bass * 3.0

            fade   = max(0.0, 1.0 - r / max_r)
            alpha  = int(intensity * fade * 220)
            if alpha < 5:
                continue

            thick = max(1, int(3 * fade))
            ri    = max(1, int(r))

            # R (inner), G (centre), B (outer) — additive RGB separation
            pygame.draw.circle(
                self._trail, (min(255, alpha * 2), 0, 0),
                (cx, cy), max(1, ri - split), thick)
            pygame.draw.circle(
                self._trail, (0, min(255, alpha * 2), 0),
                (cx, cy), ri, thick)
            pygame.draw.circle(
                self._trail, (0, 0, min(255, alpha * 2)),
                (cx, cy), ri + split, thick)

        scaled = pygame.transform.scale(self._trail,
                                        (config.WIDTH, config.HEIGHT))
        surf.blit(scaled, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def _spawn(self, bass, W, H):
        if len(self._rings) >= _MAX_RINGS:
            return
        cx     = W // 2 + random.randint(-W // 6, W // 6)
        cy     = H // 2 + random.randint(-H // 6, H // 6)
        max_r  = math.hypot(max(cx, W - cx), max(cy, H - cy)) * 1.1
        speed  = 3.0 + bass * 5.0
        inten  = 0.5 + bass * 0.5
        self._rings.append([cx, cy, 0.0, max_r, speed, inten])
