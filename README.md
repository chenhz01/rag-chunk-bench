# rag-chunk-bench

A reproducible benchmark for RAG chunking strategies: fixed-size windows,
sliding overlap, structure-aware (heading) packing, and sentence-aware
packing, scored over restoration metrics — containment, exact
restorability, word-boundary integrity, packing uniformity, and duplication.
Deterministic, pure standard library, zero model calls. Confidence: high
for metrics and determinism; metric *usefulness* for retrieval quality is
medium (see Limits).

as of 2026-10-11

## Problem

Teams pick a chunking strategy by vibes — "512 with 64 overlap, sure" —
and discover later that half their chunks cut sentences mid-word or that
overlapping settings double their storage. Published comparisons exist but
are tied to embeddings, models, and downloaded corpora, so results are not
reproducible offline. What is missing is a tiny, deterministic harness that
scores chunkers on text-restoration properties you can reason about.

## How it works

- **Strategies**: `fixed` (back-to-back slices, lossless), `overlap`
  (sliding window), `structure` (markdown-`#` heading aware packing that
  never mixes sections; overlong lines kept whole), `sentences` (pack on
  sentence boundaries, never cut inside a sentence).
- **Metrics** per strategy:
  - `containment`: fraction of chunks that appear verbatim in the source.
  - `exact_restore`: `"".join(chunks) == text` (losslessness).
  - `boundary_violations`: chunk starts that cut a word in half.
  - `uniformity`: 1 − (size stddev / mean), packing evenness.
  - `duplication`: 1 − (union of chunk spans)/(sum of chunk lengths);
    0 for lossless, grows with overlap.
  - `score`: containment × boundary-integrity × 100 + exact-restore bonus,
    capped at 100.
- **Determinism**: no randomness anywhere; identical input → identical
  rows, byte for byte.

## Quickstart

```bash
python core.py --input doc.md --format table          # all strategies (~1 s)
python core.py --input doc.md --size 512 --overlap 64 (~1 s)
python self_test.py                                   # ~55 cases (~3 s)
```

## Why not X

| Alternative | Stars (as of 2026-10-11) | How this differs |
| --- | --- | --- |
| [joshuaazzs/rag-chunking-benchmark](https://github.com/joshuaazzs/rag-chunking-benchmark) | 0 | Compares recursive/sliding-window/semantic chunking aimed at retrieval quality; this repo needs no embeddings or downloads — it scores restoration properties deterministically on any local text. |
| [koriannsq/rag-chunking-benchmark](https://github.com/koriannsq/rag-chunking-benchmark) | 0 | Same retrieval-oriented comparison shape; this repo adds losslessness/duplication accounting so the *storage cost* of overlap is visible next to its benefit. |
| [harsh462003/RAG-Chunking-Benchmark](https://github.com/harsh462003/RAG-Chunking-Benchmark) | 0 | A full benchmarking framework spanning multiple strategies and pipelines; this repo is a single-file, stdlib-only harness you can run in CI in seconds. |

Anchors found via search as of 2026-10-11; descriptions paraphrased.

## Minimal Fallback

No harness? Chunk manually and check two properties by eye: concatenate
your chunks and diff against the source (catches loss/reordering), and
inspect a few boundaries for mid-word cuts. That is `exact_restore` and
`boundary_violations` with eyeballs instead of metrics.

## Design Trade-offs

- Restoration metrics over retrieval metrics: zero dependencies and full
  determinism, but a high score does not guarantee better recall — it
  guarantees your chunks preserve the document faithfully.
- Heading heuristic is markdown-`#` only: simple and predictable; HTML or
  LaTeX structure needs a custom splitter.
- Score is a weighted composite: convenient for ranking, but read the
  per-metric columns before deciding.

## Limits & Second-order Effects

- Restoration quality is a *proxy*; semantic chunking tuned to your
  embedder can beat every strategy here on real retrieval benchmarks.
- `structure` never mixes sections, which can produce many tiny chunks on
  heading-dense documents and inflate index size.
- Second-order effect: optimizing `uniformity` alone pushes toward fixed
  windows, quietly sacrificing semantic boundaries.

## FAQ

**Does it call an LLM or embed anything?**
No. It is pure text arithmetic — that is what makes it reproducible.

**When NOT to use this?**
When you need end-to-end retrieval quality numbers (precision/recall over
a labeled QA set) or semantic chunking evaluation — use an embedding-based
benchmark instead.

**Can I add my own strategy?**
Implement `fn(text, size, overlap) -> list[str]` and register it in
`STRATEGIES`; the metrics run unchanged.

## Core Assumptions

- [A1] Faithful restoration of the source document is a desirable baseline
  property of any chunker.
- [A2] Markdown-ish `#` headings are meaningful section boundaries for the
  target corpus.
- [A3] Determinism matters more than throughput for CI-sized documents.

Confidence: metric implementation high; correlation with retrieval quality
medium. All claims as of 2026-10-11.

---

Part of the [zhengming-toolbox](https://github.com/chenhz01/zhengming-toolbox) — 55 purpose-built AI-engineering tools across neglected niches.

Related tools: [agent-audit-trail](https://github.com/chenhz01/agent-audit-trail) · [tool-call-replay](https://github.com/chenhz01/tool-call-replay) · [model-capability-matrix](https://github.com/chenhz01/model-capability-matrix)
