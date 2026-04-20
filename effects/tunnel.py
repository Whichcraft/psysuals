import math
import random

import numpy as np
import pygame

import config
from .utils import hsl


from .base import Effect

class Tunnel(Effect):
    """First-person ride through a curving tube.

    Each ring has a fixed position on the tube path and a z-depth that
    decreases every frame so rings physically fly toward the camera.
    When a ring passes through (z < Z_NEAR) it is recycled to the far end.
    """

    N_RINGS = 30
    N_SIDES = 20
    TUBE_R  = 2.8
    Z_FAR   = 10.0
    Z_NEAR  = 0.18

    def __init__(self):
        self.hue  = 0.0
        self.time = 0.0
        spacing = (self.Z_FAR - self.Z_NEAR) / self.N_RINGS
        self.rings = [
            {"z": self.Z_NEAR + i * spacing,
             "pt": self.Z_NEAR + i * spacing}
            for i in range(self.N_RINGS)
        ]
        self.tris = []

    def _path(self, t):
        return (math.sin(t * 0.21) * 0.8,
                math.cos(t * 0.16) * 0.6)

    def _proj(self, wx, wy, wz):
        fov = min(config.WIDTH, config.HEIGHT) * 0.75
        z   = max(wz, 0.01)
        return (int(wx * fov / z + config.WIDTH  / 2),
                int(wy * fov / z + config.HEIGHT / 2),
                fov / z)

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue  += 0.006
        bass       = float(np.mean(fft[:6]))
        mid        = float(np.mean(fft[6:30]))

        dt         = 0.03 + bass * 0.09 + beat * 0.18
        self.time += dt

        # Spawn only in the far third of the tube and cap the live count so the
        # mid-range doesn't fill up with spinning triangles.
        spawn_n = int(bass * 2.0 + (beat * 3.0 if beat > 0.5 else 0))
        for _ in range(spawn_n):
            z = self.Z_FAR * random.uniform(0.80, 0.98)
            self.tris.append({
                "z":    z,
                "pt":   self.time + z,
                "rot":  random.uniform(0, math.tau),
                "rvel": random.choice([-1, 1]) * random.uniform(0.04, 0.12),
                "size": random.uniform(0.45, 1.1) * (1.0 + bass * 1.5),
                "hue":  (self.hue + random.uniform(0, 0.5)) % 1.0,
            })

        for r in self.rings:
            r["z"] -= dt
            if r["z"] < self.Z_NEAR:
                r["z"]  += self.Z_FAR
                r["pt"]  = self.time + r["z"]

        ordered = sorted(self.rings, key=lambda r: -r["z"])

        for i in range(len(ordered) - 1):
            r1 = ordered[i]
            r2 = ordered[i + 1]

            cx1, cy1 = self._path(r1["pt"])
            cx2, cy2 = self._path(r2["pt"])

            sx1, sy1, sc1 = self._proj(cx1, cy1, r1["z"])
            sx2, sy2, sc2 = self._proj(cx2, cy2, r2["z"])

            sr1 = max(1, int(self.TUBE_R * sc1))
            sr2 = max(1, int(self.TUBE_R * sc2))

            near_t = max(0.0, 1.0 - r1["z"] / self.Z_FAR)
            fi     = min(int(near_t * len(fft) * 0.8), len(fft) - 1)
            h      = (self.hue + near_t) % 1.0
            bright = 0.06 + near_t * 0.70 + fft[fi] * 0.20 + beat * near_t * 0.50
            lw     = max(1, int(1 + beat * 3 * near_t))

            pygame.draw.circle(surf, hsl(h, l=bright * 0.35), (sx1, sy1), sr1 + 4, lw + 3)
            pygame.draw.circle(surf, hsl(h, l=bright),        (sx1, sy1), sr1,     lw)

            for side in range(self.N_SIDES):
                angle = side / self.N_SIDES * math.tau
                p1 = (sx1 + int(math.cos(angle) * sr1),
                      sy1 + int(math.sin(angle) * sr1))
                p2 = (sx2 + int(math.cos(angle) * sr2),
                      sy2 + int(math.sin(angle) * sr2))
                hs = (h + side / self.N_SIDES * 0.25) % 1.0
                pygame.draw.line(surf, hsl(hs, l=bright * 0.55), p1, p2, 1)

            n_star  = 3 + (i % 4)
            s_dir   = 1 if i % 2 == 0 else -1
            s_rot   = self.time * 0.45 * s_dir + i * 0.52
            s_r     = max(2, int(sr1 * 0.24))
            s_h     = (h + 0.5) % 1.0
            s_l     = min(bright * 1.1 + mid * 0.2, 0.92)
            s_pts   = [
                (sx1 + int(math.cos(v / n_star * math.tau + s_rot) * s_r),
                 sy1 + int(math.sin(v / n_star * math.tau + s_rot) * s_r))
                for v in range(n_star)
            ]
            pygame.draw.polygon(surf, hsl(s_h, l=s_l), s_pts, max(1, lw))

        live = []
        for tri in self.tris:
            tri["z"]   -= dt
            tri["rot"] += tri["rvel"]
            if tri["z"] < self.Z_NEAR:
                continue
            tcx, tcy   = self._path(tri["pt"])
            sx, sy, sc = self._proj(tcx, tcy, tri["z"])
            near_t     = max(0.0, 1.0 - tri["z"] / self.Z_FAR)
            tr         = max(3, int(tri["size"] * sc))
            h          = (tri["hue"] + near_t * 0.4) % 1.0
            bright     = 0.35 + near_t * 0.60
            lw         = max(1, int(1 + near_t * 3))
            pts = [
                (sx + int(math.cos(tri["rot"] + v * math.tau / 3) * tr),
                 sy + int(math.sin(tri["rot"] + v * math.tau / 3) * tr))
                for v in range(3)
            ]
            pygame.draw.polygon(surf, hsl(h, l=bright * 0.30), pts, lw + 4)
            pygame.draw.polygon(surf, hsl(h, l=bright),         pts, lw)
            live.append(tri)
        self.tris = live[-50:]
