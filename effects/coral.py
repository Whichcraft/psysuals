"""Coral — bioluminescent fractal coral growing from the bottom edge.

Iterative branch-tip growth produces organic upward-sweeping structures
with depth-tapered thickness and hue.  Beat fires a bioluminescent pulse
that illuminates the whole colony at once.

  Bass   → growth speed + stem length
  Mid    → branching angle spread
  Treble → tip respawn rate
  Beat   → bioluminescent bloom pulse
"""
import math
import random

import pygame

import config
from .base import Effect
from .utils import hsl

_MAX_SEGS = 600
_MAX_TIPS = 200


class Coral(Effect):
    TRAIL_ALPHA = 6

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._hue  = 0.50
        # Segments: [x1, y1, x2, y2, age, max_age, depth, hue_off]
        self._segs: list = []
        # Tips:    [x, y, angle, depth, hue_off]
        self._tips: list = []
        self._pulse     = 0.0
        self._beat_prev = 0.0
        self._reseed()

    def _reseed(self):
        W, H = config.WIDTH, config.HEIGHT
        n = 5
        self._tips = []
        for i in range(n):
            x = W * (0.10 + 0.80 * i / (n - 1)) + random.gauss(0, W * 0.04)
            y = H * 0.95
            a = -math.pi / 2 + random.gauss(0, 0.15)
            self._tips.append([x, y, a, 0, i / n * 0.30])

    def draw(self, surf, waveform, fft, beat, tick):
        W, H = config.WIDTH, config.HEIGHT
        bass = beat
        mid  = config.MID_ENERGY
        high = config.TREBLE_ENERGY

        self._hue = (self._hue + 0.002 + mid * 0.002) % 1.0

        if bass > 0.65 and self._beat_prev <= 0.65:
            self._pulse = 1.0
        self._beat_prev = bass
        self._pulse = max(0.0, self._pulse - 0.04)

        speed    = 8 + bass * 25
        spread   = 0.25 + mid * 0.35
        branch_p = 0.10 + high * 0.08
        seg_life = 200 + int(bass * 100)

        next_tips: list = []
        for tx, ty, ta, depth, h_off in self._tips:
            if depth >= 10 or ty < H * 0.05:
                continue
            ta2    = ta + random.gauss(0, spread * 0.20)
            length = max(3.0, speed * (1.0 - depth * 0.07)
                         * random.uniform(0.70, 1.30))
            ex     = tx + math.cos(ta2) * length
            ey     = ty + math.sin(ta2) * length
            if len(self._segs) < _MAX_SEGS:
                max_age = max(30, seg_life - depth * 15)
                self._segs.append(
                    [tx, ty, ex, ey, 0, max_age, depth, h_off])
            if len(next_tips) < _MAX_TIPS:
                next_tips.append([ex, ey, ta2, depth + 1, h_off])
            if (random.random() < branch_p and depth < 8
                    and len(next_tips) < _MAX_TIPS):
                b_ang = ta2 + random.choice([-1, 1]) * (
                    0.30 + random.uniform(0, spread))
                next_tips.append(
                    [ex, ey, b_ang, depth + 1, (h_off + 0.10) % 1.0])

        self._tips = next_tips
        if not self._tips:
            self._reseed()

        self._segs = [s for s in self._segs if s[4] < s[5]]
        for s in self._segs:
            s[4] += 1

        for x1, y1, x2, y2, age, max_age, depth, h_off in self._segs:
            fade   = max(0.0, 1.0 - age / max_age)
            h      = (self._hue + h_off) % 1.0
            bright = (0.18 + bass * 0.12 + self._pulse * 0.35) * fade
            lw     = max(1, 4 - depth // 3)
            pygame.draw.line(surf, hsl(h, l=bright * 0.25),
                             (int(x1), int(y1)), (int(x2), int(y2)),
                             lw * 2 + 1)
            pygame.draw.line(surf, hsl(h, l=bright),
                             (int(x1), int(y1)), (int(x2), int(y2)), lw)
