"""Lattice — crystal grid of glowing nodes and beam lines.

A 14×9 grid of nodes glows according to their assigned FFT frequency bin
(bass on the left columns, treble on the right).  Thin double-stroke beams
connect adjacent nodes; beam brightness tracks local spectral energy.  On
every strong beat a shockwave ring expands outward from the centre — nodes
near the wavefront flare white.  Hue rotates slowly with a radial colour
offset (cyan at the core, violet at the edges).

  FFT bins → per-node brightness (spatial frequency map across the grid)
  Waveform / beat energy → beam brightness
  Bass → subtle whole-grid scale breath
  Beat → shockwave ring + node flare at the wavefront
"""
import math

import numpy as np
import pygame

import config
from .utils import hsl

try:
    import pygame as _pg
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

_COLS = 14
_ROWS = 9
_FFT_USE = 0.55   # fraction of FFT range mapped across the grid columns
_SHOCK_W = 22     # half-width of shockwave boost zone in pixels
_IDLE    = 0.08   # base glow when there is no audio


class Lattice:
    TRAIL_ALPHA = 20

    def __init__(self):
        W, H = config.WIDTH, config.HEIGHT
        self._hue       = 0.52          # start in cyan-blue
        self._shock_r   = 9999.0        # large = inactive
        self._shock_spd = 6.0
        self._beat_prev = 0.0
        self._scale     = 1.0
        self._svel      = 0.0

        cx = W / 2.0
        cy = H / 2.0
        self._cx = cx
        self._cy = cy
        self._max_r = math.hypot(cx, cy)

        # Grid spans 84% W × 80% H, centred
        x0 = W * 0.08
        y0 = H * 0.10
        cw = W * 0.84 / max(_COLS - 1, 1)
        ch = H * 0.80 / max(_ROWS - 1, 1)

        self._nodes: list[dict] = []
        for row in range(_ROWS):
            for col in range(_COLS):
                ox = x0 + col * cw
                oy = y0 + row * ch
                dist = math.hypot(ox - cx, oy - cy)
                # Radial hue offset: 0 at centre → 0.55 at corner
                h_off = dist / self._max_r * 0.55
                self._nodes.append({
                    'ox': ox, 'oy': oy,
                    'col': col, 'row': row,
                    'dist': dist,
                    'h_off': h_off,
                })

    def _bin(self, col: int, fft_len: int) -> int:
        return int(col / (_COLS - 1) * min(fft_len - 1,
                                            int(fft_len * _FFT_USE)))

    def draw(self, surf, waveform, fft, beat, tick):
        W, H    = config.WIDTH, config.HEIGHT
        fft_len = len(fft)
        bass    = float(np.mean(fft[:6]))
        mid     = float(np.mean(fft[6:30]))
        cx, cy  = self._cx, self._cy

        self._hue = (self._hue + 0.0025 + mid * 0.001) % 1.0

        # Beat → fire shockwave
        if beat > 0.6 and self._beat_prev <= 0.6:
            self._shock_r = 0.0
        self._beat_prev = beat
        self._shock_r  += self._shock_spd * (1.0 + bass * 2.0 + beat * 0.8)

        # Bass → subtle scale breath around centre
        self._svel += (1.0 + bass * 0.04 - self._scale) * 0.18
        self._svel *= 0.70
        self._scale  = max(0.90, min(self._scale + self._svel, 1.12))

        sc = self._scale

        # Compute per-node screen position, brightness, shock boost
        n_nodes  = len(self._nodes)
        sx_arr   = np.empty(n_nodes, dtype=np.float32)
        sy_arr   = np.empty(n_nodes, dtype=np.float32)
        bright   = np.empty(n_nodes, dtype=np.float32)

        for ni, nd in enumerate(self._nodes):
            sx = cx + (nd['ox'] - cx) * sc
            sy = cy + (nd['oy'] - cy) * sc
            sx_arr[ni] = sx
            sy_arr[ni] = sy

            energy = float(fft[self._bin(nd['col'], fft_len)]) + _IDLE
            dist   = math.hypot(sx - cx, sy - cy)
            shock  = max(0.0, 1.0 - abs(dist - self._shock_r) / _SHOCK_W)
            bright[ni] = min(energy + shock * (0.6 + bass * 0.4), 1.6)

        # ── Beams ────────────────────────────────────────────────────────────
        for row in range(_ROWS):
            for col in range(_COLS):
                ni = row * _COLS + col
                x0i = int(sx_arr[ni]); y0i = int(sy_arr[ni])
                hue = (self._hue + self._nodes[ni]['h_off']) % 1.0

                # Horizontal beam → right neighbour
                if col < _COLS - 1:
                    ni_r   = ni + 1
                    avg_b  = (bright[ni] + bright[ni_r]) * 0.5
                    if avg_b > 0.06:
                        x1 = int(sx_arr[ni_r]); y1 = int(sy_arr[ni_r])
                        lo = min(avg_b * 0.22, 0.38)
                        li = min(avg_b * 0.55, 0.80)
                        pygame.draw.line(surf, hsl(hue, l=lo), (x0i, y0i), (x1, y1), 3)
                        pygame.draw.line(surf, hsl(hue, l=li), (x0i, y0i), (x1, y1), 1)

                # Vertical beam → lower neighbour
                if row < _ROWS - 1:
                    ni_d   = ni + _COLS
                    avg_b  = (bright[ni] + bright[ni_d]) * 0.5
                    if avg_b > 0.06:
                        x1 = int(sx_arr[ni_d]); y1 = int(sy_arr[ni_d])
                        lo = min(avg_b * 0.18, 0.32)
                        li = min(avg_b * 0.48, 0.72)
                        pygame.draw.line(surf, hsl(hue, l=lo), (x0i, y0i), (x1, y1), 3)
                        pygame.draw.line(surf, hsl(hue, l=li), (x0i, y0i), (x1, y1), 1)

        # ── Nodes ────────────────────────────────────────────────────────────
        for ni, nd in enumerate(self._nodes):
            sx = int(sx_arr[ni]); sy = int(sy_arr[ni])
            hue = (self._hue + nd['h_off']) % 1.0
            b   = float(bright[ni])

            r_glow = max(3, int(5  + b * 10))
            r_core = max(1, int(2  + b * 4))

            pygame.draw.circle(surf, hsl(hue, l=min(b * 0.22, 0.38)),
                               (sx, sy), r_glow)
            pygame.draw.circle(surf, hsl(hue, l=min(b * 0.65 + 0.15, 0.92)),
                               (sx, sy), r_core)

            # Shockwave flare: white-hot ring near wavefront
            dist   = math.hypot(sx - cx, sy - cy)
            shock  = max(0.0, 1.0 - abs(dist - self._shock_r) / _SHOCK_W)
            if shock > 0.12:
                fr = max(2, int(r_core + shock * 9))
                pygame.draw.circle(surf, hsl(hue, l=min(0.88 + shock * 0.12, 1.0)),
                                   (sx, sy), fr)
