"""Shared mutable configuration — update config.WIDTH/HEIGHT after display init."""

WIDTH  = 1280
HEIGHT = 720
FPS    = 60

SAMPLE_RATE = 44100
BLOCK_SIZE  = 1024
CHANNELS    = 1

# Multi-band energy (normalised, updated each frame by psysualizer)
# Effects can read these directly for mid/treble reactivity.
MID_ENERGY    = 0.0   # bins 20-100  (~860 Hz – 4.3 kHz)
TREBLE_ENERGY = 0.0   # bins 100-256 (~4.3 kHz – 11 kHz)
BPM           = 0.0   # detected tempo (60–200), 0 until enough beats seen
