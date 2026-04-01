import math

import numpy as np
import pygame

import config
from .utils import hsl


class Cube:
    """Dual rotating wireframe cubes — each axis driven by a different band."""

    TRAIL_ALPHA = 18

    VERTS = np.array([
        [-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],
        [-1,-1, 1],[1,-1, 1],[1,1, 1],[-1,1, 1],
    ], dtype=float)
    EDGES = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),
             (0,4),(1,5),(2,6),(3,7)]

    def __init__(self):
        self.rx = self.ry = self.rz = 0.0
        self.hue      = 0.0
        self.fade_hue = 0.0
        self.scale    = 1.0
        self.svel     = 0.0
        self.rvx = self.rvy = self.rvz = 0.0
        self.orb_angle = 0.0

    @staticmethod
    def _Rx(a):
        c, s = math.cos(a), math.sin(a)
        return np.array([[1,0,0],[0,c,-s],[0,s,c]])

    @staticmethod
    def _Ry(a):
        c, s = math.cos(a), math.sin(a)
        return np.array([[c,0,s],[0,1,0],[-s,0,c]])

    @staticmethod
    def _Rz(a):
        c, s = math.cos(a), math.sin(a)
        return np.array([[c,-s,0],[s,c,0],[0,0,1]])

    def _project(self, v, fov=680):
        z = v[2] + 3.8
        return (int(v[0] * fov / z + config.WIDTH  // 2),
                int(v[1] * fov / z + config.HEIGHT // 2))

    def _project_off(self, v, ox, oy, oz, fov=680):
        z = v[2] + oz + 3.8
        return (int((v[0] + ox) * fov / z + config.WIDTH  // 2),
                int((v[1] + oy) * fov / z + config.HEIGHT // 2))

    def draw(self, surf, waveform, fft, beat, tick):
        self.fade_hue += 0.0018
        bass = min(float(np.mean(fft[:5])),   1.0)
        mid  = min(float(np.mean(fft[5:25])), 1.0)
        high = min(float(np.mean(fft[25:])),  1.0)

        self.rvx += 0.00165 + mid  * 0.012 + beat * 0.10
        self.rvy += 0.00248 + bass * 0.015 + beat * 0.12
        self.rvz += 0.00083 + high * 0.008 + beat * 0.05
        self.rvx *= 0.94
        self.rvy *= 0.94
        self.rvz *= 0.94
        self.rx  += self.rvx
        self.ry  += self.rvy
        self.rz  += self.rvz

        self.svel  += beat * 0.32 + bass * 0.20
        self.svel  += (1.0 - self.scale) * 0.18
        self.svel  *= 0.68
        self.scale += self.svel
        self.scale  = max(0.5, self.scale)

        R = self._Rx(self.rx) @ self._Ry(self.ry) @ self._Rz(self.rz)

        for base_scale, hue_off in ((self.scale, 0.0), (self.scale * 0.45, 0.5)):
            verts = (R @ (self.VERTS * base_scale).T).T
            proj  = [self._project(v) for v in verts]
            for ei, (a, b) in enumerate(self.EDGES):
                h     = (self.fade_hue + hue_off + ei / len(self.EDGES) * 0.4) % 1.0
                lw    = max(1, int(2 + self.svel * 4)) if base_scale > 0.4 else 1
                color = hsl(h, l=0.40 + min(self.svel, 1.0) * 0.25)
                pygame.draw.line(surf, color, proj[a], proj[b], lw)

        n_sats    = 2 + int(min(beat, 2.0) * 2)
        sat_scale = self.scale * 0.28
        ORB_R     = 2.6
        self.orb_angle += 0.012 + beat * 0.04

        for si in range(n_sats):
            theta = self.orb_angle + si / n_sats * math.tau
            ox    = ORB_R * math.cos(theta)
            oy    = ORB_R * math.sin(theta)
            verts = (R @ (self.VERTS * sat_scale).T).T
            proj  = [self._project_off(v, ox, oy, 0.0) for v in verts]
            h_off = si / n_sats * 0.6
            for ei, (a, b) in enumerate(self.EDGES):
                h     = (self.fade_hue + h_off + ei / len(self.EDGES) * 0.4) % 1.0
                color = hsl(h, l=0.38 + min(self.svel, 1.0) * 0.20)
                pygame.draw.line(surf, color, proj[a], proj[b], 1)
