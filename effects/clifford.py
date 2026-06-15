"""Clifford — strange attractor with audio-morphing parameters.

40 000 parallel walkers are iterated through the Clifford map each frame:
  x' = sin(a·y) - cos(b·x)
  y' = sin(c·x) - cos(d·y)

Parameters (a, b, c, d) drift slowly at rest and snap to new values on strong
beats.  Uses NumPy vectorised ops + surfarray for near-zero Python overhead.

  Bass   → parameter morph speed + point brightness
  Mid    → morph amplitude
  Treble → colour cycle speed
  Beat   → jump to new attractor parameters
"""
import math
import random

import numpy as np
import pygame
import pygame.surfarray as surfarray

import config
from .base import Effect


class Clifford(Effect):
    TRAIL_ALPHA = 0
    RES_DIV     = 2

    _N = 40_000   # parallel walkers

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        W = config.WIDTH  // self.RES_DIV
        H = config.HEIGHT // self.RES_DIV
        self._W, self._H = W, H
        self._trail = pygame.Surface((W, H))
        self._trail.fill((0, 0, 0))
        self._hue = random.random()
        self._a, self._b = np.float32(-1.4), np.float32(1.6)
        self._c, self._d = np.float32(1.0),  np.float32(0.7)
        self._ta = self._a; self._tb = self._b
        self._tc = self._c; self._td = self._d
        self._xs = np.random.uniform(-2, 2, self._N).astype(np.float32)
        self._ys = np.random.uniform(-2, 2, self._N).astype(np.float32)
        self._beat_prev = 0.0

    def _new_params(self):
        self._ta = np.float32(random.uniform(-2.0, 2.0))
        self._tb = np.float32(random.uniform(-2.0, 2.0))
        self._tc = np.float32(random.uniform(-2.0, 2.0))
        self._td = np.float32(random.uniform(-2.0, 2.0))

    def draw(self, surf, waveform, fft, beat, tick):
        RD   = self.RES_DIV
        W    = config.WIDTH  // RD
        H    = config.HEIGHT // RD
        bass = beat
        mid  = config.MID_ENERGY
        high = config.TREBLE_ENERGY

        if self._trail.get_width() != W or self._trail.get_height() != H:
            self._trail = pygame.Surface((W, H))
            self._trail.fill((0, 0, 0))

        self._hue = (self._hue + 0.002 + high * 0.003) % 1.0

        if bass > 0.8 and self._beat_prev <= 0.8:
            self._new_params()
        self._beat_prev = bass

        spd  = 0.008 + mid * 0.012 + bass * 0.006
        self._a = np.float32(self._a + (self._ta - self._a) * spd)
        self._b = np.float32(self._b + (self._tb - self._b) * spd)
        self._c = np.float32(self._c + (self._tc - self._c) * spd)
        self._d = np.float32(self._d + (self._td - self._d) * spd)

        # Vectorised Clifford map — one step for all walkers simultaneously
        xs, ys = self._xs, self._ys
        nx = np.sin(self._a * ys) - np.cos(self._b * xs)
        ny = np.sin(self._c * xs) - np.cos(self._d * ys)
        self._xs, self._ys = nx.astype(np.float32), ny.astype(np.float32)

        scale = min(W, H) * 0.24
        ix = np.clip((xs * scale + W * 0.5).astype(np.int32), 0, W - 1)
        iy = np.clip((ys * scale + H * 0.5).astype(np.int32), 0, H - 1)

        ang   = (np.arctan2(ys, xs) / math.tau + 0.5).astype(np.float32)
        h_arr = (self._hue + ang * 0.7) % 1.0
        bright = 0.40 + bass * 0.30

        r_arr = np.clip(
            (np.sin(h_arr * math.tau) * 127 + 128) * bright * 2,
            0, 255).astype(np.uint32)
        g_arr = np.clip(
            (np.sin((h_arr + 0.333) * math.tau) * 127 + 128) * bright * 2,
            0, 255).astype(np.uint32)
        b_arr = np.clip(
            (np.sin((h_arr + 0.667) * math.tau) * 127 + 128) * bright * 2,
            0, 255).astype(np.uint32)
        colors = (r_arr << 16) | (g_arr << 8) | b_arr

        self._trail.fill((228, 225, 232), special_flags=pygame.BLEND_RGB_MULT)
        pix = surfarray.pixels2d(self._trail)
        try:
            pix[ix, iy] = colors
        finally:
            del pix

        if RD > 1:
            scaled = pygame.transform.scale(self._trail,
                                            (config.WIDTH, config.HEIGHT))
            surf.blit(scaled, (0, 0), special_flags=pygame.BLEND_RGB_MAX)
        else:
            surf.blit(self._trail, (0, 0), special_flags=pygame.BLEND_RGB_MAX)
