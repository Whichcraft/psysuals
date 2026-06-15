"""OilSlick — iridescent thin-film interference pattern.

Two families of sine waves interfere across a full-screen pixel grid,
simulating the rainbow shimmer of an oil film on water.  The interference
value maps continuously to hue, producing flowing prismatic colours.

  Bass   → radial ripple amplitude
  Mid    → spatial frequency (zoom)
  Treble → temporal shimmer speed
  Beat   → phase jump + hue shift
"""
import math

import numpy as np
import pygame
import pygame.surfarray as surfarray

import config
from .base import Effect


class OilSlick(Effect):
    TRAIL_ALPHA = 0
    RES_DIV     = 4   # full-screen pixel ops need resolution reduction

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        W = config.WIDTH  // self.RES_DIV
        H = config.HEIGHT // self.RES_DIV
        self._W, self._H = W, H
        self._surf  = pygame.Surface((W, H))
        self._t     = 0.0
        self._hue   = 0.0
        self._phase = 0.0
        # Coordinate grids (indexing='ij' → shape (W, H))
        xs = np.linspace(0, math.tau * 2, W, dtype=np.float32)
        ys = np.linspace(0, math.tau * 2, H, dtype=np.float32)
        self._X, self._Y = np.meshgrid(xs, ys, indexing='ij')
        # Radial distance grid
        cx = (W - 1) / 2.0
        cy = (H - 1) / 2.0
        xi = np.arange(W, dtype=np.float32)
        yi = np.arange(H, dtype=np.float32)
        XI, YI = np.meshgrid(xi, yi, indexing='ij')
        self._R = np.sqrt((XI - cx) ** 2 + (YI - cy) ** 2).astype(np.float32)

    def draw(self, surf, waveform, fft, beat, tick):
        W, H = self._W, self._H
        bass = beat
        mid  = config.MID_ENERGY
        high = config.TREBLE_ENERGY

        self._hue   = (self._hue   + 0.005 + mid * 0.005) % 1.0
        self._t    += 0.04 + high * 0.12 + bass * 0.06
        self._phase = (self._phase + bass * 0.5) % math.tau

        freq = 1.0 + mid * 1.5
        X    = self._X * freq
        Y    = self._Y * freq
        t    = self._t

        # Two interfering wave families
        w1 = np.sin(X +  t) * np.cos(Y * 0.7 - t * 0.8)
        w2 = (np.cos(X * 1.3 - t * 0.6 + self._phase)
              * np.sin(Y * 1.1 + t * 0.5))
        interference = (w1 + w2) * 0.5   # range ≈ -1..1

        # Radial ripple from bass
        interference += np.sin(self._R * 0.2 - t * 2.0) * bass * 0.35

        # Map to hue and lightness
        h_arr = ((interference * 0.5 + 0.5 + self._hue) % 1.0).astype(np.float32)
        l_arr = np.clip(0.15 + np.abs(interference) * 0.40 + bass * 0.12,
                        0.0, 1.0).astype(np.float32)

        r_arr = np.clip(
            (np.sin(h_arr * math.tau) * 127 + 128) * l_arr * 2,
            0, 255).astype(np.uint32)
        g_arr = np.clip(
            (np.sin((h_arr + 0.333) * math.tau) * 127 + 128) * l_arr * 2,
            0, 255).astype(np.uint32)
        b_arr = np.clip(
            (np.sin((h_arr + 0.667) * math.tau) * 127 + 128) * l_arr * 2,
            0, 255).astype(np.uint32)
        colors = (r_arr << 16) | (g_arr << 8) | b_arr

        pix = surfarray.pixels2d(self._surf)
        try:
            pix[:] = colors
        finally:
            del pix

        scaled = pygame.transform.scale(self._surf,
                                        (config.WIDTH, config.HEIGHT))
        surf.blit(scaled, (0, 0), special_flags=pygame.BLEND_RGB_MAX)
