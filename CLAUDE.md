# Project rules

## Release cycle

After completing any feature or fix work, always follow this release cycle in order:

1. **Bump minor version** — update the version number in `README.md` (badge) and add a new entry at the top of `CHANGELOG.md`. Minor bump: `x.y.z → x.(y+1).0`.
2. **Update all docs** — ensure `README.md` (What's new section, modes table, project structure) and `CHANGELOG.md` are accurate and complete.
3. **Update qmd index** — run `qmd update` so the local search index reflects all changes.
4. **Push to dev** — commit all changes on the `dev` branch and push: `git push origin dev`.
5. **Sync to main** — merge dev into main and push: `git checkout main && git merge dev && git push origin main && git checkout dev`.

## Effect order

**Spectrum and Waterfall must always be the last two entries in `MODES`** (in `effects/__init__.py`), in that order: Spectrum second-to-last, Waterfall last. When adding new effects, insert them before Spectrum.
