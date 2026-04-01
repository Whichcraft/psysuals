import math
import random

import numpy as np
import pygame

import config
from .utils import hsl


class Attractor:
    """Triangle mosaic wall.

    All triangles are wireframe with rainbow edges.  4-6 tiles are filled
    at any time.  On beats, a tile pops to the FRONT at 4-5× size, pulses
    with bass, then after a fixed lifetime springs back into the grid.
    Active tiles are drawn last (always on top) with a solid fill so
    nothing shows through from behind.
    """

    TRAIL_ALPHA  = 28
    N_COLS       = 14
    GAP          = 0.88
    N_FILLED     = 5
    N_ACTIVE_MAX = 2
    ACTIVE_LIFE  = 360   # frames before tile starts falling back (~6 s at 60 fps)
    MIN_LIFE     = 180   # minimum frames a tile stays enlarged before falling back

    def __init__(self):
        self.hue        = 0.0
        self.tiles      = []
        self.filled_ids = []
        self.active_ids = []
        self._built     = False
        self._swap_cd   = 0
        self._auto_cd   = random.randint(180, 300)  # frames until next auto-activation
        # Two independent rainbow sweeps so one is nearly always on screen
        # Second starts mid-travel so they're never both off-screen simultaneously
        self._sweeps = [
            {"pos": 0.0,   "angle": random.uniform(0, math.tau), "vel": 3.2},
            {"pos": 600.0, "angle": random.uniform(0, math.tau), "vel": 4.1},
        ]
        self._sweep_width = 90.0         # half-width of each sweep band
        self._sweep_diag  = 0.0          # set on build

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

        # Seed filled set — allow any tile whose centroid is near the screen
        visible = self._visible_indices()
        self.filled_ids = random.sample(visible, min(self.N_FILLED, len(visible)))
        self._built = True
        # Screen diagonal for sweep wrap-around
        self._sweep_diag = math.hypot(config.WIDTH, config.HEIGHT)

    def _make_tile(self, verts):
        cx = sum(v[0] for v in verts) / 3
        cy = sum(v[1] for v in verts) / 3
        return {
            "verts":   verts,
            "cx": cx,  "cy": cy,
            "hue":     random.random(),
            "hvel":    random.uniform(-0.0006, 0.0006),
            "bright":  random.uniform(0.20, 0.50),
            "rot":     0.0,
            "rot_vel": 0.0,
            "scale":   1.0,
            "svel":    0.0,
            "life":    0,      # frames remaining as active; 0 = not active / falling back
        }

    def _visible_indices(self):
        """Tiles whose centroid is within a half-tile margin of the screen."""
        W, H = config.WIDTH, config.HEIGHT
        tw = W / self.N_COLS
        m  = tw
        return [i for i, t in enumerate(self.tiles)
                if -m <= t["cx"] < W + m and -m <= t["cy"] < H + m]

    def _interior_indices(self):
        """Tiles whose centroid is comfortably inside the screen (not edge tiles)."""
        W, H  = config.WIDTH, config.HEIGHT
        tw    = W / self.N_COLS
        margin = tw * 1.5   # stay at least 1.5 tile-widths from each edge
        return [i for i, t in enumerate(self.tiles)
                if margin <= t["cx"] < W - margin and margin <= t["cy"] < H - margin]

    def _any_on_screen(self, tile):
        W, H = config.WIDTH, config.HEIGHT
        return any(0 <= vx < W and 0 <= vy < H for vx, vy in tile["verts"])

    def _screen_verts(self, tile):
        cx, cy  = tile["cx"], tile["cy"]
        s       = self.GAP * tile["scale"]
        cos_r   = math.cos(tile["rot"])
        sin_r   = math.sin(tile["rot"])
        _C = 16383  # safe pygame/SDL coordinate limit
        return [(max(-_C, min(_C, int(cx + ((vx - cx) * s) * cos_r - ((vy - cy) * s) * sin_r))),
                 max(-_C, min(_C, int(cy + ((vx - cx) * s) * sin_r + ((vy - cy) * s) * cos_r))))
                for vx, vy in tile["verts"]]

    def _rainbow_edges(self, surf, pts, lw=1):
        for i in range(3):
            a = pts[i];  b = pts[(i + 1) % 3]
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

        # Slowly rotate filled set
        self._swap_cd -= 1
        if self._swap_cd <= 0:
            self._swap_cd = random.randint(70, 120)
            vis       = self._visible_indices()
            candidates = [i for i in vis if i not in self.filled_ids]
            if candidates and self.filled_ids:
                self.filled_ids[random.randrange(len(self.filled_ids))] = random.choice(candidates)

        # On beat, pop a new interior tile to front (or extend life of existing ones)
        if beat > 0.5:
            if len(self.active_ids) < self.N_ACTIVE_MAX:
                candidates = [i for i in self._interior_indices() if i not in self.active_ids]
                if candidates:
                    idx = random.choice(candidates)
                    self.active_ids.append(idx)
                    t = self.tiles[idx]
                    t["life"]    = self.ACTIVE_LIFE
                    t["rot_vel"] = random.choice([-1, 1]) * random.uniform(0.04, 0.10)
                    t["home_cx"] = t["cx"]; t["home_cy"] = t["cy"]
                    t["cvx"] = 0.0;         t["cvy"] = 0.0
            else:
                # Slots full — extend life of existing active tiles so they don't fall back yet
                for idx in self.active_ids:
                    self.tiles[idx]["life"] = max(self.tiles[idx]["life"], self.MIN_LIFE)

        # Periodically auto-activate 1-2 interior tiles regardless of beat
        self._auto_cd -= 1
        if self._auto_cd <= 0:
            self._auto_cd = random.randint(180, 320)
            n_new = random.randint(1, 2)
            candidates = [i for i in self._interior_indices() if i not in self.active_ids]
            random.shuffle(candidates)
            for idx in candidates[:n_new]:
                if len(self.active_ids) < self.N_ACTIVE_MAX + 2:  # allow up to +2 extra
                    self.active_ids.append(idx)
                    t = self.tiles[idx]
                    t["life"]    = self.ACTIVE_LIFE
                    t["rot_vel"] = random.choice([-1, 1]) * random.uniform(0.03, 0.08)
                    t["home_cx"] = t["cx"]; t["home_cy"] = t["cy"]
                    t["cvx"] = 0.0;         t["cvy"] = 0.0

        W, H = config.WIDTH, config.HEIGHT

        # ── Advance both sweeps ──────────────────────────────────────────────
        for sw in self._sweeps:
            sw["pos"] += sw["vel"]
            if sw["pos"] > self._sweep_diag + self._sweep_width:
                sw["pos"]   = -self._sweep_width
                sw["angle"] = random.uniform(0, math.tau)

        # ── Pass 1: all non-active tiles ────────────────────────────────────
        for i, tile in enumerate(self.tiles):
            if i in self.active_ids:
                continue

            tile["hue"] = (tile["hue"] + tile["hvel"] + 0.00015) % 1.0

            # Spring back to scale=1.0 and rot=0.0 (in case it was previously active)
            tile["svel"]    += (1.0 - tile["scale"]) * 0.15
            tile["svel"]    *= 0.75
            tile["scale"]   += tile["svel"]
            tile["rot_vel"] += (0.0 - tile["rot"]) * 0.05
            tile["rot_vel"] *= 0.88
            tile["rot"]     += tile["rot_vel"]

            pts = self._screen_verts(tile)
            if all(p[0] < 0 or p[0] >= W or p[1] < 0 or p[1] >= H for p in pts):
                continue

            # Sweep glows — drawn first so tile fill and edges render on top
            for sw in self._sweeps:
                sw_cos = math.cos(sw["angle"])
                sw_sin = math.sin(sw["angle"])
                d      = tile["cx"] * sw_cos + tile["cy"] * sw_sin
                dist   = abs(d - sw["pos"])
                if dist < self._sweep_width:
                    sw_t    = 1.0 - dist / self._sweep_width
                    sweep_h = (self.hue + d / self._sweep_diag) % 1.0
                    sweep_br = 0.20 + sw_t * 0.55
                    pygame.draw.polygon(surf, hsl(sweep_h, s=1.0, l=sweep_br), pts)

            if i in self.filled_ids:
                h      = (tile["hue"] + self.hue) % 1.0
                bright = min(tile["bright"] + bass * 0.20, 0.72)
                pygame.draw.polygon(surf, hsl(h, l=bright), pts)

            self._rainbow_edges(surf, pts)

        # ── Pass 2: active tiles — on top, way bigger, bass-pulsing ─────────
        finished = []
        for i in self.active_ids:
            tile = self.tiles[i]
            tile["hue"] = (tile["hue"] + tile["hvel"] + 0.00015) % 1.0

            alive = tile["life"] > 0
            if alive:
                # Still alive: hold at large scale, pulse hard with bass
                tile["life"] -= 1
                target         = 4.5 + bass * 4.0     # up to ~8.5x on strong bass beat
                tile["svel"]  += (target - tile["scale"]) * 0.22
                tile["svel"]  *= 0.70
                tile["scale"]  = min(tile["scale"] + tile["svel"], 12.0)
                tile["rot"]   += tile["rot_vel"]
                # Bass reinforces spin
                tile["rot_vel"] += bass * 0.016 * math.copysign(1, tile["rot_vel"] or 1)
                tile["rot_vel"] *= 0.96
                # Move centroid with velocity, then let bounce handle edges
                tile["cx"] += tile.get("cvx", 0.0)
                tile["cy"] += tile.get("cvy", 0.0)
                tile["cvx"] = tile.get("cvx", 0.0) * 0.97
                tile["cvy"] = tile.get("cvy", 0.0) * 0.97
            else:
                # Life expired: spring back to rest (scale → 1.0, rot → 0.0, pos → home)
                tile["svel"]    += (1.0 - tile["scale"]) * 0.12
                tile["svel"]    *= 0.78
                tile["scale"]   += tile["svel"]
                tile["rot_vel"] += (0.0 - tile["rot"]) * 0.06
                tile["rot_vel"] *= 0.85
                tile["rot"]     += tile["rot_vel"]
                # Decay centroid velocity and spring back to home grid position
                tile["cvx"] = tile.get("cvx", 0.0) * 0.80
                tile["cvy"] = tile.get("cvy", 0.0) * 0.80
                home_cx = tile.get("home_cx", tile["cx"])
                home_cy = tile.get("home_cy", tile["cy"])
                tile["cx"] += (home_cx - tile["cx"]) * 0.10
                tile["cy"] += (home_cy - tile["cy"]) * 0.10

                if (abs(tile["scale"] - 1.0) < 0.03 and abs(tile["rot"]) < 0.02
                        and abs(tile["rot_vel"]) < 0.003
                        and abs(tile["cx"] - home_cx) < 1.0
                        and abs(tile["cy"] - home_cy) < 1.0):
                    tile["scale"]   = 1.0
                    tile["rot"]     = 0.0
                    tile["rot_vel"] = 0.0
                    tile["svel"]    = 0.0
                    tile["cx"]      = home_cx
                    tile["cy"]      = home_cy
                    finished.append(i)

            pts = self._screen_verts(tile)

            # ── Bounce off screen edges (active phase only) ──────────────────
            if alive:
                min_x = min(p[0] for p in pts)
                max_x = max(p[0] for p in pts)
                min_y = min(p[1] for p in pts)
                max_y = max(p[1] for p in pts)
                if min_x < 0:
                    tile["cvx"]  = abs(tile.get("cvx", 0.0)) * 0.8 + 1.5
                    tile["cx"]  -= min_x          # push back inside
                    pts = self._screen_verts(tile)
                elif max_x > W:
                    tile["cvx"]  = -(abs(tile.get("cvx", 0.0)) * 0.8 + 1.5)
                    tile["cx"]  -= (max_x - W)
                    pts = self._screen_verts(tile)
                if min_y < 0:
                    tile["cvy"]  = abs(tile.get("cvy", 0.0)) * 0.8 + 1.5
                    tile["cy"]  -= min_y
                    pts = self._screen_verts(tile)
                elif max_y > H:
                    tile["cvy"]  = -(abs(tile.get("cvy", 0.0)) * 0.8 + 1.5)
                    tile["cy"]  -= (max_y - H)
                    pts = self._screen_verts(tile)

            h      = (tile["hue"] + self.hue) % 1.0
            bright = min(tile["bright"] + bass * 0.40 + 0.25, 0.92)

            # Solid black backing so nothing bleeds through
            pygame.draw.polygon(surf, (0, 0, 0), pts)
            # Colour fill
            pygame.draw.polygon(surf, hsl(h, l=bright), pts)
            # Bold rainbow edges on top
            self._rainbow_edges(surf, pts, lw=3)

        for i in finished:
            self.active_ids.remove(i)
