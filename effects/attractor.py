import math
import random

import numpy as np
import pygame

import config
from .utils import hsl


class Attractor:
    """Mosaic wall of equilateral triangles filling the screen.

    Triangles tessellate to cover the full display.  Each has its own hue
    that drifts slowly.  On beats, random triangles pulse outward and spin;
    bass drives overall brightness.  The global hue offset shifts across the
    full palette over time, producing coordinated colour waves.
    """

    TRAIL_ALPHA = 25
    N_COLS      = 14     # triangles per row (up-pointing)
    GAP         = 0.90   # draw at 90% size → visible gap/border between tiles

    def __init__(self):
        self.hue   = 0.0
        self.tiles = []
        self._built = False

    # ------------------------------------------------------------------
    def _build_grid(self):
        tw = config.WIDTH  / self.N_COLS
        th = tw * math.sqrt(3) / 2
        n_rows = int(config.HEIGHT / th) + 2

        for r in range(n_rows):
            y_top = r * th
            y_bot = y_top + th
            for k in range(self.N_COLS + 1):
                # Up-pointing triangle ▲
                up = [
                    (k * tw + tw / 2, y_top),
                    (k * tw,          y_bot),
                    ((k + 1) * tw,    y_bot),
                ]
                self.tiles.append(self._make_tile(up))

                # Down-pointing triangle ▽ (sits between up k and up k+1)
                dn = [
                    (k * tw + tw / 2,       y_top),
                    ((k + 1) * tw + tw / 2, y_top),
                    ((k + 1) * tw,          y_bot),
                ]
                self.tiles.append(self._make_tile(dn))

        self._built = True

    def _make_tile(self, verts):
        cx = sum(v[0] for v in verts) / 3
        cy = sum(v[1] for v in verts) / 3
        return {
            "verts":   verts,
            "cx": cx,  "cy": cy,
            "hue":     random.random(),
            "hvel":    random.uniform(-0.0008, 0.0008),
            "bright":  random.uniform(0.15, 0.45),
            "rot":     0.0,
            "rot_vel": 0.0,
            "pulse":   0.0,
        }

    def _screen_verts(self, tile):
        cx, cy  = tile["cx"], tile["cy"]
        s       = (self.GAP + tile["pulse"])
        cos_r   = math.cos(tile["rot"])
        sin_r   = math.sin(tile["rot"])
        pts = []
        for vx, vy in tile["verts"]:
            dx = (vx - cx) * s
            dy = (vy - cy) * s
            pts.append((int(cx + dx * cos_r - dy * sin_r),
                        int(cy + dx * sin_r + dy * cos_r)))
        return pts

    # ------------------------------------------------------------------
    def draw(self, surf, waveform, fft, beat, tick):
        if not self._built:
            self._build_grid()

        self.hue += 0.0025
        bass = float(np.mean(fft[:6]))
        high = float(np.mean(fft[30:]))

        # Beat: activate random tiles — more on stronger beats
        if beat > 0.3:
            for _ in range(int(beat * 10)):
                t = random.choice(self.tiles)
                t["pulse"]   = random.uniform(0.10, 0.35) * min(beat, 2.0)
                t["rot_vel"] = random.choice([-1, 1]) * random.uniform(0.04, 0.14) * min(beat, 2.0)

        W, H = config.WIDTH, config.HEIGHT

        for tile in self.tiles:
            # Drift individual hue + global shift
            tile["hue"] = (tile["hue"] + tile["hvel"] + 0.0002) % 1.0

            # Decay pulse and rotation
            tile["pulse"]   *= 0.88
            tile["rot"]     += tile["rot_vel"]
            tile["rot_vel"] *= 0.91

            pts = self._screen_verts(tile)

            # Skip tiles fully off screen
            if all(p[0] < 0 or p[0] >= W or p[1] < 0 or p[1] >= H for p in pts):
                continue

            h      = (tile["hue"] + self.hue) % 1.0
            bright = min(tile["bright"] + bass * 0.28 + tile["pulse"] * 0.35
                         + high * 0.10, 0.88)

            pygame.draw.polygon(surf, hsl(h, l=bright), pts)
            # Brighter edge for the panel-border look
            pygame.draw.polygon(surf, hsl(h, l=min(bright + 0.18, 0.96)), pts, 1)
