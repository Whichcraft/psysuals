"""
RhythmicParticles — qwen2.5:14b concept.

Batch rendering via numpy arrays (qwen's skeleton fixed and completed):
- Particle state stored as parallel numpy float32 arrays (vectorised update).
- pygame.draw.circle replaced with pre-rendered circle blit cache keyed by
  radius — avoids repeated Surface allocation per frame.
- Dead-particle compaction done with numpy boolean indexing.
"""

import math

import numpy as np
import pygame

import config
from effects.utils import hsl

_TWO_PI   = math.pi * 2.0
_MAX      = 3000          # hard cap on live particles
_CACHE: dict[int, pygame.Surface] = {}   # radius -> white-circle SRCALPHA Surface


def _circle_surf(radius: int) -> pygame.Surface:
    """Return a cached white circle Surface of given radius."""
    if radius not in _CACHE:
        d = radius * 2 + 2
        s = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 255, 255, 220), (radius, radius), radius)
        _CACHE[radius] = s
    return _CACHE[radius]


class RhythmicParticles:
    TRAIL_ALPHA = 18

    def __init__(self):
        # Parallel numpy arrays — preallocated to _MAX
        self._xs    = np.empty(_MAX, np.float32)
        self._ys    = np.empty(_MAX, np.float32)
        self._vxs   = np.empty(_MAX, np.float32)
        self._vys   = np.empty(_MAX, np.float32)
        self._ages  = np.empty(_MAX, np.int32)
        self._lifes = np.empty(_MAX, np.int32)
        self._hues  = np.empty(_MAX, np.float32)
        self._sizes = np.empty(_MAX, np.float32)
        self._n     = 0          # number of live particles

        self._hue       = 0.0
        self._beat_prev = 0.0

    # ── spawn ────────────────────────────────────────────────────────────────

    def _spawn(self, n: int, cx=None, cy=None, speed_scale: float = 1.0):
        n = min(n, _MAX - self._n)
        if n <= 0:
            return
        W, H   = config.WIDTH, config.HEIGHT
        angles = np.random.uniform(0, _TWO_PI, n).astype(np.float32)
        speeds = (np.random.uniform(1.5, 4.5, n) * speed_scale).astype(np.float32)
        i      = self._n
        self._xs[i:i+n]    = cx if cx is not None else np.random.uniform(0, W, n)
        self._ys[i:i+n]    = cy if cy is not None else np.random.uniform(0, H, n)
        self._vxs[i:i+n]   = np.cos(angles) * speeds
        self._vys[i:i+n]   = np.sin(angles) * speeds
        self._ages[i:i+n]  = 0
        self._lifes[i:i+n] = np.random.randint(60, 130, n)
        self._hues[i:i+n]  = (self._hue + np.random.uniform(-0.08, 0.08, n)) % 1.0
        self._sizes[i:i+n] = np.random.uniform(2.0, 5.0, n).astype(np.float32)
        self._n += n

    # ── draw ─────────────────────────────────────────────────────────────────

    def draw(self, surf, waveform, fft, beat, tick):
        W, H   = config.WIDTH, config.HEIGHT
        mid    = config.MID_ENERGY
        treble = config.TREBLE_ENERGY

        # Drift hue with mid energy
        self._hue = (self._hue + 0.001 + mid * 0.003) % 1.0

        # Trickle spawn — treble drives rate (2–12/frame)
        self._spawn(int(2 + treble * 10))

        # Beat burst on rising edge
        if beat > 1.2 and self._beat_prev <= 1.2:
            self._spawn(int(30 + beat * 40),
                        cx=W / 2, cy=H / 2,
                        speed_scale=beat * 0.8)
        self._beat_prev = beat

        n = self._n
        if n == 0:
            return

        # ── vectorised update ────────────────────────────────────────────────
        speed_mult = np.float32(1.0 + beat * 0.5)
        self._xs[:n]   = (self._xs[:n]   + self._vxs[:n] * speed_mult) % W
        self._ys[:n]   = (self._ys[:n]   + self._vys[:n] * speed_mult) % H
        self._ages[:n] += 1

        # Compact — keep only alive particles
        alive = self._ages[:n] < self._lifes[:n]
        na    = int(alive.sum())
        if na < n:
            for arr in (self._xs, self._ys, self._vxs, self._vys,
                        self._ages, self._lifes, self._hues, self._sizes):
                arr[:na] = arr[:n][alive]
        self._n = na
        n = na
        if n == 0:
            return

        # Pre-compute per-particle render properties
        t      = self._ages[:n] / self._lifes[:n]            # float32 array
        alphas = (255 * (1.0 - t)).astype(np.uint8)
        radii  = np.maximum(1, (self._sizes[:n] * (1.0 - t * 0.5))).astype(np.int32)
        hues   = (self._hues[:n] + t * 0.15) % 1.0

        # ── blit-cache draw ──────────────────────────────────────────────────
        for i in range(n):
            r, g, b = hsl(float(hues[i]), 0.9, 0.55)
            rad     = int(radii[i])
            base    = _circle_surf(rad)
            colored = base.copy()
            # Tint white circle to particle colour
            colored.fill((r, g, b, int(alphas[i])), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(colored, (int(self._xs[i]) - rad, int(self._ys[i]) - rad))
