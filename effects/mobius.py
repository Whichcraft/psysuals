"""Möbius — a 3-D Möbius strip rendered with perspective projection.

The strip is drawn as a wireframe: latitude lines (constant v, varying u)
and a sparse set of longitude lines.  It rotates slowly in 3-D; beat fires
a "shiver" that briefly widens the twist.

  Bass   → rotation speed
  Mid    → roll (tilt) speed
  Treble → longitude line density
  Beat   → shiver: twist amplitude spike
"""
import math

import numpy as np
import pygame

import config
from .base import Effect
from .utils import hsl


class Mobius(Effect):
    TRAIL_ALPHA = 15

    _N_LAT  = 60    # latitude lines (parallel to the long axis)
    _N_U    = 120   # segments along u (around the strip)
    _N_LON  = 30    # longitude sample count (across strip width)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ry = 0.0   # rotation around Y
        self._rx = 0.0   # rotation around X
        self._hue    = 0.55
        self._u_off  = 0.0
        self._shiver = 0.0
        self._beat_prev = 0.0
        # Pre-compute u and v arrays
        self._u  = np.linspace(0, math.tau, self._N_U + 1, dtype=np.float32)
        self._vs = np.linspace(-0.5, 0.5, self._N_LAT, dtype=np.float32)
        self._v_lon = np.linspace(-0.5, 0.5, self._N_LON, dtype=np.float32)

    # ------------------------------------------------------------------

    def _project(self, pts3d, W, H, fov=3.0):
        """Perspective-project Nx3 → Nx2 pixel array."""
        cy, sy = math.cos(self._ry), math.sin(self._ry)
        cx, sx = math.cos(self._rx), math.sin(self._rx)

        # Rotation around Y axis
        xr = pts3d[:, 0] * cy + pts3d[:, 2] * sy
        zr = -pts3d[:, 0] * sy + pts3d[:, 2] * cy
        # Rotation around X axis
        yr  = pts3d[:, 1] * cx - zr * sx
        zr2 = pts3d[:, 1] * sx + zr * cx

        zr2 = np.where(zr2 > -fov + 0.2, zr2, -fov + 0.2)
        sc  = fov / (fov + zr2)
        half = min(W, H) * 0.42
        px  = xr * sc * half + W / 2.0
        py  = yr * sc * half + H / 2.0
        return np.stack([px, py], axis=1)

    def _strip_pts(self, u, v_scalar, twist):
        """Möbius strip 3-D coordinates for array u and scalar v."""
        hu   = u / 2.0
        cohu = np.cos(hu) * twist
        x    = (1.0 + v_scalar * cohu) * np.cos(u)
        y    = (1.0 + v_scalar * cohu) * np.sin(u)
        z    = v_scalar * np.sin(hu) * twist
        return np.stack([x, y, z], axis=1)

    def _strip_pts_v(self, u_scalar, v, twist):
        """Möbius strip 3-D coordinates for scalar u and array v."""
        hu   = u_scalar / 2.0
        x    = (1.0 + v * math.cos(hu) * twist) * math.cos(u_scalar)
        y    = (1.0 + v * math.cos(hu) * twist) * math.sin(u_scalar)
        z    = v * math.sin(hu) * twist
        return np.stack([x, y, z], axis=1)

    # ------------------------------------------------------------------

    def draw(self, surf, waveform, fft, beat, tick):
        W, H = config.WIDTH, config.HEIGHT
        bass = beat
        mid  = config.MID_ENERGY
        high = config.TREBLE_ENERGY

        self._hue   = (self._hue + 0.0012 + mid * 0.002) % 1.0
        self._ry   += 0.008 + bass * 0.025 + mid * 0.012
        self._rx   += 0.003 + bass * 0.008
        self._u_off = (self._u_off + 0.006 + high * 0.020) % math.tau

        if bass > 0.75 and self._beat_prev <= 0.75:
            self._shiver = 1.0
        self._beat_prev = bass
        self._shiver = max(0.0, self._shiver - 0.04)

        twist = 1.0 + self._shiver * 0.30 + mid * 0.15

        # Latitude lines
        u = self._u
        for i, v in enumerate(self._vs):
            pts3d = self._strip_pts(u, v, twist)
            pts2d = self._project(pts3d, W, H)
            h      = (self._hue + (v + 0.5)) % 1.0
            bright = 0.18 + abs(v) * 0.30 + bass * 0.20 + self._shiver * 0.25
            col    = hsl(h, l=bright)
            pts_i  = [(int(p[0]), int(p[1])) for p in pts2d]
            if len(pts_i) >= 2:
                pygame.draw.lines(surf, col, False, pts_i, 1)

        # Longitude lines (sparse)
        v_arr  = self._v_lon.astype(np.float32)
        stride = max(1, self._N_U // (4 + int(high * 4)))
        for i in range(0, len(u) - 1, stride):
            u_val  = float(u[i]) + self._u_off
            pts3d  = self._strip_pts_v(u_val, v_arr, twist)
            pts2d  = self._project(pts3d, W, H)
            h      = (self._hue + u_val / math.tau * 0.5) % 1.0
            bright = 0.12 + bass * 0.12 + self._shiver * 0.18
            col    = hsl(h, l=bright)
            pts_i  = [(int(p[0]), int(p[1])) for p in pts2d]
            if len(pts_i) >= 2:
                pygame.draw.lines(surf, col, False, pts_i, 1)
