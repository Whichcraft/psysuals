import math

import numpy as np
import pygame

import config
from .utils import hsl


class Branches:
    """Recursive fractal lightning tree.

    Six neon arms radiate from screen centre, each splitting recursively to
    depth 6 (64 tips per arm).  Mid frequencies jitter branch angles live;
    bass drives trunk length; beat fires extra arms with a brightness burst.
    """

    TRAIL_ALPHA = 16
    MAX_DEPTH   = 6
    BASE_ARMS   = 6

    def __init__(self):
        self.hue  = 0.0
        self.time = 0.0
        self.beat_flash = 0.0

    # ------------------------------------------------------------------
    def _branch(self, surf, x, y, angle, length, depth,
                hue, time, mid, high, beat_flash):
        if depth == 0 or length < 1.5:
            return

        # Per-branch angle jitter driven by mid
        jitter = (math.sin(time * 2.3 + depth * 1.7 + angle) * mid * 0.55
                  + math.cos(time * 1.1 + depth * 2.9) * mid * 0.25)
        ex = x + math.cos(angle + jitter) * length
        ey = y + math.sin(angle + jitter) * length

        # Colour: trunk = bass-warm, tips = high-cool
        depth_t = depth / self.MAX_DEPTH          # 1 at trunk, 0 at tips
        h       = (hue + (1.0 - depth_t) * 0.45) % 1.0
        bright  = 0.25 + depth_t * 0.50 + high * 0.20 + beat_flash * 0.30
        lw      = max(1, depth // 2)

        pygame.draw.line(surf, hsl(h, l=bright),
                         (int(x), int(y)), (int(ex), int(ey)), lw)

        # Add a third middle branch occasionally for denser tips
        spread = math.pi / 2.8 + mid * 0.45
        ratio  = 0.64 + high * 0.08
        self._branch(surf, ex, ey, angle - spread / 2,
                     length * ratio, depth - 1,
                     hue, time, mid, high, beat_flash)
        self._branch(surf, ex, ey, angle + spread / 2,
                     length * ratio, depth - 1,
                     hue, time, mid, high, beat_flash)
        if depth == self.MAX_DEPTH:
            # Extra central branch only at trunk level — creates Y-fork at base
            self._branch(surf, ex, ey, angle,
                         length * ratio * 0.72, depth - 1,
                         hue, time, mid, high, beat_flash)

    # ------------------------------------------------------------------
    def draw(self, surf, waveform, fft, beat, tick):
        self.hue  += 0.005
        bass = float(np.mean(fft[:6]))
        mid  = float(np.mean(fft[6:30]))
        high = float(np.mean(fft[30:]))

        self.time       += 0.018 + bass * 0.04 + beat * 0.08
        self.beat_flash  = self.beat_flash * 0.75 + beat * 0.25

        cx = config.WIDTH  // 2
        cy = config.HEIGHT // 2

        # Short trunk so the first split happens close to centre
        trunk = (min(config.WIDTH, config.HEIGHT) * 0.10
                 * (1.0 + bass * 0.70 + beat * 0.40))

        # Extra arms on strong beats (up to +3)
        n_arms = self.BASE_ARMS + int(min(beat, 2.5) * 1.5)

        # Slow rotation of the whole tree
        base_rot = self.time * 0.06

        for i in range(n_arms):
            angle   = base_rot + i / n_arms * math.tau
            arm_hue = (self.hue + i / n_arms * 0.35) % 1.0
            self._branch(surf, cx, cy, angle, trunk,
                         self.MAX_DEPTH, arm_hue,
                         self.time, mid, high, self.beat_flash)
