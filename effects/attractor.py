import math

import numpy as np
import pygame

import config
from .utils import hsl


class Attractor:
    """Lorenz strange attractor rendered as a twisted 3-D ribbon.

    Perspective projection (near = big, far = small) combined with filled
    quad ribbon segments gives the appearance of a flat panel twisting
    through 3-D space.  The panel width scales with perspective depth so
    near sections look like broad glowing planes and far sections taper to
    thin lines.  Dual-axis rotation tumbles the butterfly continuously.
    """

    TRAIL_ALPHA = 20
    _ATTR_FADE  = 4        # very slow → full shape accumulates over time

    _SIGMA0 = 10.0
    _RHO0   = 28.0
    _BETA   = 8.0 / 3.0

    _STEPS  = 8
    _DT     = 0.018    # larger step → segments spaced further apart

    # Perspective camera distance — lower = more dramatic perspective
    _CAM_Z  = 55.0
    # Ribbon half-width in world units — large enough to see as a distinct plane
    _RIB_W  = 7.0

    def __init__(self):
        self.hue      = 0.0
        self.ry       = 0.0
        self.rx       = 0.0
        self.rho_kick = 0.0
        self.x, self.y, self.z = 0.1, 0.0, 25.0
        self.attr_surf  = None
        self._attr_fade = None

    def _init_surf(self):
        self.attr_surf  = pygame.Surface((config.WIDTH, config.HEIGHT))
        self.attr_surf.fill((0, 0, 0))
        self._attr_fade = pygame.Surface((config.WIDTH, config.HEIGHT))
        self._attr_fade.set_alpha(self._ATTR_FADE)
        self._attr_fade.fill((0, 0, 0))

    def _step(self, sigma, rho):
        dx = sigma * (self.y - self.x)
        dy = self.x * (rho - self.z) - self.y
        dz = self.x * self.y - self._BETA * self.z
        self.x += dx * self._DT
        self.y += dy * self._DT
        self.z += dz * self._DT
        if abs(self.x) > 80 or abs(self.y) > 80 or abs(self.z) > 80:
            self.x, self.y, self.z = 0.1, 0.0, 25.0

    def _rotate(self, x3, y3, z3):
        """Apply dual-axis rotation and return (xr, yr, zr)."""
        cos_y, sin_y = math.cos(self.ry), math.sin(self.ry)
        xr =  x3 * cos_y + z3 * sin_y
        yr =  y3
        zr = -x3 * sin_y + z3 * cos_y

        cos_x, sin_x = math.cos(self.rx), math.sin(self.rx)
        yr2 =  yr * cos_x - zr * sin_x
        zr2 =  yr * sin_x + zr * cos_x
        return xr, yr2, zr2

    def _project(self, xr, yr, zr):
        """Perspective projection. Returns (sx, sy, scale)."""
        depth = self._CAM_Z + zr          # always > 0 for reasonable rotations
        depth = max(depth, 5.0)
        fov   = min(config.WIDTH, config.HEIGHT) * 0.45
        scale = fov / depth
        sx = xr * scale + config.WIDTH  / 2
        sy = yr * scale + config.HEIGHT / 2
        sx = max(0.0, min(config.WIDTH  - 1.0, sx))
        sy = max(0.0, min(config.HEIGHT - 1.0, sy))
        return sx, sy, scale

    def _ribbon_quad(self, px, py, ps, cx, cy, cs, rib_w):
        """Return a 4-point screen-space ribbon quad for segment p→c.

        The ribbon is oriented perpendicular to the segment direction.
        Width at each end scales with the perspective scale so far ends
        taper naturally, giving the twisted-plane illusion.
        """
        dx = cx - px
        dy = cy - py
        seg = math.sqrt(dx * dx + dy * dy)
        if seg < 0.5:
            return None
        # Screen-space perpendicular (normalised)
        nx = -dy / seg
        ny =  dx / seg
        hw_p = rib_w * ps   # half-width at previous point
        hw_c = rib_w * cs   # half-width at current point
        return [
            (px + nx * hw_p, py + ny * hw_p),
            (cx + nx * hw_c, cy + ny * hw_c),
            (cx - nx * hw_c, cy - ny * hw_c),
            (px - nx * hw_p, py - ny * hw_p),
        ]

    def draw(self, surf, waveform, fft, beat, tick):
        if self.attr_surf is None:
            self._init_surf()

        self.hue += 0.004
        bass = float(np.mean(fft[:6]))
        high = float(np.mean(fft[30:]))

        sigma = self._SIGMA0 + bass * 5.0
        self.rho_kick = self.rho_kick * 0.92 + beat * 12.0
        rho   = self._RHO0 + self.rho_kick

        self.ry += 0.002 + bass * 0.006
        self.rx += 0.0008 + bass * 0.003

        self.attr_surf.blit(self._attr_fade, (0, 0))

        xr, yr, zr       = self._rotate(self.x, self.y, self.z - 25.0)
        prev_sx, prev_sy, prev_sc = self._project(xr, yr, zr)

        for _ in range(self._STEPS):
            self._step(sigma, rho)
            xr, yr, zr    = self._rotate(self.x, self.y, self.z - 25.0)
            sx, sy, sc    = self._project(xr, yr, zr)

            z_norm  = (self.z - 5.0) / 40.0
            h       = (self.hue + z_norm * 0.55) % 1.0
            # Depth-cued brightness: near = brighter
            depth_t = max(0.0, min(1.0, sc / (min(config.WIDTH, config.HEIGHT) * 0.45 / 5.0)))
            bright  = 0.22 + depth_t * 0.40 + high * 0.20 + beat * 0.12

            quad = self._ribbon_quad(prev_sx, prev_sy, prev_sc,
                                     sx, sy, sc, self._RIB_W)
            if quad:
                pts = [(int(p[0]), int(p[1])) for p in quad]
                edge_col  = hsl(h, l=min(bright + 0.20, 0.95))
                inner_col = hsl(h, l=bright)
                # Leading/trailing edges (travel direction)
                pygame.draw.line(self.attr_surf, edge_col,  pts[0], pts[1], 1)
                pygame.draw.line(self.attr_surf, edge_col,  pts[3], pts[2], 1)
                # Side edges (ribbon width) — slightly dimmer
                pygame.draw.line(self.attr_surf, inner_col, pts[0], pts[3], 1)
                pygame.draw.line(self.attr_surf, inner_col, pts[1], pts[2], 1)

            prev_sx, prev_sy, prev_sc = sx, sy, sc

        surf.blit(self.attr_surf, (0, 0), special_flags=pygame.BLEND_ADD)
