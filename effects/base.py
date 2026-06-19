import numpy as np
import pygame
import config

class Effect:
    """Base class for all visualization effects."""
    
    # Optional — controls trail fade speed (lower = longer trails, default 28)
    TRAIL_ALPHA = 28
    
    # Resolution divisor for performance-heavy effects
    RES_DIV = 1
    
    # Set to True if the effect renders directly to the GL backbuffer
    IS_GL = False

    def __init__(self, renderer=None, **kwargs):
        """One-time setup. Stores optional GLRenderer."""
        self.renderer = renderer

    def _auto_res_div(self) -> int:
        """Pick a display-aware internal scale bucket.

        Higher resolutions get finer internal rendering so the effect does
        not look blocky on HiDPI or TV-sized screens.
        """
        w = max(1, config.WIDTH)
        h = max(1, config.HEIGHT)
        try:
            info = pygame.display.Info()
            w = max(w, int(getattr(info, "current_w", 0) or 0))
            h = max(h, int(getattr(info, "current_h", 0) or 0))
        except Exception:
            pass

        area = w * h
        if w >= 3200 or h >= 1800 or area >= 5_500_000:
            return 1
        if w >= 2200 or h >= 1300 or area >= 3_000_000:
            return 2
        return 3

    def _render_div(self) -> int:
        """Return the effect's effective internal render divisor."""
        return max(1, min(int(getattr(self, "RES_DIV", 1)), self._auto_res_div()))

    def _render_size(self) -> tuple[int, int, int]:
        """Return (internal_width, internal_height, divisor)."""
        div = self._render_div()
        return max(1, config.WIDTH // div), max(1, config.HEIGHT // div), div
    
    def draw(self, surf: pygame.Surface | None, waveform: np.ndarray,
             fft: np.ndarray, beat: float, tick: int) -> None:
        """Called once per frame. Draw directly onto surf."""
        raise NotImplementedError("Each effect must implement the draw method.")
