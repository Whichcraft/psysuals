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


_N      = 4000
_FS     = 0.0022   # spatial frequency of the noise field
_LAYERS = 3        # sine layers stacked


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
            a += (np.sin(x * _FS * f + t * (0.29 + i * 0.08)) *
                  np.cos(y * _FS * f * 0.75 + t * (0.21 - i * 0.06)))
        return a * math.pi * (2.2 + bass * 1.8)

    def draw(self, surf, waveform, fft, beat, tick):
        W, H  = config.WIDTH, config.HEIGHT
        bass  = float(np.mean(fft[:6]))
        mids  = float(np.mean(fft[10:40]))
        self._hue = (self._hue + 0.0013 + bass * 0.002) % 1.0
        self._t  += 0.007 + mids * 0.010

        if beat > 0.55:
            self._t     += 0.5 + beat * 0.4   # phase jump reshapes all lines
            self._boost  = 2.0 + beat * 2.0

        self._boost = max(0.0, self._boost - 0.08)

        treble = float(np.mean(fft[100:256]))

        # Move particles along the field (wrap at edges)
        angles = self._field_angles(bass)
        spd    = 1.6 + bass * 1.4 + self._boost

        # Bass gravity: pull all particles gently toward screen centre
        attract_x = (W * 0.5 - self._px) * (bass * 0.0018)
        attract_y = (H * 0.5 - self._py) * (bass * 0.0018)

        # Treble scatter: random kick in any direction — particles disperse on hi-hats
        scatter   = treble * 3.2
        scatter_x = np.random.uniform(-scatter, scatter, _N).astype(np.float32)
        scatter_y = np.random.uniform(-scatter, scatter, _N).astype(np.float32)

        self._px = (self._px + np.cos(angles) * spd + attract_x + scatter_x) % W
        self._py = (self._py + np.sin(angles) * spd + attract_y + scatter_y) % H

        # Decay trail
        self._trail.fill((247, 247, 247), special_flags=pygame.BLEND_RGB_MULT)

        # Hue from position + global drift
        h  = (self._hue + self._px / W * 0.30 + self._py / H * 0.18) % 1.0
        # HSL → RGB (s=0.90, l=0.62, vectorised)
        s, l = 0.90, 0.62
        C    = float((1.0 - abs(2.0 * l - 1.0)) * s)
        H6   = h * 6.0
        X    = C * (1.0 - np.abs(H6 % 2.0 - 1.0))
        m    = l - C * 0.5
        hi   = H6.astype(np.int32) % 6
        Ca   = np.full(_N, C, dtype=np.float32)
        Cz   = np.zeros(_N, dtype=np.float32)
        r = np.select([hi==0, hi==1, hi==2, hi==3, hi==4],
                      [Ca, X,  Cz, Cz, X],  default=Ca) + m
        g = np.select([hi==0, hi==1, hi==2, hi==3, hi==4],
                      [X,  Ca, Ca, X,  Cz], default=Cz) + m
        b = np.select([hi==0, hi==1, hi==2, hi==3, hi==4],
                      [Cz, Cz, X,  Ca, Ca], default=X)  + m

        # Write pixels directly into trail surface
        ix  = np.clip(self._px.astype(np.int32), 0, W - 1)
        iy  = np.clip(self._py.astype(np.int32), 0, H - 1)
        arr = pygame.surfarray.pixels3d(self._trail)
        arr[ix, iy, 0] = (r * 255).clip(0, 255).astype(np.uint8)
        arr[ix, iy, 1] = (g * 255).clip(0, 255).astype(np.uint8)
        arr[ix, iy, 2] = (b * 255).clip(0, 255).astype(np.uint8)
        del arr

        surf.blit(self._trail, (0, 0))
