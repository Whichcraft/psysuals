#!/usr/bin/env python3
import os
import time
import numpy as np
import pygame
import config
from effects import MODES
from gl_renderer import GLRenderer, HAS_MODERNGL

def run_benchmark(duration_s=2.0):
    global HAS_MODERNGL
    print(f"Running benchmarks (duration: {duration_s}s per mode)...")
    
    # Mock audio data
    waveform = np.random.uniform(-1, 1, 1024).astype(np.float32)
    fft = np.random.uniform(0, 1, 512).astype(np.float32)
    beat = 1.0
    tick = 0
    
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    pygame.init()
    W, h = 1920, 1080 # Benchmark at Full HD
    config.WIDTH, config.HEIGHT = W, h
    
    # CPU Target
    cpu_surf = pygame.Surface((W, h))
    
    # GL Target (if available)
    renderer = None
    gl_target = None
    if HAS_MODERNGL:
        try:
            pygame.display.set_mode((W, h), pygame.OPENGL | pygame.DOUBLEBUF)
            renderer = GLRenderer(W, h)
            gl_target = pygame.Surface((W, h), pygame.SRCALPHA)
        except Exception as e:
            print(f"  ⚠️ ModernGL init failed for benchmark: {e}")
            HAS_MODERNGL = False

    results = []

    for name, VisCls in MODES:
        print(f"  Benchmarking {name:12}...", end="", flush=True)
        
        # CPU Test
        vis_cpu = VisCls()
        start = time.perf_counter()
        frames = 0
        end_time = start + duration_s
        while time.perf_counter() < end_time:
            vis_cpu.draw(cpu_surf, waveform, fft, beat, tick)
            frames += 1
            tick += 1
        cpu_fps = frames / (time.perf_counter() - start)
        
        # GL Test
        gl_fps = None
        if renderer:
            vis_gl = VisCls(renderer=renderer)
            start = time.perf_counter()
            frames = 0
            end_time = start + duration_s
            while time.perf_counter() < end_time:
                # In our app, even GL mode draws UI to a surface
                # But effects draw to context.
                vis_gl.draw(gl_target, waveform, fft, beat, tick)
                # Composite (as in main loop)
                renderer.blit(gl_target)
                gl_target.fill((0, 0, 0, 0))
                frames += 1
                tick += 1
            gl_fps = frames / (time.perf_counter() - start)
            
        results.append((name, cpu_fps, gl_fps))
        print(f" Done. (CPU: {cpu_fps:6.1f} fps" + (f" | GL: {gl_fps:6.1f} fps" if gl_fps else "") + ")")

    print("\n" + "="*60)
    print(f"{'Effect':15} | {'CPU FPS':10} | {'GL FPS':10} | {'Speedup':8}")
    print("-" * 60)
    for name, cpu, gl in results:
        speedup = f"{gl/cpu:7.2f}x" if gl else "N/A"
        gl_str = f"{gl:10.1f}" if gl else "N/A"
        print(f"{name:15} | {cpu:10.1f} | {gl_str:10} | {speedup}")
    print("="*60)

if __name__ == "__main__":
    run_benchmark()
