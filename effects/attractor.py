import math
from collections import deque

import numpy as np
import pygame

import config
from .utils import hsl


class Attractor:
    """Lorenz strange attractor — single particle traces the chaotic butterfly.

    A dedicated slow-fade surface accumulates the full trajectory shape over
    time so the iconic double-wing is always visible.  Audio modulates the
    Lorenz parameters in real-time, deforming the wings live.
    """

    TRAIL_ALPHA = 20          # main surface fade (normal)
    _ATTR_FADE  = 4           # attractor surface fade — very slow → full shape visible

    # Lorenz baseline parameters
    _SIGMA0 = 10.0
    _RHO0   = 28.0
    _BETA   = 8.0 / 3.0

    # Steps per frame — more steps = faster trajectory buildup
    _STEPS  = 12
    _DT     = 0.007

    def __init__(self):
        self.hue      = 0.0
        self.ry       = 0.0    # view rotation around Y
        self.rx       = 0.0    # view rotation around X (adds 3-D tumble)
        self.rho_kick = 0.0    # extra rho from beats (decays each frame)
        # Seed near the attractor
        self.x, self.y, self.z = 0.1, 0.0, 25.0
        self.attr_surf  = None
        self._attr_fade = None

    def _init_surf(self):
        self.attr_surf  = pygame.Surface((config.WIDTH, config.HEIGHT))
        self.attr_surf.fill((0, 0, 0))
        self._attr_fade = pygame.Surface((config.WIDTH, config.HEIGHT))
        self._attr_fade.set_alpha(self._ATTR_FADE)
        self._attr_fade.fill((0, 0, 0))

    def _step(self, sigma, rho):
        dt = self._DT
        dx = sigma * (self.y - self.x)
        dy = self.x * (rho - self.z) - self.y
        dz = self.x * self.y - self._BETA * self.z
        self.x += dx * dt
        self.y += dy * dt
        self.z += dz * dt
        # Reset if particle escapes (rare but possible under heavy audio mod)
        if abs(self.x) > 80 or abs(self.y) > 80 or abs(self.z) > 80:
            self.x, self.y, self.z = 0.1, 0.0, 25.0

    def _project(self, x3, y3, z3):
        """Orthographic projection with dual-axis rotation for 3-D tumble.

        Returns (sx, sy, depth) where depth is the post-rotation Z used for
        brightness depth-cueing.  Coordinates are clamped to the screen so
        the attractor never leaves the visible area.
        """
        # Rotate around Y axis
        cos_y, sin_y = math.cos(self.ry), math.sin(self.ry)
        xr =  x3 * cos_y + z3 * sin_y
        yr =  y3
        zr = -x3 * sin_y + z3 * cos_y

        # Rotate around X axis
        cos_x, sin_x = math.cos(self.rx), math.sin(self.rx)
        yr2 =  yr * cos_x - zr * sin_x
        zr2 =  yr * sin_x + zr * cos_x

        # Scale to fit attractor (max extent ~±35 units) within the screen
        scale = min(config.WIDTH, config.HEIGHT) / 80.0
        sx = int(xr  * scale + config.WIDTH  / 2)
        sy = int(yr2 * scale + config.HEIGHT / 2)

        # Hard clamp — trajectory stays fully on screen
        sx = max(0, min(config.WIDTH  - 1, sx))
        sy = max(0, min(config.HEIGHT - 1, sy))
        return sx, sy, zr2

    def draw(self, surf, waveform, fft, beat, tick):
        if self.attr_surf is None:
            self._init_surf()

        self.hue += 0.004
        bass = float(np.mean(fft[:6]))
        mid  = float(np.mean(fft[6:30]))
        high = float(np.mean(fft[30:]))

        sigma = self._SIGMA0 + bass * 5.0
        self.rho_kick  = self.rho_kick * 0.92 + beat * 12.0
        rho   = self._RHO0 + self.rho_kick

        # Dual-axis rotation: Y spins the butterfly, X tilts it — gives 3-D tumble
        self.ry += 0.004 + bass * 0.012
        self.rx += 0.0017 + bass * 0.005   # slower X tilt

        # Fade the attractor surface (very slowly)
        self.attr_surf.blit(self._attr_fade, (0, 0))

        # Step and draw new trajectory segments
        prev_sx, prev_sy, _ = self._project(self.x, self.y, self.z - 25.0)
        for i in range(self._STEPS):
            self._step(sigma, rho)
            sx, sy, depth = self._project(self.x, self.y, self.z - 25.0)

            # Colour by z position; depth-cue brightness so far points are dimmer
            z_norm   = (self.z - 5.0) / 40.0
            h        = (self.hue + z_norm * 0.55) % 1.0
            depth_t  = max(0.0, min(1.0, (depth + 30.0) / 60.0))  # 0=far, 1=near
            bright   = 0.28 + depth_t * 0.35 + high * 0.25 + beat * 0.15

            pygame.draw.line(self.attr_surf, hsl(h, l=bright),
                             (prev_sx, prev_sy), (sx, sy), 1)
            prev_sx, prev_sy = sx, sy

        # Composite — additive blend so black background is transparent
        surf.blit(self.attr_surf, (0, 0), special_flags=pygame.BLEND_ADD)
