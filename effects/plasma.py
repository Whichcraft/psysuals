import math

import numpy as np
import pygame

import config


from .base import Effect

class Plasma(Effect):
    """Full-screen sine-interference plasma — four overlapping wave fields
    create a flowing psychedelic texture.  Audio modulates wave frequency,
    time speed, palette, and beat triggers a global brightness flash."""

    RES_DIV = 4

    def __init__(self):
        self.hue  = 0.0
        self.time = 0.0
        rw = max(1, config.WIDTH  // self.RES_DIV)
        rh = max(1, config.HEIGHT // self.RES_DIV)
        self._surf = pygame.Surface((rw, rh))
        xs = np.linspace(-math.pi * 2.5, math.pi * 2.5, rw)
        ys = np.linspace(-math.pi * 2.5, math.pi * 2.5, rh)
        self._X, self._Y = np.meshgrid(xs, ys)
        self._R = np.sqrt(self._X ** 2 + self._Y ** 2)

    @staticmethod
    def _hsl_arr(h, l):
        """Vectorised HSL→RGB (s=1) for 2-D numpy arrays; returns uint8 (H,W,3)."""
        c  = 1.0 - np.abs(2.0 * l - 1.0)
        h6 = h * 6.0
        x  = c * (1.0 - np.abs(h6 % 2.0 - 1.0))
        m  = l - c / 2.0
        i  = h6.astype(int) % 6
        z  = np.zeros_like(h)
        r = np.select([i==0,i==1,i==2,i==3,i==4,i==5], [c,x,z,z,x,c]) + m
        g = np.select([i==0,i==1,i==2,i==3,i==4,i==5], [x,c,c,x,z,z]) + m
        b = np.select([i==0,i==1,i==2,i==3,i==4,i==5], [z,z,x,c,c,x]) + m
        u8 = lambda a: np.clip(a * 255, 0, 255).astype(np.uint8)
        return np.stack([u8(r), u8(g), u8(b)], axis=2)

    def draw(self, surf, waveform, fft, beat, tick):
        self.hue  += 0.005
        bass = float(np.mean(fft[:6]))
        mid  = float(np.mean(fft[6:30]))
        high = float(np.mean(fft[30:]))

        self.time += 0.018 + bass * 0.09 + beat * 0.14

        fm = 1.0 + mid * 0.7

        t  = self.time
        v  = (np.sin(self._X * fm          +  t        ) +
              np.sin(self._Y * fm * 0.8    +  t * 1.4  ) +
              np.sin((self._X * 0.6 + self._Y * 0.8) * fm + t * 0.9) +
              np.sin(self._R * fm * 0.5    -  t * 1.2  )) * 0.25

        h = (v * 0.55 + 0.5 + self.hue + bass * 0.35) % 1.0
        l = np.clip(0.28 + v * 0.22 + beat * 0.22 + high * 0.08, 0.0, 0.95)

        rgb = self._hsl_arr(h, l)
        pygame.surfarray.blit_array(self._surf, rgb.transpose(1, 0, 2))
        surf.blit(pygame.transform.scale(self._surf, (config.WIDTH, config.HEIGHT)), (0, 0))
