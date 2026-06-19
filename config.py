"""Shared mutable configuration — WIDTH/HEIGHT are set by the host at display
init time (psysualizer.py reads the actual monitor geometry from xrandr).
These defaults are placeholders only; effects must not be instantiated before
the display is opened."""

import os
import random

import numpy as np

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
DEFAULT_EFFECT_GAIN = 0.7
EFFECT_GAIN         = DEFAULT_EFFECT_GAIN  # current effect intensity
IS_SILENT           = True

# Silence handling: keep a faint idle motion floor, but suppress false beat
# spikes from noise-floor normalization before/after tracks.
SILENCE_RMS_ENTER = 0.0035
SILENCE_RMS_EXIT  = 0.0060
SILENCE_FFT_ENTER = 0.0015
SILENCE_FFT_EXIT  = 0.0030
SILENCE_FRAMES_ENTER = 6
SILENCE_BEAT_FLOOR   = 0.015
SILENCE_MID_FLOOR    = 0.020
SILENCE_TREBLE_FLOOR = 0.018

RNG_SEED = int(os.environ.get("PSYSUALS_SEED", "0") or 0)
if RNG_SEED:
    random.seed(RNG_SEED)
    np.random.seed(RNG_SEED)
