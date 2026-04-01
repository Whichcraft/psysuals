import math

import numpy as np
import pygame

import config
from .utils import hsl


class Branches:
    """Recursive fractal lightning tree — psychedelic edition.

    Nine neon arms radiate from screen centre, each splitting recursively to
    depth 7.  Triple-fork at the trunk AND first split level creates a dense
    inner canopy.  Every segment is drawn twice (wide dim glow + bright core)
    for a neon flare effect.  Mid frequencies jitter all branch angles live;
    bass drives trunk length; beat fires extra arms with a brightness burst.
    """

    TRAIL_ALPHA = 10
    MAX_DEPTH   = 7
    BASE_ARMS   = 9

    def __init__(self):
        self.hue  = 0.0
        self.time = 0.0
        self.beat_flash = 0.0

    # ------------------------------------------------------------------
    def _branch(self, surf, x, y, angle, length, depth,
                hue, time, mid, high, beat_flash):
        if depth == 0 or length < 1.5:
            return

        # Per-branch angle jitter — two overlapping sine fields for organic feel
        jitter = (math.sin(time * 2.3 + depth * 1.7 + angle) * mid * 0.80
                  + math.cos(time * 1.1 + depth * 2.9) * mid * 0.40
                  + math.sin(time * 3.7 + angle * 2.1) * mid * 0.25)

        # Trunk segment drawn short; children still get full length
        draw_len = length * 0.15 if depth == self.MAX_DEPTH else length
        ex = x + math.cos(angle + jitter) * draw_len
        ey = y + math.sin(angle + jitter) * draw_len

        # Colour: trunk warm, tips cool, wide hue sweep across depth
        depth_t = depth / self.MAX_DEPTH
        h       = (hue + (1.0 - depth_t) * 0.80) % 1.0
        bright  = 0.28 + depth_t * 0.52 + high * 0.22 + beat_flash * 0.35
        lw      = max(1, depth // 2)

        # Neon glow: wide dim halo first, then bright core on top
        pygame.draw.line(surf, hsl(h, l=bright * 0.30),
                         (int(x), int(y)), (int(ex), int(ey)), lw * 3 + 2)
        pygame.draw.line(surf, hsl(h, l=bright),
                         (int(x), int(y)), (int(ex), int(ey)), lw)

        spread = math.pi / 2.6 + mid * 0.55
        ratio  = 0.62 + high * 0.10
        self._branch(surf, ex, ey, angle - spread / 2,
                     length * ratio, depth - 1,
                     hue, time, mid, high, beat_flash)
        self._branch(surf, ex, ey, angle + spread / 2,
                     length * ratio, depth - 1,
                     hue, time, mid, high, beat_flash)

        # Triple-fork (extra centre child) at trunk AND first split level
        if depth >= self.MAX_DEPTH - 1:
            self._branch(surf, ex, ey, angle,
                         length * ratio * 0.72, depth - 1,
                         hue, time, mid, high, beat_flash)

    # ------------------------------------------------------------------
    def draw(self, surf, waveform, fft, beat, tick):
        self.hue  += 0.012
        bass = float(np.mean(fft[:6]))
        mid  = float(np.mean(fft[6:30]))
        high = float(np.mean(fft[30:]))

        self.time       += 0.025 + bass * 0.06 + beat * 0.12
        self.beat_flash  = self.beat_flash * 0.72 + beat * 0.28

        cx = config.WIDTH  // 2
        cy = config.HEIGHT // 2

        trunk = (min(config.WIDTH, config.HEIGHT) * 0.18
                 * (1.0 + bass * 0.80 + beat * 0.50))

        # Extra arms on strong beats (up to +5)
        n_arms = self.BASE_ARMS + int(min(beat, 2.5) * 2.2)

        # Slow rotation of the whole tree; hue spread across all arms
        base_rot = self.time * 0.06

        for i in range(n_arms):
            angle   = base_rot + i / n_arms * math.tau
            arm_hue = (self.hue + i / n_arms * 0.75) % 1.0
            self._branch(surf, cx, cy, angle, trunk,
                         self.MAX_DEPTH, arm_hue,
                         self.time, mid, high, self.beat_flash)
