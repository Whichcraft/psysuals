# Project rules

## Release cycle

After completing any feature or fix work, always follow this release cycle in order:

1. **Develop on dev** — always perform work on the `dev` branch.
2. **Verify with smoke test** — run `.venv/bin/python smoke_test.py` to ensure all effects and entrypoints are functional.
3. **Bump minor version** — update the version number in `README.md` (badge), `psysualizer.py` (`__version__`), and add a new entry at the top of `CHANGELOG.md`. Minor bump: `x.y.z → x.(y+1).0`.
4. **Update all docs** — ensure `README.md` (What's new section, modes table, project structure), `EFFECTS.md`, `ARCHITECTURE.md`, and `CHANGELOG.md` are accurate and complete.
5. **Update qmd index** — run `node qmd-setup.mjs` (or use local `qmd` tools) so the local search index and embeddings reflect all changes.
6. **Push to dev** — commit all changes on the `dev` branch and push: `git push origin dev`.
7. **Sync to main** — merge dev into main and push: `git checkout main && git merge dev && git push origin main && git checkout dev`.

## Architecture & Rendering

- **Unified Entry Point:** `psysualizer.py` is the only supported entry point. It handles both CPU and GPU paths via the `--gl` flag.
- **Effect Contract:** All effects MUST inherit from `effects.base.Effect`.
- **Initialization:** All `__init__` methods must accept `**kwargs` and call `super().__init__(**kwargs)` to properly handle the optional `renderer`.
- **GL Support:** Prefer adding GLSL paths to existing effects (e.g., `PlasmaGL`) rather than creating separate files when possible.

## Android integration (androsaver)

These visuals will be used in an Android live wallpaper / screensaver app
called **androsaver** (Kotlin/Java).  Keep this in mind when touching the
python code: simple math, avoiding heavy new dependencies, keeping
drawing code self-contained.

## Assistant workflow

When practical, prefer using `~/bin/codebot.sh` for broad repo analysis,
ranking, brainstorming, and first-pass diagnosis to save local model tokens.
Keep final code edits, local debugging, and verification in the repo itself.

## Effect order

**Spectrum and Waterfall must always be the last two entries in `MODES`** (in `effects/__init__.py`), in that order: Spectrum second-to-last, Waterfall last. When adding new effects, insert them before Spectrum.
