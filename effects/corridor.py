import math
import random

import numpy as np
import pygame

import config
from .utils import hsl


class Corridor:
    """Neon rainbow corridor — concentric rounded-rectangle frames fly toward
    the camera creating a first-person ride through a glowing geometric passage.
    Full rainbow sweep across depth; beat flares nearest frames and spawns
    glowing sparks that streak toward the camera."""

    N_FRAMES = 28
    Z_FAR    = 12.0
    Z_NEAR   = 0.28
    WORLD_H  = 2.0
    ASPECT   = 1.65

    def __init__(self):
        self.hue    = 0.0
        self.time   = 0.0
        spacing     = (self.Z_FAR - self.Z_NEAR) / self.N_FRAMES
        self.frames = [{"z": self.Z_NEAR + i * spacing} for i in range(self.N_FRAMES)]
        self.sparks = []

    def _path(self, t):
        return (math.sin(t * 0.19) * 0.5, math.cos(t * 0.14) * 0.35)

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue  += 0.005
        bass       = float(np.mean(fft[:6]))
        dt         = 0.028 + bass * 0.08 + beat * 0.16
        self.time += dt

        fov = min(config.WIDTH, config.HEIGHT) * 0.72

        # Spawn sparks with ox/oy bounded to corridor half-extents so they
        # never leave the tunnel.  Drop "pt" — sparks use self.time so their
        # path centre always matches the corridor frame at the same z.
        spawn_n = int(bass * 1.2 + (beat * 4.0 if beat > 0.25 else 0))
        for _ in range(spawn_n):
            z = self.Z_FAR * random.uniform(0.55, 0.92)
            self.sparks.append({
                "z":   z,
                "hue": (self.hue + random.uniform(0, 0.6)) % 1.0,
                "ox":  random.uniform(-(self.WORLD_H * self.ASPECT) * 0.85,
                                       (self.WORLD_H * self.ASPECT) * 0.85),
                "oy":  random.uniform(-self.WORLD_H * 0.85, self.WORLD_H * 0.85),
            })

        for f in self.frames:
            f["z"] -= dt
            if f["z"] < self.Z_NEAR:
                f["z"] += self.Z_FAR

        # Advance sparks and drop expired ones
        live = []
        for sp in self.sparks:
            sp["z"] -= dt
            if sp["z"] >= self.Z_NEAR:
                live.append(sp)
        self.sparks = live[-100:]

        # Build a single depth-sorted draw list so frames never overwrite
        # nearer sparks — everything is painted back-to-front together.
        draw_list = [("frame", f["z"], f) for f in self.frames]
        draw_list += [("spark", sp["z"], sp) for sp in self.sparks]
        draw_list.sort(key=lambda x: -x[1])

        for kind, raw_z, obj in draw_list:
            z      = max(raw_z, 0.01)
            near_t = max(0.0, 1.0 - z / self.Z_FAR)
            pcx, pcy = self._path(self.time - z * 0.5)

            if kind == "frame":
                cx_s = int(pcx * fov / z + config.WIDTH  / 2)
                cy_s = int(pcy * fov / z + config.HEIGHT / 2)

                fi     = min(int(near_t * len(fft) * 0.8), len(fft) - 1)
                h      = (self.hue + near_t) % 1.0
                bright = 0.06 + near_t * 0.70 + fft[fi] * 0.20 + beat * near_t * 0.50
                lw     = max(1, int(1 + beat * 4 * near_t))

                half_h = int(self.WORLD_H * fov / z)
                half_w = int(self.WORLD_H * self.ASPECT * fov / z)
                if half_w < 3 or half_h < 3:
                    continue

                rect   = pygame.Rect(cx_s - half_w, cy_s - half_h, half_w * 2, half_h * 2)
                radius = max(2, min(half_w // 3, half_h // 3, half_w - 1, half_h - 1))

                infl = lw * 5 + 4
                gr   = rect.inflate(infl, infl)
                g_r  = max(2, min(gr.width // 2 - 1, gr.height // 2 - 1, radius + infl // 2))
                pygame.draw.rect(surf, hsl(h, l=bright * 0.22), gr,   lw + 4, border_radius=g_r)
                pygame.draw.rect(surf, hsl(h, l=bright),        rect, lw,     border_radius=radius)

            else:  # spark — path centre tracks corridor at same z/time
                sx     = int((pcx + obj["ox"]) * fov / z + config.WIDTH  / 2)
                sy     = int((pcy + obj["oy"]) * fov / z + config.HEIGHT / 2)
                r      = max(2, int(fov / z * 0.05))
                h      = (obj["hue"] + near_t * 0.35) % 1.0
                bright = 0.35 + near_t * 0.60
                pygame.draw.circle(surf, hsl(h, l=bright * 0.25), (sx, sy), r + 4)
                pygame.draw.circle(surf, hsl(h, l=bright),         (sx, sy), max(1, r))
