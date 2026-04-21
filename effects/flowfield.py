"""FlowField — 4 000 particles surfing a continuously-evolving noise field.

Three layers of sine/cosine noise generate a smooth organic vector field.
Particles ride the field and paint vivid rainbow trails on a slow-fade
persistent surface.  Bass warps field intensity and particle speed; beat
fires a phase jump that instantly reshapes all flow lines.
"""
import math
import random

import numpy as np
import pygame

import config
from .base import Effect


_N      = 8000
_FS     = 0.0022   # spatial frequency of the noise field
_LAYERS = 2        # fewer layers for speed


class FlowField(Effect):
    TRAIL_ALPHA = 0   # we manage the surface

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        W, H = config.WIDTH, config.HEIGHT
        self._px    = np.random.uniform(0, W, _N).astype(np.float32)
        self._py    = np.random.uniform(0, H, _N).astype(np.float32)
        self._hue   = random.random()
        self._t     = 0.0
        self._boost = 0.0
        self._trail = pygame.Surface((W, H))
        self._trail.fill((0, 0, 0))

    def _field_angles(self, bass):
        x, y, t = self._px, self._py, self._t
        a = np.zeros(_N, dtype=np.float32)
        for i in range(_LAYERS):
            f = 1.6 ** i
            # Inline math for speed
            a += (np.sin(x * _FS * f + t * (0.29 + i * 0.08)) *
                  np.cos(y * _FS * f * 0.75 + t * (0.21 - i * 0.06)))
        return a * (math.pi * (2.2 + bass * 1.8))

    def draw(self, surf, waveform, fft, beat, tick):
        W, H  = config.WIDTH, config.HEIGHT
        bass  = float(np.mean(fft[:6]))
        mids  = float(np.mean(fft[10:40]))
        self._hue = (self._hue + 0.0013 + bass * 0.002) % 1.0
        self._t  += 0.007 + mids * 0.010

        if beat > 0.55:
            self._t     += 0.5 + beat * 0.4   # phase jump reshapes all lines
            self._boost  = 2.0 + beat * 2.0

        self._boost = max(0.0, self._boost - 0.12)

        treble = float(np.mean(fft[100:256]))

        # Move particles along the field (wrap at edges)
        angles = self._field_angles(bass)
        spd    = 1.8 + bass * 1.6 + self._boost

        # Faster update: vectorised trig
        cos_a = np.cos(angles)
        sin_a = np.sin(angles)
        
        self._px = (self._px + cos_a * spd) % W
        self._py = (self._py + sin_a * spd) % H

        # Decay trail (faster decay for clearer movement)
        self._trail.fill((240, 240, 240), special_flags=pygame.BLEND_RGB_MULT)

        # Vectorised HSL-ish colors for speed
        hx = (self._hue + self._px / W * 0.30) % 1.0
        
        # Super fast pseudo-colors
        ir = (np.sin(hx * math.tau) * 127 + 128).astype(np.uint32)
        ig = (np.sin((hx + 0.33) * math.tau) * 127 + 128).astype(np.uint32)
        ib = (np.sin((hx + 0.66) * math.tau) * 127 + 128).astype(np.uint32)
        
        colors = (ir << 16) | (ig << 8) | ib

        ix = self._px.astype(np.int32)
        iy = self._py.astype(np.int32)
        
        # PixelArray is faster for mass individual pixel setting
        pa = pygame.PixelArray(self._trail)
        # Using slice/indexing on PixelArray with numpy arrays is fast
        pa[ix, iy] = colors
        del pa

        surf.blit(self._trail, (0, 0))
