"""Persistence of Vision — stroboscopic rotating geometric shapes.

Multiple nested polygons rotate at subtly different speeds.  With long
trail persistence their ghost images accumulate and interfere, creating
wagon-wheel moiré illusions and mandala-like kaleidoscope patterns.

  Bass   → rotation speed burst
  Mid    → number of shapes / polygon complexity
  Treble → strobe flash
  Beat   → speed spike + hue jump
"""
import math

import pygame

import config
from .base import Effect
from .utils import hsl

_MAX_SHAPES = 8


class Persistence(Effect):
    TRAIL_ALPHA = 5   # very long persistence for moiré build-up

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._hue    = 0.0
        self._angles = [i / _MAX_SHAPES * math.tau for i in range(_MAX_SHAPES)]
        # Each shape has a slightly different angular speed
        self._speeds = [0.014 * (1 + i * 0.17) for i in range(_MAX_SHAPES)]
        self._boost  = 0.0
        self._beat_prev = 0.0

    def draw(self, surf, waveform, fft, beat, tick):
        W, H = config.WIDTH, config.HEIGHT
        bass = beat
        mid  = config.MID_ENERGY
        high = config.TREBLE_ENERGY

        self._hue  = (self._hue + 0.003 + mid * 0.003) % 1.0
        self._boost = max(0.0, self._boost - 0.04)

        if bass > 0.75 and self._beat_prev <= 0.75:
            self._boost = 1.5 + bass * 1.0
        self._beat_prev = bass

        cx, cy  = W // 2, H // 2
        base_r  = min(W, H) * 0.36
        spd_mul = 1.0 + bass * 2.5 + self._boost

        n_shapes = max(3, min(_MAX_SHAPES, 3 + int(mid * 5)))

        for i in range(n_shapes):
            self._angles[i] += self._speeds[i] * spd_mul

            r     = base_r * (0.25 + 0.75 * (i + 1) / n_shapes)
            sides = 3 + i
            h     = (self._hue + i / n_shapes * 0.55) % 1.0
            bright = 0.28 + bass * 0.25 + (high * 0.12 if i == n_shapes - 1 else 0)

            pts = []
            for s in range(sides):
                a = self._angles[i] + s / sides * math.tau
                pts.append((cx + int(math.cos(a) * r),
                            cy + int(math.sin(a) * r)))

            col  = hsl(h, l=bright)
            glow = hsl(h, l=bright * 0.30)
            pygame.draw.polygon(surf, glow, pts, 4)
            pygame.draw.polygon(surf, col,  pts, 1)

        # Treble: brief radial flash ring
        if high > 0.50:
            flash_r = int(min(W, H) * 0.48 * high)
            pygame.draw.circle(surf, hsl(self._hue, l=0.15 * high),
                               (cx, cy), flash_r, 2)
