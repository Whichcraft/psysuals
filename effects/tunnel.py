import math
import random

import numpy as np
import pygame

import config
from .utils import hsl


class Tunnel:
    """First-person ride through a curving tube.

    Two persistent surfaces are managed internally:
      tunnel_surf — tunnel geometry with its own fade
      spark_surf  — spark triangles with a slower fade
    psysualizer clears surf to black each frame (TRAIL_ALPHA=255), then we
    blit tunnel_surf then spark_surf so sparks are ALWAYS above tunnel geometry
    with zero bleed-through, regardless of fade rates.
    """

    N_RINGS = 30
    N_SIDES = 20
    TUBE_R  = 2.8
    Z_FAR   = 10.0
    Z_NEAR  = 0.18

    # psysualizer uses this to set the fade overlay alpha.
    # 255 = fully opaque black → surf is effectively cleared to black every frame.
    TRAIL_ALPHA  = 255
    _TUNNEL_FADE = 28   # tunnel surface fade (same feel as before)
    _SPARK_FADE  = 10   # spark surface fade — slower = longer trails

    def __init__(self):
        self.hue        = 0.0
        self.time       = 0.0
        self.tunnel_surf = None
        self.spark_surf  = None
        self._tfade      = None
        self._sfade      = None
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

    def _init_surfs(self):
        W, H = config.WIDTH, config.HEIGHT
        self.tunnel_surf = pygame.Surface((W, H)); self.tunnel_surf.fill((0, 0, 0))
        self.spark_surf  = pygame.Surface((W, H)); self.spark_surf.fill((0, 0, 0))
        self._tfade = pygame.Surface((W, H)); self._tfade.set_alpha(self._TUNNEL_FADE); self._tfade.fill((0, 0, 0))
        self._sfade = pygame.Surface((W, H)); self._sfade.set_alpha(self._SPARK_FADE);  self._sfade.fill((0, 0, 0))

    def draw(self, surf, waveform, fft, beat, tick):
        if self.tunnel_surf is None:
            self._init_surfs()

        self.hue  += 0.006
        bass       = float(np.mean(fft[:6]))
        mid        = float(np.mean(fft[6:30]))

        dt         = 0.03 + bass * 0.14 + beat * 0.22
        self.time += dt

        # Fewer sparks; size and spawn rate react strongly to bass
        spawn_n = int(bass * 0.6 + (beat * 1.5 if beat > 0.4 else 0))
        for _ in range(spawn_n):
            z = self.Z_FAR * random.uniform(0.65, 0.95)
            self.tris.append({
                "z":    z,
                "pt":   self.time + z,
                "rot":  random.uniform(0, math.tau),
                "rvel": random.choice([-1, 1]) * random.uniform(0.04, 0.14),
                "size": random.uniform(0.5, 1.2) * (1.0 + bass * 3.0 + beat * 1.5),
                "hue":  (self.hue + random.uniform(0, 0.5)) % 1.0,
            })

        for r in self.rings:
            r["z"] -= dt
            if r["z"] < self.Z_NEAR:
                r["z"]  += self.Z_FAR
                r["pt"]  = self.time + r["z"]

        ordered = sorted(self.rings, key=lambda r: -r["z"])

        # ── Fade both layers ─────────────────────────────────────────────────
        self.tunnel_surf.blit(self._tfade, (0, 0))
        self.spark_surf.blit(self._sfade, (0, 0))

        # ── Draw tunnel rings onto tunnel_surf ───────────────────────────────
        for i in range(len(ordered) - 1):
            r1 = ordered[i]
            r2 = ordered[i + 1]

            cx1, cy1 = self._path(r1["pt"])
            cx2, cy2 = self._path(r2["pt"])

            sx1, sy1, sc1 = self._proj(cx1, cy1, r1["z"])
            sx2, sy2, sc2 = self._proj(cx2, cy2, r2["z"])

            sr1 = max(1, int((self.TUBE_R + bass * 0.6) * sc1))
            sr2 = max(1, int((self.TUBE_R + bass * 0.6) * sc2))

            near_t = max(0.0, 1.0 - r1["z"] / self.Z_FAR)
            fi     = min(int(near_t * len(fft) * 0.8), len(fft) - 1)
            h      = (self.hue + near_t) % 1.0
            bright = 0.06 + near_t * 0.65 + fft[fi] * 0.20 + beat * near_t * 0.45 + bass * near_t * 0.40
            lw     = max(1, int(1 + beat * 3 * near_t + bass * 3 * near_t))

            pygame.draw.circle(self.tunnel_surf, hsl(h, l=bright * 0.35), (sx1, sy1), sr1 + 4, lw + 3)
            pygame.draw.circle(self.tunnel_surf, hsl(h, l=bright),        (sx1, sy1), sr1,     lw)

            for side in range(self.N_SIDES):
                angle = side / self.N_SIDES * math.tau
                p1 = (sx1 + int(math.cos(angle) * sr1),
                      sy1 + int(math.sin(angle) * sr1))
                p2 = (sx2 + int(math.cos(angle) * sr2),
                      sy2 + int(math.sin(angle) * sr2))
                hs = (h + side / self.N_SIDES * 0.25) % 1.0
                pygame.draw.line(self.tunnel_surf, hsl(hs, l=bright * 0.55), p1, p2, 1)

            n_star  = 3 + (i % 4)
            s_dir   = 1 if i % 2 == 0 else -1
            s_rot   = self.time * 0.45 * s_dir + i * 0.52
            s_r     = max(2, int(sr1 * 0.52))
            s_h     = (h + 0.5) % 1.0
            s_l     = min(bright * 1.1 + mid * 0.2, 0.92)
            s_pts   = [
                (sx1 + int(math.cos(v / n_star * math.tau + s_rot) * s_r),
                 sy1 + int(math.sin(v / n_star * math.tau + s_rot) * s_r))
                for v in range(n_star)
            ]
            pygame.draw.polygon(self.tunnel_surf, hsl(s_h, l=s_l), s_pts, max(1, lw))

        # ── Draw sparks onto spark_surf ──────────────────────────────────────
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
            bright     = 0.40 + near_t * 0.55 + bass * 0.30
            lw         = max(1, int(1 + near_t * 3))
            pts = [
                (sx + int(math.cos(tri["rot"] + v * math.tau / 3) * tr),
                 sy + int(math.sin(tri["rot"] + v * math.tau / 3) * tr))
                for v in range(3)
            ]
            pygame.draw.polygon(self.spark_surf, hsl(h, l=bright * 0.30), pts, lw + 4)
            pygame.draw.polygon(self.spark_surf, hsl(h, l=bright),         pts, lw)
            live.append(tri)
        self.tris = live[-60:]

        # ── Composite: tunnel below, sparks always on top ────────────────────
        # surf was cleared to black by psysualizer (TRAIL_ALPHA=255)
        surf.blit(self.tunnel_surf, (0, 0))
        surf.blit(self.spark_surf,  (0, 0), special_flags=pygame.BLEND_ADD)
