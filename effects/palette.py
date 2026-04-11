"""
Shared color palette — qwen2.5:14b concept, fixed by Claude.

qwen's get() referenced beat/treble which weren't in scope; fixed by
storing them in update() and reading instance vars in get().

Usage:
    from effects.palette import palette
    palette.update(beat, mid, treble, tick)   # once per frame in main loop
    r, g, b = palette.get(offset=0.0)         # any time in any effect
"""

from effects.utils import hsl


class ColorPalette:
    def __init__(self):
        self.base_hue = 0.0
        self._beat   = 0.0
        self._treble = 0.0

    def update(self, beat: float, mid: float, treble: float, tick: int) -> None:
        self.base_hue = (self.base_hue + 0.001 + mid * 0.003) % 1.0
        self._beat   = beat
        self._treble = treble

    def get(self, offset: float = 0.0):
        hue = (self.base_hue + offset) % 1.0
        sat = min(0.5 + self._beat * 0.25, 1.0)
        lit = max(0.30, min(0.35 + self._treble * 0.15, 0.65))
        return hsl(hue, sat, lit)


palette = ColorPalette()
