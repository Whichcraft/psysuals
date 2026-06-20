"""Persistence of Vision — stroboscopic rotating geometric shapes in 3D.

Multiple nested polygons rotate in 3D space at subtly different speeds on
different axes. With long trail persistence, their ghost images accumulate
in perspective, creating a glowing 3D wagon-wheel moiré and holographic mandala.

  Bass   → rotation speed burst
  Mid    → number of shapes / polygon complexity
  Treble → strobe flash
  Beat   → speed spike + hue jump
"""
import math
import random

import pygame

import config
from .base import Effect
from .utils import hsl

_MAX_SHAPES = 8


class Persistence(Effect):
    TRAIL_ALPHA = 5   # very long persistence for 3D moiré build-up

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._hue = 0.0
        # Initialize 3D rotation angles for each shape
        self._rot_x = [random.uniform(0, math.tau) for _ in range(_MAX_SHAPES)]
        self._rot_y = [random.uniform(0, math.tau) for _ in range(_MAX_SHAPES)]
        self._rot_z = [random.uniform(0, math.tau) for _ in range(_MAX_SHAPES)]
        
        # Non-coplanar speed ratios for complex 3D orbital dynamics
        self._speeds_x = [0.008 * (1 + i * 0.12) for i in range(_MAX_SHAPES)]
        self._speeds_y = [0.012 * (1 + i * 0.08) for i in range(_MAX_SHAPES)]
        self._speeds_z = [0.015 * (1 + i * 0.15) for i in range(_MAX_SHAPES)]
        
        self._boost = 0.0
        self._beat_prev = 0.0

    def draw(self, surf, waveform, fft, beat, tick):
        W, H = config.WIDTH, config.HEIGHT
        bass = beat
        mid  = config.MID_ENERGY
        high = config.TREBLE_ENERGY

        self._hue = (self._hue + 0.003 + mid * 0.003) % 1.0
        self._boost = max(0.0, self._boost - 0.04)

        if bass > 0.75 and self._beat_prev <= 0.75:
            self._boost = 1.5 + bass * 1.0
        self._beat_prev = bass

        cx, cy = W // 2, H // 2
        base_r = min(W, H) * 0.38
        fov = base_r
        spd_mul = 1.0 + bass * 2.5 + self._boost

        n_shapes = max(3, min(_MAX_SHAPES, 3 + int(mid * 5)))

        for i in range(n_shapes):
            # Update 3D rotation angles
            self._rot_x[i] += self._speeds_x[i] * spd_mul
            self._rot_y[i] += self._speeds_y[i] * spd_mul
            self._rot_z[i] += self._speeds_z[i] * spd_mul

            ax, ay, az = self._rot_x[i], self._rot_y[i], self._rot_z[i]
            r = 0.25 + 0.75 * (i + 1) / n_shapes
            sides = 3 + i
            h = (self._hue + i / n_shapes * 0.55) % 1.0
            bright = 0.28 + bass * 0.25 + (high * 0.12 if i == n_shapes - 1 else 0)

            # Precompute trig values for fast rotation
            cx_cos, cx_sin = math.cos(ax), math.sin(ax)
            cy_cos, cy_sin = math.cos(ay), math.sin(ay)
            cz_cos, cz_sin = math.cos(az), math.sin(az)

            projected = []
            depths = []

            for s in range(sides):
                ang = s / sides * math.tau
                # Original point in local 3D space (Z = 0)
                vx = math.cos(ang) * r
                vy = math.sin(ang) * r
                vz = 0.0

                # 3D Rotation Matrix Multiplication (Euler sequence: X -> Y -> Z)
                # Rotate around X
                y1 = vy * cx_cos - vz * cx_sin
                z1 = vy * cx_sin + vz * cx_cos

                # Rotate around Y
                x2 = vx * cy_cos + z1 * cy_sin
                z2 = -vx * cy_sin + z1 * cy_cos

                # Rotate around Z
                x3 = x2 * cz_cos - y1 * cz_sin
                y3 = x2 * cz_sin + y1 * cz_cos
                z3 = z2

                # Camera distance and perspective projection
                cam_z = 2.2
                depth = cam_z + z3
                
                sx = cx + int(x3 * fov / depth)
                sy = cy + int(y3 * fov / depth)

                projected.append((sx, sy))
                depths.append(z3)

            # Draw edge segments with depth fading
            for s in range(sides):
                next_s = (s + 1) % sides
                p1 = projected[s]
                p2 = projected[next_s]

                # Compute depth factor (Z ranges from -r to +r, mapping to [0.15, 1.0])
                avg_z = (depths[s] + depths[next_s]) / 2.0
                d_factor = (3.2 - (2.2 + avg_z)) / 2.0
                d_factor = max(0.15, min(1.0, 0.2 + 0.8 * d_factor))

                col = hsl(h, l=bright * d_factor)
                glow = hsl(h, l=bright * 0.30 * d_factor)
                thickness = max(1, int(4 * d_factor))

                # Double-pass drawing for neon/glowing effect
                pygame.draw.line(surf, glow, p1, p2, thickness + 2)
                pygame.draw.line(surf, col, p1, p2, thickness)

        # Treble: brief radial flash ring in background
        if high > 0.50:
            flash_r = int(min(W, H) * 0.48 * high)
            pygame.draw.circle(surf, hsl(self._hue, l=0.15 * high),
                               (cx, cy), flash_r, 2)
