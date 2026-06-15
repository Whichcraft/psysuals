"""Heartbeat — rhythmic pressure waves from a pulsing centre.

Each beat spawns one or more concentric rings that expand outward.
The ring outline smoothly morphs between a circle (high n_sides) and a
polygon (low n_sides) based on bass intensity at spawn time.
Multiple overlapping rings create moiré interference patterns.

  Bass   → wave speed + polygon morphing
  Mid    → propagation speed modifier
  Treble → ring shimmer
  Beat   → spawn new ring(s)
"""
import math

import pygame

import config
from .base import Effect
from .utils import hsl

_MAX_RINGS = 16
_N_PTS     = 120   # polygon resolution


class Heartbeat(Effect):
    TRAIL_ALPHA = 20

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._hue  = 0.0
        # Rings: [r, max_r, speed, intensity, hue, n_sides, phase]
        self._rings: list = []
        self._beat_prev = 0.0
        self._auto_cd   = 45

    # ------------------------------------------------------------------

    def _spawn(self, bass, offset_hue=0.0):
        if len(self._rings) >= _MAX_RINGS:
            return
        W, H   = config.WIDTH, config.HEIGHT
        max_r  = max(W, H) * 0.75
        speed  = 2.5 + bass * 4.5
        inten  = 0.60 + bass * 0.40
        hue    = (self._hue + offset_hue) % 1.0
        # n_sides: low bass → near-circle (12 sides), high bass → triangle (3)
        n_sides = max(3, 12 - int(bass * 9))
        self._rings.append([1.0, max_r, speed, inten, hue, n_sides, 0.0])

    # ------------------------------------------------------------------

    def draw(self, surf, waveform, fft, beat, tick):
        W, H = config.WIDTH, config.HEIGHT
        bass = beat
        mid  = config.MID_ENERGY
        high = config.TREBLE_ENERGY

        self._hue = (self._hue + 0.005 + mid * 0.004) % 1.0

        if bass > 0.60 and self._beat_prev <= 0.60:
            self._spawn(bass)
            if bass > 0.85:
                self._spawn(bass * 0.7, offset_hue=0.25)
        self._beat_prev = bass

        self._auto_cd -= 1
        if self._auto_cd <= 0 and len(self._rings) < 4:
            self._spawn(mid * 0.5)
            self._auto_cd = 50

        spd_mul = 1.0 + mid * 0.8
        cx, cy  = W // 2, H // 2

        live = []
        for ring in self._rings:
            ring[0] += ring[2] * spd_mul
            if ring[0] <= ring[1]:
                live.append(ring)
        self._rings = live

        for r, max_r, _spd, inten, hue, n_sides, phase in self._rings:
            fade = max(0.0, 1.0 - r / max_r) * inten
            if fade < 0.01:
                continue
            bright = 0.20 + fade * 0.50 + high * 0.12
            col    = hsl(hue, l=bright)
            glow   = hsl(hue, l=bright * 0.28)

            pts = []
            for i in range(_N_PTS):
                a       = i / _N_PTS * math.tau + phase
                # Polygon modulation: more pronounced at low n_sides
                poly_m  = math.cos(a * n_sides) * (
                    0.04 + (1 - n_sides / 12.0) * 0.14)
                r_actual = r * (1.0 + poly_m)
                pts.append((cx + int(math.cos(a) * r_actual),
                            cy + int(math.sin(a) * r_actual)))

            if len(pts) >= 3:
                lw = max(1, int(3 * fade + bass))
                pygame.draw.polygon(surf, glow, pts, lw + 3)
                pygame.draw.polygon(surf, col,  pts, lw)
