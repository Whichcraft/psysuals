"""Mycelium — spreading fungal hyphal network.

Active tips grow outward leaving decaying filament segments behind.
New branches sprout probabilistically; beat fires a central bloom burst.

  Bass   → growth speed + filament reach
  Mid    → branching probability + angle spread
  Treble → tip respawn rate
  Beat   → explosive central bloom
"""
import math
import random

import pygame

import config
from .base import Effect
from .utils import hsl

_MAX_SEGS = 500
_MAX_TIPS = 150


class Mycelium(Effect):
    TRAIL_ALPHA = 8

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._hue = random.random()
        # Segments: [x1, y1, x2, y2, age, max_age, hue_off]
        self._segs: list = []
        # Tips: [x, y, angle, depth, hue_off]
        self._tips: list = []
        W, H = config.WIDTH, config.HEIGHT
        cx, cy = W / 2, H / 2
        self._tips = [
            [cx, cy, i / 7 * math.tau, 0, i / 7 * 0.4]
            for i in range(7)
        ]

    def draw(self, surf, waveform, fft, beat, tick):
        W, H = config.WIDTH, config.HEIGHT
        bass   = beat
        mid    = config.MID_ENERGY
        high   = config.TREBLE_ENERGY

        self._hue = (self._hue + 0.003 + mid * 0.002) % 1.0

        # Beat: bloom from center
        if bass > 0.65 and len(self._tips) < _MAX_TIPS:
            cx, cy = W / 2, H / 2
            for _ in range(int(3 + bass * 5)):
                angle = random.uniform(0, math.tau)
                self._tips.append([cx, cy, angle, 0, random.uniform(0, 0.5)])

        speed    = 12 + bass * 35
        spread   = 0.35 + mid * 0.45
        branch_p = 0.06 + high * 0.10 + mid * 0.04
        seg_life = 80 + int(bass * 40)

        next_tips: list = []
        for tx, ty, ta, depth, h_off in self._tips:
            if depth >= 14:
                continue
            ta2    = ta + random.gauss(0, spread * 0.25)
            length = speed * random.uniform(0.8, 1.6)
            ex     = tx + math.cos(ta2) * length
            ey     = ty + math.sin(ta2) * length
            if len(self._segs) < _MAX_SEGS:
                max_age = seg_life + random.randint(-20, 40)
                self._segs.append([tx, ty, ex, ey, 0, max_age, h_off])
            if 0 < ex < W and 0 < ey < H and len(next_tips) < _MAX_TIPS:
                next_tips.append([ex, ey, ta2, depth + 1, h_off])
            if (random.random() < branch_p and depth < 10
                    and len(next_tips) < _MAX_TIPS):
                b_ang = ta2 + random.choice([-1, 1]) * random.uniform(0.3, spread)
                next_tips.append([ex, ey, b_ang, depth + 1, (h_off + 0.12) % 1.0])

        self._tips = next_tips

        # Reseed when screen would go silent
        if not self._tips:
            cx, cy = W / 2, H / 2
            self._tips = [
                [cx, cy, i / 7 * math.tau, 0, i / 7 * 0.4]
                for i in range(7)
            ]

        # Age and cull segments
        self._segs = [s for s in self._segs if s[4] < s[5]]
        for s in self._segs:
            s[4] += 1

        # Draw
        for x1, y1, x2, y2, age, max_age, h_off in self._segs:
            fade = max(0.0, 1.0 - age / max_age)
            h      = (self._hue + h_off) % 1.0
            bright = (0.20 + bass * 0.15) * fade
            pygame.draw.line(surf, hsl(h, l=bright * 0.3),
                             (int(x1), int(y1)), (int(x2), int(y2)), 3)
            pygame.draw.line(surf, hsl(h, l=bright),
                             (int(x1), int(y1)), (int(x2), int(y2)), 1)
