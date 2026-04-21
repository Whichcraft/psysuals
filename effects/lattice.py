"""Lattice — crystal grid of glowing nodes and beam lines with feedback.

A 14×9 grid of nodes glows according to their assigned FFT frequency bin.
This version uses a rotozoom feedback loop to create a trailing 'tunnel' effect.
"""
import math
import numpy as np
import pygame
import config
from .utils import hsl
from .base import Effect

_COLS = 14
_ROWS = 9
_FFT_USE = 0.55
_SHOCK_W = 22
_IDLE = 0.08

class Lattice(Effect):
    TRAIL_ALPHA = 0 # Managed by internal surface
    RES_DIV     = 3 # Render at 1/3 resolution

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        W, H = config.WIDTH // self.RES_DIV, config.HEIGHT // self.RES_DIV
        self._surf = pygame.Surface((W, H))
        self._surf.fill((0, 0, 0))
        self._hue = 0.52
        self._shock_r = 9999.0
        self._shock_spd = 6.0 / self.RES_DIV
        self._beat_prev = 0.0
        self._scale = 1.0
        self._svel = 0.0

        cx, cy = W / 2.0, H / 2.0
        self._cx, self._cy = cx, cy
        self._max_r = math.hypot(cx, cy)

        x0, y0 = W * 0.08, H * 0.10
        cw = W * 0.84 / max(_COLS - 1, 1)
        ch = H * 0.80 / max(_ROWS - 1, 1)

        self._nodes = []
        for row in range(_ROWS):
            for col in range(_COLS):
                ox = x0 + col * cw
                oy = y0 + row * ch
                dist = math.hypot(ox - cx, oy - cy)
                h_off = dist / self._max_r * 0.55
                self._nodes.append({
                    'ox': ox, 'oy': oy,
                    'col': col, 'row': row,
                    'dist': dist,
                    'h_off': h_off,
                })

    def _bin(self, col: int, fft_len: int) -> int:
        return int(col / (_COLS - 1) * min(fft_len - 1, int(fft_len * _FFT_USE)))

    def draw(self, surf, waveform, fft, beat, tick):
        W, H = config.WIDTH // self.RES_DIV, config.HEIGHT // self.RES_DIV
        fft_len = len(fft)
        bass = float(np.mean(fft[:6]))
        mid = float(np.mean(fft[6:30]))
        cx, cy = self._cx, self._cy

        self._hue = (self._hue + 0.0025 + mid * 0.001) % 1.0

        if beat > 0.6 and self._beat_prev <= 0.6:
            self._shock_r = 0.0
        self._beat_prev = beat
        self._shock_r += self._shock_spd * (1.0 + bass * 2.0 + beat * 0.8)

        self._svel += (1.0 + bass * 0.04 - self._scale) * 0.18
        self._svel *= 0.70
        self._scale = max(0.90, min(self._scale + self._svel, 1.12))

        # Feedback loop at lower res
        rotated = pygame.transform.rotozoom(self._surf, 0.5 + beat * 2.0, 1.0 + bass * 0.01)
        rw, rh = rotated.get_size()
        self._surf.fill((0, 0, 0))
        self._surf.blit(rotated, (-((rw - W) // 2), -((rh - H) // 2)))
        self._surf.fill((230, 230, 230), special_flags=pygame.BLEND_RGB_MULT)

        sc = self._scale
        sx_arr = np.empty(len(self._nodes), dtype=np.float32)
        sy_arr = np.empty(len(self._nodes), dtype=np.float32)
        bright = np.empty(len(self._nodes), dtype=np.float32)

        for ni, nd in enumerate(self._nodes):
            sx = cx + (nd['ox'] - cx) * sc
            sy = cy + (nd['oy'] - cy) * sc
            sx_arr[ni], sy_arr[ni] = sx, sy
            energy = float(fft[self._bin(nd['col'], fft_len)]) + _IDLE
            dist = math.hypot(sx - cx, sy - cy)
            shock = max(0.0, 1.0 - abs(dist - self._shock_r) / (_SHOCK_W / self.RES_DIV))
            bright[ni] = min(energy + shock * (0.6 + bass * 0.4), 1.6)

        # Draw Beams
        for row in range(_ROWS):
            for col in range(_COLS):
                ni = row * _COLS + col
                hue = (self._hue + self._nodes[ni]['h_off']) % 1.0
                if col < _COLS - 1:
                    ni_r = ni + 1
                    avg_b = (bright[ni] + bright[ni_r]) * 0.5
                    if avg_b > 0.1:
                        pygame.draw.line(self._surf, hsl(hue, l=min(avg_b * 0.4, 0.7)),
                                         (int(sx_arr[ni]), int(sy_arr[ni])),
                                         (int(sx_arr[ni_r]), int(sy_arr[ni_r])), 1)
                if row < _ROWS - 1:
                    ni_d = ni + _COLS
                    avg_b = (bright[ni] + bright[ni_d]) * 0.5
                    if avg_b > 0.1:
                        pygame.draw.line(self._surf, hsl(hue, l=min(avg_b * 0.4, 0.7)),
                                         (int(sx_arr[ni]), int(sy_arr[ni])),
                                         (int(sx_arr[ni_d]), int(sy_arr[ni_d])), 1)

        # Draw Nodes
        for ni, nd in enumerate(self._nodes):
            b = float(bright[ni])
            if b > 0.15:
                hue = (self._hue + nd['h_off']) % 1.0
                r = max(1, int(2 + b * 5))
                pygame.draw.circle(self._surf, hsl(hue, l=min(b * 0.6 + 0.15, 0.95)),
                                   (int(sx_arr[ni]), int(sy_arr[ni])), r)

        if self.RES_DIV > 1:
            scaled = pygame.transform.scale(self._surf, (config.WIDTH, config.HEIGHT))
            surf.blit(scaled, (0, 0), special_flags=pygame.BLEND_RGBA_MAX)
        else:
            surf.blit(self._surf, (0, 0), special_flags=pygame.BLEND_RGBA_MAX)
