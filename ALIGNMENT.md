# ALIGNMENT.md — R13 alignment record (16 items)

Design source: `_r13_design.json` → repo `rag-chunk-bench`,
domain RAG分块基准, sim `adjacent`. Date of record: 2026-10-11.

| # | Item | Evidence |
| --- | --- | --- |
| 1 | Repo name matches design entry | Directory `rag-chunk-bench` == design JSON `name`. |
| 2 | Mechanism implemented as specified | Design mechanism "固定/重叠/结构感知三策略在还原率指标上的可复现对比架" → `chunk_fixed/chunk_overlap(overlap)/chunk_structure` over restoration metrics in core.py. |
| 3 | Pure Python standard library only | Imports: argparse, json, re, sys (+ os/tempfile in tests). |
| 4 | CLI entry via argparse | `core.py --input [--size --overlap --strategies --format]`; README quickstart runs as written. |
| 5 | self_test.py ≥40 cases, three categories | Functional (strategies, metrics, bench), exception paths (bad size/overlap/strategy, CLI errors), extreme edge (empty text, size=1, 500-char single line, 8000-line doc, unicode, determinism byte-for-byte). |
| 6 | Final line `SUMMARY: PASS n/n` | `python self_test.py` ends with that exact line. |
| 7 | README first paragraph ≤60 words | Intro ~55 words (counted 2026-10-11). |
| 8 | README required sections present | All mandated sections incl. FAQ "When NOT to use" and 3 Core Assumptions. |
| 9 | why-not-X ≥3 alternatives with real anchors | Table lists joshuaazzs/rag-chunking-benchmark (0★), koriannsq/rag-chunking-benchmark (0★), harsh462003/RAG-Chunking-Benchmark (0★) with stars from design JSON; differences paraphrased. |
| 10 | MIT LICENSE, "zhengming contributors" | LICENSE copyright line as required; no real names. |
| 11 | CHANGELOG v0.1.0 → v0.1.1 | CHANGELOG.md documents both versions dated 2026-10-11. |
| 12 | Two-round iteration, ≥1 dimension ≥20% | Round 2 added strategy `sentences` + metric `duplication` — strategy count 3 → 4 (+33%), metrics 5 → 6 (+20%) — plus 11 new tests. Recorded in CHANGELOG v0.1.1. |
| 13 | Number discipline | Metric definitions given as formulas in README; test counts reproducible via `python self_test.py`; no unverifiable perf claims. |
| 14 | Zero secrets / zero real names | No keys; "zhengming contributors" copyright. |
| 15 | No >50-char text copied from anchors | Anchor facts reduced to name + stars + paraphrased difference. |
| 16 | as-of date marked | README headline and Confidence footer say "as of 2026-10-11". |
