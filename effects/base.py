import numpy as np
import pygame

class Effect:
    """Base class for all visualization effects."""
    
    # Optional — controls trail fade speed (lower = longer trails, default 28)
    TRAIL_ALPHA = 28

    def __init__(self):
        """One-time setup. May read config.WIDTH / config.HEIGHT."""
        pass

    def draw(self, surf: pygame.Surface, waveform: np.ndarray,
             fft: np.ndarray, beat: float, tick: int) -> None:
        """Called once per frame. Draw directly onto surf."""
        raise NotImplementedError("Each effect must implement the draw method.")
