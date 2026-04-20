from collections import deque

import numpy as np
import pygame

import config
from .utils import hsl


from .base import Effect

class GlowSquares(Effect):
    """Waterfall spectrogram — scrolling time-frequency display.

    Each new frame adds a row at the top; older slices scroll downward.
    Log-spaced frequency bins; hue = frequency position, brightness = energy.
    """

    ROWS = 100
    COLS = 80

    def __init__(self):
        self.hue   = 0.0
        n_bins     = config.BLOCK_SIZE // 2
        raw        = np.geomspace(2, int(n_bins * 0.85), self.COLS + 1).astype(int)
        self.edges = np.unique(np.clip(raw, 1, n_bins - 1))
        self.cols  = len(self.edges) - 1
        self.buf   = deque(maxlen=self.ROWS)

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue += 0.003 + beat * 0.015
        sums = np.add.reduceat(fft[:self.edges[-1]], self.edges[:-1])
        row  = sums / np.maximum(np.diff(self.edges), 1).astype(float)
        row  = row[:self.cols]
        row /= (row.max() + 1e-6)
        self.buf.appendleft(row)

        bw    = max(1, config.WIDTH  // self.cols)
        bh    = max(4, config.HEIGHT // self.ROWS)
        flash = beat * 0.35

        for ri, r in enumerate(self.buf):
            y = ri * bh
            if y > config.HEIGHT:
                break
            age     = ri / max(len(self.buf), 1)
            row_boost = flash * max(0.0, 1.0 - age * 6)
            for ci, e in enumerate(r):
                x   = ci * bw
                hue = (self.hue + ci / self.cols * 0.75) % 1.0
                lit = (1 - age * 0.7) * (0.2 + e * 0.8) + row_boost
                lit = max(0.10, lit)
                pygame.draw.rect(surf, hsl(hue, l=min(lit, 0.95)),
                                 (x, y, bw - 1, bh - 1))
