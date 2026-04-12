"""Shared mutable configuration — WIDTH/HEIGHT are set by the host at display
init time (psysualizer.py reads the actual monitor geometry from xrandr).
These defaults are placeholders only; effects must not be instantiated before
the display is opened."""

WIDTH  = 0
HEIGHT = 0
FPS    = 60

SAMPLE_RATE = 44100
BLOCK_SIZE  = 1024
CHANNELS    = 1

# Multi-band energy (normalised, updated each frame by psysualizer)
# Effects can read these directly for mid/treble reactivity.
MID_ENERGY    = 0.0   # bins 20-100  (~860 Hz – 4.3 kHz)
TREBLE_ENERGY = 0.0   # bins 100-256 (~4.3 kHz – 11 kHz)
BPM           = 0.0   # detected tempo (60–200), 0 until enough beats seen
EFFECT_GAIN   = 1.0   # current effect intensity (set by main loop each frame)
