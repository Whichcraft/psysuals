"""FlowField — 12 000+ particles surfing a continuously-evolving noise field.

Particles ride a multi-layered noise field and paint vivid rainbow trails.
Optimized for high particle count and high frame rates using NumPy surfarray vectorisation.
"""
import math
import random
import numpy as np
import pygame
import pygame.surfarray as surfarray
import config
from .base import Effect

_FS = 0.0022
_LAYERS = 2

class FlowField(Effect):
    TRAIL_ALPHA = 0 # we manage the surface

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        W, H = config.WIDTH, config.HEIGHT
        # Scale particle count dynamically based on screen area.
        # Baseline: 25000 particles for a 1920x1080 (1080p) screen.
        area = W * H
        self._n = int(max(8000, min(100000, 25000 * area / (1920 * 1080))))
        self._px = np.random.uniform(0, W, self._n).astype(np.float32)
        self._py = np.random.uniform(0, H, self._n).astype(np.float32)
        self._hue = random.random()
        self._t = 0.0
        self._boost = 0.0
        # Internal trail is always 24-bit for BLEND_RGB_MULT speed
        self._trail = pygame.Surface((W, H))
        self._trail.fill((0, 0, 0))

    def _field_angles(self, bass):
        x, y, t = self._px, self._py, self._t
        a = np.zeros(self._n, dtype=np.float32)
        for i in range(_LAYERS):
            f = 1.6 ** i
            a += (np.sin(x * _FS * f + t * (0.29 + i * 0.08)) *
                  np.cos(y * _FS * f * 0.75 + t * (0.21 - i * 0.06)))
        return a * (math.pi * (2.2 + bass * 1.8))

    def draw(self, surf, waveform, fft, beat, tick):
        W, H = config.WIDTH, config.HEIGHT
        if self._trail.get_width() != W or self._trail.get_height() != H:
            self._trail = pygame.Surface((W, H))
            self._trail.fill((0, 0, 0))
            area = W * H
            self._n = int(max(8000, min(100000, 25000 * area / (1920 * 1080))))
            self._px = np.random.uniform(0, W, self._n).astype(np.float32)
            self._py = np.random.uniform(0, H, self._n).astype(np.float32)

        bass = beat
        mid  = config.MID_ENERGY
        high = config.TREBLE_ENERGY
        
        self._hue = (self._hue + 0.0013 + bass * 0.002 + high * 0.001) % 1.0
        self._t += 0.007 + mid * 0.010 + high * 0.005

        if beat > 0.55:
            self._t += 0.5 + beat * 0.4
            self._boost = 2.0 + beat * 2.0

        self._boost = max(0.0, self._boost - 0.12)

        angles = self._field_angles(bass)
        spd = 1.8 + bass * 1.6 + mid * 1.2 + self._boost
        
        self._px = (self._px + np.cos(angles) * spd) % W
        self._py = (self._py + np.sin(angles) * spd) % H

        # Treble transient spikes push particles outward from screen center
        if high > 0.45:
            cx, cy = W / 2.0, H / 2.0
            dx = self._px - cx
            dy = self._py - cy
            dist = np.hypot(dx, dy) + 1e-5
            # Push is stronger closer to center and scales with treble intensity
            push = (high * 22.0) * (1.0 - np.minimum(dist / (min(W, H) * 0.5), 1.0))
            self._px = (self._px + (dx / dist) * push) % W
            self._py = (self._py + (dy / dist) * push) % H

        # Recycle particles that accumulate near screen edges back into a central cloud.
        # Edge margin: 8% of each dimension.
        margin_x = W * 0.08
        margin_y = H * 0.08
        on_edge = ((self._px < margin_x) | (self._px > W - margin_x) |
                   (self._py < margin_y) | (self._py > H - margin_y))
        edge_idx = np.where(on_edge)[0]
        if edge_idx.size > 0:
            # Relocate to a random position within the central 60% of the screen.
            cx_min, cx_max = W * 0.20, W * 0.80
            cy_min, cy_max = H * 0.20, H * 0.80
            self._px[edge_idx] = np.random.uniform(cx_min, cx_max, edge_idx.size).astype(np.float32)
            self._py[edge_idx] = np.random.uniform(cy_min, cy_max, edge_idx.size).astype(np.float32)

        # Decay trail (RGB mult is fast on 24-bit)
        self._trail.fill((240, 240, 240), special_flags=pygame.BLEND_RGB_MULT)

        # Fast color calc
        hx = (self._hue + self._px / W * 0.30) % 1.0
        ir = (np.sin(hx * math.tau) * 127 + 128).astype(np.uint32)
        ig = (np.sin((hx + 0.33) * math.tau) * 127 + 128).astype(np.uint32)
        ib = (np.sin((hx + 0.66) * math.tau) * 127 + 128).astype(np.uint32)
        colors = (ir << 16) | (ig << 8) | ib

        ix = np.clip(self._px.astype(np.int32), 0, W - 1)
        iy = np.clip(self._py.astype(np.int32), 0, H - 1)
        
        # NumPy vectorized pixel assignment is extremely fast
        pixels = surfarray.pixels2d(self._trail)
        try:
            pixels[ix, iy] = colors
        finally:
            del pixels

        # Force alpha 255 to ensure visibility in GL mode
        surf.blit(self._trail, (0, 0), special_flags=pygame.BLEND_RGB_MAX)
