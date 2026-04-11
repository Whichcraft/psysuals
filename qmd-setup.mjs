import { createStore } from '@tobilu/qmd'

/** @import { UpdateProgress, EmbedProgress } from '@tobilu/qmd' */

const store = await createStore({
  dbPath: './qmd.sqlite',
  configPath: './qmd.yml',
})

// Global context
await store.setGlobalContext(
  'Desktop audio visualizer (Python, pygame + sounddevice). Captures system audio in real time, computes FFT, drives 16 full-screen visual effects. Entry: psysualizer.py. Effects in effects/.',
)

// source collection
await store.addContext('source', '/', 'psysualizer.py: audio capture thread (sounddevice) → FFT analysis → beat detection → effect dispatch loop (pygame). config.py: shared mutable globals (WIDTH, HEIGHT, FPS, SAMPLE_RATE, BLOCK_SIZE, CHANNELS)')

// effects collection
await store.addContext('effects', '/', '16 visual effect modules, each implementing draw(surf, waveform, fft, beat, tick). Registry and MODES list in __init__.py. Rule: Spectrum and Waterfall must always be the last two entries in MODES, in that order. effects/utils.py: shared drawing utilities')

// docs collection
await store.addContext('docs', '/', 'ARCHITECTURE.md (entry point + threading model), EFFECTS.md (per-effect parameter and behaviour docs), CHANGELOG.md, README.md')

// Index + embed
await store.update({
  onProgress: /** @param {UpdateProgress} p */ ({ collection, file, current, total }) =>
    process.stdout.write(`\r[${collection}] ${current}/${total} ${file}`),
})
console.log()

await store.embed({
  chunkStrategy: 'auto',
  onProgress: /** @param {EmbedProgress} p */ ({ current, total, collection }) =>
    process.stdout.write(`\r[${collection}] embedding ${current}/${total}`),
})
console.log()

await store.close()
console.log('qmd index ready.')
