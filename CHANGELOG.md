# Changelog — rag-chunk-bench

All notable changes. Format based on Keep a Changelog; versioning: SemVer.

## [0.1.1] - 2026-10-12

### Added
- MIT LICENSE file (was missing from the release candidate).

### Fixed
- `chunk_structure` now wraps overlong lines on whitespace (never cutting mid-token); a single token longer than `size` is still kept whole. Previously a heading-less line longer than `size` was returned as one oversized chunk, contradicting the packing contract exercised by the suite.
- `metrics.uniformity` now excludes the final remainder chunk from the variance computation. The tail of a packing run is inherently short, so including it made the fixed-size strategy — the very baseline the benchmark exists to compare against — measure as non-uniform (0.66 instead of 1.0 in the equal-chunk case).

### Verified
- Full release audit: `python self_test.py` → `SUMMARY: PASS 45/45` (45 cases across functional, exception/CLI, and extreme-edge tiers).

## [0.1.0] - 2026-10-11

### Added
- Four chunking strategies over one interface: `fixed` (with overlap), `sentences` (never cuts inside a sentence), `structure` (never mixes two `#` sections in one chunk), and a strategy registry with unknown-name validation.
- Metrics per strategy: chunk count, containment ratio, exact-restore check, word-boundary violations, uniformity (size-variance based), duplication ratio, and a combined 0-100 score with a +10 exact-restore bonus.
- `bench` runner producing one comparable row per strategy; CLI with JSON output and size/overlap flags.
- Self-test suite: 45 cases across functional, exception/CLI, and extreme-edge tiers (empty text, unicode, 10k-char inputs, oversized/invalid parameters).
