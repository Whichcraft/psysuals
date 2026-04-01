import math
import random

import numpy as np
import pygame

import config
from .utils import hsl


class Attractor:
    """Triangle mosaic wall.

    All triangles are wireframe with rainbow edges.  Only 4-6 tiles are
    filled with colour at any time; the set rotates slowly.  A small pool
    of "active" tiles pops to the front (drawn last, scaled up), spins and
    pulses to the music, then eases back into the wall.
    """

    TRAIL_ALPHA  = 28
    N_COLS       = 14
    GAP          = 0.88   # normal draw size (leaves a visible border)
    N_FILLED     = 5      # how many tiles have a colour fill at once
    N_ACTIVE_MAX = 2      # max simultaneously active/front tiles

    def __init__(self):
        self.hue        = 0.0
        self.tiles      = []
        self.filled_ids = []   # indices of currently filled tiles
        self.active_ids = []   # indices of currently active/front tiles
        self._built     = False
        self._swap_cd   = 0    # countdown to next filled-tile swap

    # ------------------------------------------------------------------
    def _build_grid(self):
        tw = config.WIDTH  / self.N_COLS
        th = tw * math.sqrt(3) / 2
        n_rows = int(config.HEIGHT / th) + 2

        for r in range(n_rows):
            y_top = r * th
            y_bot = y_top + th
            for k in range(self.N_COLS + 1):
                up = [
                    (k * tw + tw / 2, y_top),
                    (k * tw,          y_bot),
                    ((k + 1) * tw,    y_bot),
                ]
                self.tiles.append(self._make_tile(up))
                dn = [
                    (k * tw + tw / 2,       y_top),
                    ((k + 1) * tw + tw / 2, y_top),
                    ((k + 1) * tw,          y_bot),
                ]
                self.tiles.append(self._make_tile(dn))

        # Seed initial filled set from on-screen tiles
        on_screen = [i for i, t in enumerate(self.tiles) if self._on_screen(t)]
        self.filled_ids = random.sample(on_screen, min(self.N_FILLED, len(on_screen)))
        self._built = True

    def _make_tile(self, verts):
        cx = sum(v[0] for v in verts) / 3
        cy = sum(v[1] for v in verts) / 3
        return {
            "verts":   verts,
            "cx": cx,  "cy": cy,
            "hue":     random.random(),
            "hvel":    random.uniform(-0.0006, 0.0006),
            "bright":  random.uniform(0.18, 0.42),
            "rot":     0.0,
            "rot_vel": 0.0,
            "scale":   1.0,          # 1.0 = resting; >1 = popped to front
            "svel":    0.0,
        }

    def _on_screen(self, tile):
        W, H = config.WIDTH, config.HEIGHT
        return 0 <= tile["cx"] < W and 0 <= tile["cy"] < H

    def _screen_verts(self, tile):
        cx, cy  = tile["cx"], tile["cy"]
        s       = self.GAP * tile["scale"]
        cos_r   = math.cos(tile["rot"])
        sin_r   = math.sin(tile["rot"])
        return [(int(cx + ((vx - cx) * s) * cos_r - ((vy - cy) * s) * sin_r),
                 int(cy + ((vx - cx) * s) * sin_r + ((vy - cy) * s) * cos_r))
                for vx, vy in tile["verts"]]

    def _rainbow_edges(self, surf, pts, lw=1):
        """Draw each edge with its own rainbow hue based on its angle."""
        for i in range(3):
            a = pts[i]
            b = pts[(i + 1) % 3]
            angle = math.atan2(b[1] - a[1], b[0] - a[0])
            h = (self.hue * 2 + angle / math.tau + 0.5) % 1.0
            pygame.draw.line(surf, hsl(h, l=0.75), a, b, lw)

    # ------------------------------------------------------------------
    def draw(self, surf, waveform, fft, beat, tick):
        if not self._built:
            self._build_grid()

        self.hue += 0.003
        bass = float(np.mean(fft[:6]))
        high = float(np.mean(fft[30:]))
        mid  = float(np.mean(fft[6:30]))

        # Slowly rotate which tiles are filled (swap one every ~90 frames)
        self._swap_cd -= 1
        if self._swap_cd <= 0:
            self._swap_cd = random.randint(70, 120)
            on_screen = [i for i, t in enumerate(self.tiles) if self._on_screen(t)]
            candidates = [i for i in on_screen if i not in self.filled_ids]
            if candidates:
                self.filled_ids[random.randrange(len(self.filled_ids))] = random.choice(candidates)

        # On beat, activate a tile to pop to front — keep pool small
        if beat > 0.5 and len(self.active_ids) < self.N_ACTIVE_MAX:
            on_screen = [i for i, t in enumerate(self.tiles) if self._on_screen(t)]
            candidates = [i for i in on_screen if i not in self.active_ids]
            if candidates:
                idx = random.choice(candidates)
                self.active_ids.append(idx)
                t = self.tiles[idx]
                t["svel"]    = 0.6 + beat * 0.4       # burst toward front
                t["rot_vel"] = random.choice([-1, 1]) * (0.06 + mid * 0.08)

        W, H = config.WIDTH, config.HEIGHT

        # ── Pass 1: all non-active tiles ────────────────────────────────────
        for i, tile in enumerate(self.tiles):
            if i in self.active_ids:
                continue

            tile["hue"] = (tile["hue"] + tile["hvel"] + 0.00015) % 1.0

            # Ease scale back to 1.0
            tile["scale"] += (1.0 - tile["scale"]) * 0.08

            pts = self._screen_verts(tile)
            if all(p[0] < 0 or p[0] >= W or p[1] < 0 or p[1] >= H for p in pts):
                continue

            # Filled tiles: colour fill
            if i in self.filled_ids:
                h      = (tile["hue"] + self.hue) % 1.0
                bright = min(tile["bright"] + bass * 0.22, 0.75)
                pygame.draw.polygon(surf, hsl(h, l=bright), pts)

            # All tiles: rainbow wireframe
            self._rainbow_edges(surf, pts)

        # ── Pass 2: active tiles — drawn on top, popped to front ────────────
        finished = []
        for i in self.active_ids:
            tile = self.tiles[i]
            tile["hue"] = (tile["hue"] + tile["hvel"] + 0.00015) % 1.0

            # Spring toward scale 1.0 once the burst decays
            tile["svel"]  += (1.0 - tile["scale"]) * 0.12
            tile["svel"]  *= 0.80
            tile["scale"] += tile["svel"]
            tile["scale"]  = max(0.5, tile["scale"])

            tile["rot"]     += tile["rot_vel"]
            tile["rot_vel"] *= 0.94
            # Pulse rotation with bass
            tile["rot_vel"] += bass * 0.015 * math.copysign(1, tile["rot_vel"] or 1)

            pts = self._screen_verts(tile)

            h      = (tile["hue"] + self.hue) % 1.0
            bright = min(tile["bright"] + bass * 0.35 + 0.20, 0.90)

            # Glow halo
            pygame.draw.polygon(surf, hsl(h, l=bright * 0.35), pts)
            pygame.draw.polygon(surf, hsl(h, l=bright),         pts)
            self._rainbow_edges(surf, pts, lw=2)

            # Return to pool when close to resting
            if abs(tile["scale"] - 1.0) < 0.02 and abs(tile["rot_vel"]) < 0.005:
                tile["scale"] = 1.0
                tile["rot_vel"] = 0.0
                finished.append(i)

        for i in finished:
            self.active_ids.remove(i)
