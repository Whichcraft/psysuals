"""Synapse — neural-network graph with cascading signal propagation.

~55 nodes are placed in a loose ring layout and wired to their nearest
neighbours.  When a node fires it sends visible signal pulses down all
outgoing edges.  Beat triggers multi-node cascades; mid controls the
baseline auto-fire rate.

  Bass   → signal speed + node glow intensity
  Mid    → auto-fire rate
  Treble → signal colour saturation burst
  Beat   → cascade from 1-4 random nodes
"""
import math
import random

import pygame

import config
from .base import Effect
from .utils import hsl

_N_NODES       = 55
_EDGES_PER_NODE = 3


class Synapse(Effect):
    TRAIL_ALPHA = 18

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        W, H = config.WIDTH, config.HEIGHT
        self._hue = random.random()

        # Place nodes in a loose elliptical scatter
        self._nodes: list = []
        for i in range(_N_NODES):
            ang = random.uniform(0, math.tau)
            r   = random.uniform(0.10, 0.44) * min(W, H)
            x   = W / 2 + math.cos(ang) * r * (0.80 + random.uniform(0, 0.40))
            y   = H / 2 + math.sin(ang) * r * (0.60 + random.uniform(0, 0.30))
            self._nodes.append([x, y])   # [x, y]

        # Connect each node to _EDGES_PER_NODE nearest neighbours
        self._edges: list = []   # [from_i, to_i]
        for i in range(_N_NODES):
            xi, yi = self._nodes[i]
            dists  = sorted(
                [(math.hypot(self._nodes[j][0] - xi,
                             self._nodes[j][1] - yi), j)
                 for j in range(_N_NODES) if j != i])
            for _, j in dists[:_EDGES_PER_NODE]:
                self._edges.append([i, j])

        # Live signals: [edge_idx, progress 0..1, speed, hue]
        self._signals: list = []
        # Per-node glow decay
        self._glow = [0.0] * _N_NODES
        self._beat_prev  = 0.0
        self._auto_fire_cd = 30

    # ------------------------------------------------------------------

    def _fire(self, idx):
        self._glow[idx] = 1.0
        h = (self._hue + idx / _N_NODES * 0.4) % 1.0
        for ei, (fi, _) in enumerate(self._edges):
            if fi == idx:
                spd = 0.020 + random.uniform(0, 0.010)
                self._signals.append([ei, 0.0, spd, h])

    # ------------------------------------------------------------------

    def draw(self, surf, waveform, fft, beat, tick):
        W, H = config.WIDTH, config.HEIGHT
        bass = beat
        mid  = config.MID_ENERGY
        high = config.TREBLE_ENERGY

        self._hue = (self._hue + 0.003 + mid * 0.002) % 1.0

        # Beat cascade
        if bass > 0.65 and self._beat_prev <= 0.65:
            for _ in range(int(1 + bass * 3)):
                self._fire(random.randint(0, _N_NODES - 1))
        self._beat_prev = bass

        # Auto-fire
        self._auto_fire_cd -= 1
        if self._auto_fire_cd <= 0:
            self._fire(random.randint(0, _N_NODES - 1))
            self._auto_fire_cd = max(8, int(25 - mid * 15))

        # Advance signals
        spd_mul   = 1.0 + bass * 2.0
        live_sigs = []
        for sig in self._signals:
            ei, t, spd, h = sig
            t += spd * spd_mul
            sig[1] = t
            if t < 1.0:
                live_sigs.append(sig)
            else:
                self._fire(self._edges[ei][1])
        self._signals = live_sigs

        # Decay glow
        for i in range(_N_NODES):
            self._glow[i] = max(0.0, self._glow[i] - 0.035)

        # Draw edges (dim background wiring)
        for fi, ti in self._edges:
            xf, yf = self._nodes[fi]
            xt, yt = self._nodes[ti]
            h   = (self._hue + fi / _N_NODES * 0.3) % 1.0
            lum = 0.06 + self._glow[fi] * 0.14
            pygame.draw.line(surf, hsl(h, l=lum),
                             (int(xf), int(yf)), (int(xt), int(yt)), 1)

        # Draw travelling signals
        for ei, t, _, h in self._signals:
            fi, ti = self._edges[ei]
            xf, yf = self._nodes[fi]
            xt, yt = self._nodes[ti]
            sx = int(xf + (xt - xf) * t)
            sy = int(yf + (yt - yf) * t)
            bright = 0.55 + bass * 0.25 + high * 0.15
            r_px   = max(2, int(3 + bass * 2))
            pygame.draw.circle(surf, hsl(h, l=bright * 0.30),
                               (sx, sy), r_px + 3)
            pygame.draw.circle(surf, hsl(h, l=bright),
                               (sx, sy), r_px)

        # Draw nodes
        for i, (x, y) in enumerate(self._nodes):
            g = self._glow[i]
            h = (self._hue + i / _N_NODES * 0.4) % 1.0
            if g > 0.05:
                r_px = max(2, int(4 + g * 8 + bass * 4))
                pygame.draw.circle(surf, hsl(h, l=g * 0.22), (int(x), int(y)),
                                   r_px + 3)
                pygame.draw.circle(surf, hsl(h, l=g * 0.70), (int(x), int(y)),
                                   r_px)
            else:
                pygame.draw.circle(surf, hsl(h, l=0.10), (int(x), int(y)), 2)
