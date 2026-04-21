from __future__ import annotations
import threading
from collections import deque
import numpy as np
import sounddevice as sd
import time as _time
import config
from beat_tracking import LibrosaBeatTracker

class AudioEngine:
    def __init__(self):
        self._lock = threading.RLock()
        self._waveform = np.zeros(config.BLOCK_SIZE, dtype=np.float32)
        self._smooth_fft = np.zeros(config.BLOCK_SIZE // 2, dtype=np.float32)
        self._raw_beat_energy = 0.0
        self._mid_energy = 0.0
        self._treble_energy = 0.0
        self._audio_time = 0.0
        self._blackman_window = np.blackman(config.BLOCK_SIZE).astype(np.float32)

        self._prev_spectrum = np.zeros(config.BLOCK_SIZE // 2, dtype=np.float32)
        self._flux_avg = 1e-6
        self._mid_avg = 1e-6
        self._treble_avg = 1e-6
        self._prev_beat_energy = 0.0

        self._beat_times = deque(maxlen=8)
        self._last_onset_time = 0.0
        self._bpm = 0.0

        self._genre_weights = np.ones(20, dtype=np.float32)
        self._detect_accum = np.zeros(config.BLOCK_SIZE // 2, dtype=np.float32)
        self._detect_frames = 0
        self._DETECT_MIN = 300

        self.beat_tracker = LibrosaBeatTracker(
            sample_rate=config.SAMPLE_RATE,
            block_size=config.BLOCK_SIZE,
        )
        self.stream = None
        self.active_dev = None

    def apply_genre_weights(self, genre: str) -> None:
        weights = np.ones(20, dtype=np.float32)
        if genre == "electronic":
            weights[:5] = 1.5
            weights[10:] = 0.7
        elif genre == "rock":
            weights[2:9] = 1.3
        elif genre == "classical":
            weights[:10] = 0.6
            weights[10:] = 1.4
        with self._lock:
            self._genre_weights[:] = weights

    def detect_genre(self) -> str | None:
        """Return detected genre string once enough frames are collected."""
        with self._lock:
            if self._detect_frames < self._DETECT_MIN:
                return None
            avg = self._detect_accum / self._detect_frames
            self._detect_accum[:] = 0
            self._detect_frames = 0

        sub_bass = float(avg[:5].mean())
        bass = float(avg[:15].mean())
        mids = float(avg[15:100].mean())
        sub_ratio = sub_bass / (bass + 1e-6)
        bass_ratio = bass / (bass + mids + 1e-6)

        if sub_ratio > 0.55 and bass_ratio > 0.50:
            return "electronic"
        if bass_ratio > 0.50 and sub_ratio < 0.45:
            return "rock"
        if bass_ratio < 0.35:
            return "classical"
        return "any"

    def _audio_cb(self, indata, frames, time_info, status) -> None:
        if status:
            # log or handle buffer overflow/underflow if needed
            pass
        
        mono = np.asarray(indata[:, 0], dtype=np.float32)
        self.beat_tracker.push_audio(mono, time_info.currentTime)

        # Apply window and FFT
        windowed = mono * self._blackman_window
        spectrum = np.abs(np.fft.rfft(windowed))[: config.BLOCK_SIZE // 2]
        spectrum = spectrum.astype(np.float32, copy=False)
        
        # log1p scaling for better dynamic range representation
        np.log1p(spectrum, out=spectrum)
        spectrum /= 10.0

        with self._lock:
            self._audio_time = float(time_info.currentTime)
            self._waveform = mono.copy()
            
            # FFT Smoothing (EMA)
            alpha = 0.50
            self._smooth_fft = (1.0 - alpha) * self._smooth_fft + alpha * spectrum
            
            self._detect_accum[:] += spectrum
            self._detect_frames += 1

            # Enhanced Beat Detection using Spectral Flux
            # We use genre weights to emphasize specific bands
            weights = self._genre_weights
            
            # Positive difference in spectrum (flux)
            diff = spectrum[:20] * weights - self._prev_spectrum[:20] * weights
            flux = float(np.mean(np.maximum(0.0, diff)))
            
            # Smooth flux for baseline normalization
            self._flux_avg = self._flux_avg * 0.95 + flux * 0.05
            self._raw_beat_energy = flux / (self._flux_avg + 1e-6)

            # Local Onset/BPM detection (fallback for when librosa is slow/absent)
            t_now = float(time_info.currentTime)
            # threshold=2.0 for onset trigger
            if (
                self._raw_beat_energy > 2.2
                and self._prev_beat_energy <= 2.2
                and t_now - self._last_onset_time > 0.28  # ~214 BPM max
            ):
                self._beat_times.append(t_now)
                self._last_onset_time = t_now
                if len(self._beat_times) >= 2:
                    intervals = np.diff(list(self._beat_times))
                    median_interval = float(np.median(intervals))
                    if 0.25 <= median_interval <= 1.2: # 50-240 BPM range
                        self._bpm = 60.0 / median_interval
            
            self._prev_beat_energy = self._raw_beat_energy

            # Normalized Mid Energy (bins 20-100)
            mid = float(self._smooth_fft[20:100].mean())
            self._mid_avg = self._mid_avg * 0.98 + mid * 0.02
            self._mid_energy = mid / (self._mid_avg + 1e-6)

            # Normalized Treble Energy (bins 100-256)
            treble = float(self._smooth_fft[100:256].mean())
            self._treble_avg = self._treble_avg * 0.98 + treble * 0.02
            self._treble_energy = treble / (self._treble_avg + 1e-6)

            self._prev_spectrum[:] = spectrum

    def get_audio(self):
        """Return a thread-safe copy of the current audio analysis state."""
        with self._lock:
            return (
                self._waveform.copy(),
                self._smooth_fft.copy(),
                self._raw_beat_energy,
                self._mid_energy,
                self._treble_energy,
                self._bpm,
                self._audio_time,
            )

    def is_active(self) -> bool:
        """Return True if the audio stream is currently running."""
        return self.stream is not None and self.stream.active

    def input_devices(self) -> list[tuple[int, str]]:
        """Return list of (index, name) for all input-capable devices."""
        try:
            queried = sd.query_devices()
        except Exception:
            return []

        devices = []
        for idx, device in enumerate(queried):
            if device["max_input_channels"] > 0:
                devices.append((idx, device["name"]))
        return devices

    def start_input_stream(self, device_idx: int | None):
        if self.stream is not None:
            self.stop_input_stream()
        
        try:
            self.stream = sd.InputStream(
                samplerate=config.SAMPLE_RATE,
                blocksize=config.BLOCK_SIZE,
                channels=config.CHANNELS,
                device=device_idx,
                callback=self._audio_cb,
            )
            self.stream.start()
            self.active_dev = device_idx
            return self.stream
        except Exception:
            self.stream = None
            self.active_dev = None
            return None

    def stop_input_stream(self) -> None:
        if self.stream is None:
            return
        try:
            self.stream.stop()
        finally:
            self.stream.close()
        self.stream = None
        self.active_dev = None

    def open_input_stream(self, *candidates):
        seen = []
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.append(candidate)
            stream = self.start_input_stream(candidate)
            if stream:
                return stream, candidate
        return None, None
