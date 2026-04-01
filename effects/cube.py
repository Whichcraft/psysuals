import math

import numpy as np
import pygame

import config
from .utils import hsl


class Cube:
    """Dual rotating wireframe cubes — each axis driven by a different band.

    Satellites are rendered on a dedicated persistent surface (faded more
    slowly than the main surface) so they leave long trailing lines that
    are always composited above the main cubes.
    """

    TRAIL_ALPHA  = 18
    _SAT_FADE    = 16  # lower than TRAIL_ALPHA → longer satellite trails

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
        self.orb_angle  = 0.0
        # Satellites use their own slow rotation, independent of the main cube,
        # so they never spin too fast or look distorted at high intensity.
        self.sat_rx = 0.0
        self.sat_ry = 0.0
        self.sat_surf   = None   # created on first draw
        self._sat_fade  = None

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

    def _project_sat(self, verts_3d, ox, oy, sat_scale, fov=680):
        """Project satellite cube without distortion.

        Project the orbit centre once, apply a uniform 2D scale for all
        vertices so the cube never looks skewed, then clamp so it stays
        fully on-screen.
        """
        z       = 3.8  # satellites orbit at z=0, so effective z depth = 3.8
        scale_s = fov / z
        cx_s    = ox * scale_s + config.WIDTH  // 2
        cy_s    = oy * scale_s + config.HEIGHT // 2

        # screen-space half-extent of the cube (vertex coords are in [-1,1])
        extent = sat_scale * scale_s + 2  # +2 px margin
        cx_s   = max(extent, min(config.WIDTH  - extent, cx_s))
        cy_s   = max(extent, min(config.HEIGHT - extent, cy_s))

        return [(int(cx_s + v[0] * scale_s), int(cy_s + v[1] * scale_s))
                for v in verts_3d]

    def _init_sat_surf(self):
        self.sat_surf  = pygame.Surface((config.WIDTH, config.HEIGHT))
        self.sat_surf.fill((0, 0, 0))
        self._sat_fade = pygame.Surface((config.WIDTH, config.HEIGHT))
        self._sat_fade.set_alpha(self._SAT_FADE)
        self._sat_fade.fill((0, 0, 0))

    def draw(self, surf, waveform, fft, beat, tick):
        if self.sat_surf is None:
            self._init_sat_surf()

        self.fade_hue += 0.0018
        bass = min(float(np.mean(fft[:5])),   1.0)
        mid  = min(float(np.mean(fft[5:25])), 1.0)
        high = min(float(np.mean(fft[25:])),  1.0)

        self.rvx += 0.00165 + mid  * 0.012 + beat * 0.10
        self.rvy += 0.00248 + bass * 0.015 + beat * 0.12
        self.rvz += 0.00083 + high * 0.008 + beat * 0.05
        self.rvx *= 0.94; self.rvx = max(-0.08, min(0.08, self.rvx))
        self.rvy *= 0.94; self.rvy = max(-0.08, min(0.08, self.rvy))
        self.rvz *= 0.94; self.rvz = max(-0.05, min(0.05, self.rvz))
        self.rx  += self.rvx
        self.ry  += self.rvy
        self.rz  += self.rvz

        # Beat/bass drive visual energy (line width + brightness) but not scale
        self.svel   = self.svel * 0.68 + (beat * 0.32 + bass * 0.20) * 0.68
        self.scale  = 1.0

        R = self._Rx(self.rx) @ self._Ry(self.ry) @ self._Rz(self.rz)

        for base_scale, hue_off in ((self.scale, 0.0), (self.scale * 0.45, 0.5)):
            verts = (R @ (self.VERTS * base_scale).T).T
            proj  = [self._project(v) for v in verts]
            for ei, (a, b) in enumerate(self.EDGES):
                h     = (self.fade_hue + hue_off + ei / len(self.EDGES) * 0.4) % 1.0
                lw    = max(1, int(2 + self.svel * 4)) if base_scale > 0.4 else 1
                color = hsl(h, l=0.40 + min(self.svel, 1.0) * 0.25)
                pygame.draw.line(surf, color, proj[a], proj[b], lw)

        # Satellites: always 2, fixed positions 180° apart, own slow rotation.
        # Keeping n_sats constant prevents position jumps at high intensity.
        sat_scale = min(self.scale * 0.28, 0.55)   # cap prevents oversized cubes
        ORB_R     = 2.6
        self.orb_angle += 0.012 + beat * 0.04

        # Satellites rotate slowly and independently (no tie to main cube's R)
        self.sat_rx += 0.018
        self.sat_ry += 0.026
        Rs = self._Rx(self.sat_rx) @ self._Ry(self.sat_ry)

        # Fade satellite trail surface independently (slower than main)
        self.sat_surf.blit(self._sat_fade, (0, 0))

        for si in range(2):
            theta = self.orb_angle + si * math.pi   # always 180° apart
            ox    = ORB_R * math.cos(theta)
            oy    = ORB_R * math.sin(theta)
            verts = (Rs @ (self.VERTS * sat_scale).T).T
            proj  = self._project_sat(verts, ox, oy, sat_scale)
            h_off = si * 0.5
            for ei, (a, b) in enumerate(self.EDGES):
                h     = (self.fade_hue + h_off + ei / len(self.EDGES) * 0.4) % 1.0
                color = hsl(h, l=0.18 + min(self.svel, 1.0) * 0.28)
                pygame.draw.line(self.sat_surf, color, proj[a], proj[b], 1)

        # Composite satellite trails on top of the main cubes
        surf.blit(self.sat_surf, (0, 0), special_flags=pygame.BLEND_ADD)
