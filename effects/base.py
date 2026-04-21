import numpy as np
import pygame

class Effect:
    """Base class for all visualization effects."""
    
    # Optional — controls trail fade speed (lower = longer trails, default 28)
    TRAIL_ALPHA = 28
    
    # Resolution divisor for performance-heavy effects
    RES_DIV = 1

    def __init__(self, renderer=None, **kwargs):
        """One-time setup. Stores optional GLRenderer."""
        self.renderer = renderer

    def draw(self, surf: pygame.Surface | None, waveform: np.ndarray,
             fft: np.ndarray, beat: float, tick: int) -> None:
        """Called once per frame. Draw directly onto surf."""
        raise NotImplementedError("Each effect must implement the draw method.")
