import numpy as np
import pygame

import config
from .utils import hsl


from .base import Effect

class Bars(Effect):
    """Classic spectrum bars with peak markers and a waveform overlay."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hue = 0.0
        n_bins     = config.BLOCK_SIZE // 2
        raw        = np.geomspace(2, int(n_bins * 0.85), 81).astype(int)
        self.edges = np.unique(np.clip(raw, 1, n_bins - 1))
        self.n     = len(self.edges) - 1
        self.peaks   = np.zeros(self.n)
        self.display = np.zeros(self.n)

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue += 0.003
        bar_w   = config.WIDTH // self.n
        sums    = np.add.reduceat(fft[:self.edges[-1]], self.edges[:-1])
        heights = sums / np.maximum(np.diff(self.edges), 1).astype(float)
        heights = heights[:self.n]
        heights /= (heights.max() + 1e-6)
        lerp = 0.25 + min(beat, 1.0) * 0.75
        self.display = self.display * (1.0 - lerp) + heights * lerp
        self.peaks = np.maximum(self.peaks * 0.97, self.display)

        for i, h in enumerate(self.display):
            bar_h = int(h * config.HEIGHT * 0.82)
            peak  = int(self.peaks[i] * config.HEIGHT * 0.82)
            x     = i * bar_w
            hue   = (self.hue + i / self.n) % 1.0
            pygame.draw.rect(surf, hsl(hue, l=0.38 + h * 0.42),
                             (x, config.HEIGHT - bar_h, bar_w - 2, bar_h))
            pygame.draw.rect(surf, hsl(hue, l=0.9),
                             (x, config.HEIGHT - peak - 3, bar_w - 2, 3))

        step = max(1, len(waveform) // config.WIDTH)
        pts  = [(int(i * config.WIDTH / (len(waveform) // step)),
                 int(config.HEIGHT // 2 + waveform[i * step] * 120))
                for i in range(len(waveform) // step)]
        if len(pts) > 1:
            pygame.draw.lines(surf, hsl(self.hue, l=0.75), False, pts, 2)
