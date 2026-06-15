"""Droste — infinite self-similar recursive zoom portal.

Each frame the previous image is zoom-rotated inward (like an Escher print),
building an endlessly-receding tunnel.  Spiralling geometric shapes are
drawn on top each frame — they get swallowed into the vortex and recycled.

  Bass   → zoom depth
  Mid    → rotation speed + shape complexity
  Treble → overlay brightness
  Beat   → zoom / rotation spike
"""
import math
import random

import pygame

import config
from .base import Effect
from .utils import hsl


class Droste(Effect):
    TRAIL_ALPHA = 0
    RES_DIV     = 3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        W = config.WIDTH  // self.RES_DIV
        H = config.HEIGHT // self.RES_DIV
        self._trail  = pygame.Surface((W, H))
        self._trail.fill((0, 0, 0))
        self._hue    = random.random()
        self._rot_acc = 0.0
        self._beat_t  = 0

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

        self._hue = (self._hue + 0.003 + mid * 0.004) % 1.0

        if bass > 0.75:
            self._beat_t = 40
        self._beat_t = max(0, self._beat_t - 1)
        bt = self._beat_t / 40.0

        zoom  = 1.004 + bass * 0.006 + bt * 0.014 + mid * 0.003
        rot   = 0.20  + mid  * 0.60  + bt * 2.0
        self._rot_acc += rot * 0.016

        # Zoom-rotate feedback
        rotated = pygame.transform.rotozoom(self._trail, rot, zoom)
        rw, rh  = rotated.get_size()
        self._trail.fill((0, 0, 0))
        self._trail.blit(rotated, (-((rw - W) // 2), -((rh - H) // 2)))

        # Trail decay
        self._trail.fill((240, 238, 240), special_flags=pygame.BLEND_RGB_MULT)

        # Draw spiralling geometry each frame
        cx, cy    = W // 2, H // 2
        n_shapes  = 3 + int(mid * 3) + int(high * 2)
        for i in range(n_shapes):
            r_base = min(W, H) * (0.05 + 0.11 * (i + 1))
            ang    = self._rot_acc * (1 + i * 0.38) + i * math.tau / n_shapes
            px_    = cx + int(math.cos(ang) * r_base * 0.45)
            py_    = cy + int(math.sin(ang) * r_base * 0.45)
            h      = (self._hue + i / n_shapes * 0.6) % 1.0
            bright = 0.30 + bass * 0.28 + bt * 0.20
            size   = max(2, int(r_base * 0.15 * (1 + bass * 0.5)))
            sides  = 3 + i
            pts    = [
                (px_ + int(math.cos(ang + s / sides * math.tau) * size),
                 py_ + int(math.sin(ang + s / sides * math.tau) * size))
                for s in range(sides)
            ]
            if len(pts) >= 3:
                pygame.draw.polygon(self._trail, hsl(h, l=bright), pts)
                pygame.draw.polygon(self._trail, hsl(h, l=bright * 0.35), pts, 1)

        scaled = pygame.transform.scale(self._trail,
                                        (config.WIDTH, config.HEIGHT))
        surf.blit(scaled, (0, 0), special_flags=pygame.BLEND_RGB_MAX)
