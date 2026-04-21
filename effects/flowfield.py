"""FlowField — 8 000 particles surfing a continuously-evolving noise field.

Particles ride a multi-layered noise field and paint vivid rainbow trails.
Optimized for high particle count and high frame rates.
"""
import math
import random
import numpy as np
import pygame
import config
from .base import Effect

_N = 8000
_FS = 0.0022
_LAYERS = 2

class FlowField(Effect):
    TRAIL_ALPHA = 0 # we manage the surface

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        W, H = config.WIDTH, config.HEIGHT
        self._px = np.random.uniform(0, W, _N).astype(np.float32)
        self._py = np.random.uniform(0, H, _N).astype(np.float32)
        self._hue = random.random()
        self._t = 0.0
        self._boost = 0.0
        # Internal trail is always 24-bit for BLEND_RGB_MULT speed
        self._trail = pygame.Surface((W, H))
        self._trail.fill((0, 0, 0))

    def _field_angles(self, bass):
        x, y, t = self._px, self._py, self._t
        a = np.zeros(_N, dtype=np.float32)
        for i in range(_LAYERS):
            f = 1.6 ** i
            a += (np.sin(x * _FS * f + t * (0.29 + i * 0.08)) *
                  np.cos(y * _FS * f * 0.75 + t * (0.21 - i * 0.06)))
        return a * (math.pi * (2.2 + bass * 1.8))

    def draw(self, surf, waveform, fft, beat, tick):
        W, H = config.WIDTH, config.HEIGHT
        bass = float(np.mean(fft[:6]))
        mids = float(np.mean(fft[10:40]))
        self._hue = (self._hue + 0.0013 + bass * 0.002) % 1.0
        self._t += 0.007 + mids * 0.010

        if beat > 0.55:
            self._t += 0.5 + beat * 0.4
            self._boost = 2.0 + beat * 2.0

        self._boost = max(0.0, self._boost - 0.12)

        angles = self._field_angles(bass)
        spd = 1.8 + bass * 1.6 + self._boost
        
        self._px = (self._px + np.cos(angles) * spd) % W
        self._py = (self._py + np.sin(angles) * spd) % H

        # Decay trail (RGB mult is fast on 24-bit)
        self._trail.fill((240, 240, 240), special_flags=pygame.BLEND_RGB_MULT)

        # Fast color calc
        hx = (self._hue + self._px / W * 0.30) % 1.0
        ir = (np.sin(hx * math.tau) * 127 + 128).astype(np.uint32)
        ig = (np.sin((hx + 0.33) * math.tau) * 127 + 128).astype(np.uint32)
        ib = (np.sin((hx + 0.66) * math.tau) * 127 + 128).astype(np.uint32)
        colors = (ir << 16) | (ig << 8) | ib

        ix = self._px.astype(np.int32)
        iy = self._py.astype(np.int32)
        
        # PixelArray is fast for individual pixel access
        pa = pygame.PixelArray(self._trail)
        for i in range(_N):
            pa[ix[i], iy[i]] = colors[i]
        del pa

        # Force alpha 255 to ensure visibility in GL mode
        surf.blit(self._trail, (0, 0), special_flags=pygame.BLEND_RGBA_MAX)
