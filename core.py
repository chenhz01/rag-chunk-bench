#!/usr/bin/env python3
"""rag-chunk-bench: reproducible benchmark for RAG chunking strategies.

Compares fixed-size, sliding-overlap, and structure-aware chunking over
restoration metrics: containment, exact restorability, word-boundary
integrity, and packing uniformity, combined into a single score.
Deterministic, pure standard library, no model calls, no network.
"""
import argparse
import json
import re
import sys


# ---------------- strategies ----------------

def chunk_fixed(text, size=200, overlap=0):
    """Fixed-size windows; overlap=0 gives lossless back-to-back slices."""
    if size <= 0:
        raise ValueError("size must be a positive integer")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must satisfy 0 <= overlap < size")
    step = size - overlap
    return [text[i:i + size] for i in range(0, len(text), step)]


def split_sections(text):
    """Split markdown-ish text on '#' heading lines."""
    sections, cur = [], []
    for ln in text.splitlines():
        if ln.lstrip().startswith("#") and cur:
            sections.append("\n".join(cur))
            cur = []
        cur.append(ln)
    if cur:
        sections.append("\n".join(cur))
    return sections


def chunk_structure(text, size=200):
    """Heading-aware packing: never mixes two sections in one chunk;
    packs section lines up to `size` characters. Overlong lines are wrapped
    on whitespace when possible (never cut mid-token); a single token longer
    than `size` is kept whole rather than cut."""
    if size <= 0:
        raise ValueError("size must be a positive integer")
    chunks = []
    for sec in split_sections(text):
        buf = ""
        for ln in sec.splitlines():
            for piece in _wrap_line(ln, size):
                cand = (buf + "\n" + piece) if buf else piece
                if len(cand) > size and buf:
                    chunks.append(buf)
                    buf = piece
                else:
                    buf = cand
        if buf.strip():
            chunks.append(buf)
    return chunks


def _wrap_line(ln, size):
    """Split an overlong line on whitespace; keep space-free tokens whole."""
    if len(ln) <= size:
        return [ln]
    words = ln.split(" ")
    if len(words) <= 1:
        return [ln]
    out, cur = [], ""
    for w in words:
        cand = (cur + " " + w) if cur else w
        if len(cand) > size and cur:
            out.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        out.append(cur)
    return out


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def chunk_sentences(text, size=200):
    """Sentence-aware packing: split on sentence enders, pack up to size;
    never cuts inside a sentence."""
    if size <= 0:
        raise ValueError("size must be a positive integer")
    chunks, buf = [], ""
    for sent in _SENT_SPLIT.split(text):
        cand = (buf + " " + sent) if buf else sent
        if len(cand) > size and buf:
            chunks.append(buf)
            buf = sent
        else:
            buf = cand
    if buf.strip():
        chunks.append(buf)
    return chunks


STRATEGIES = {
    "fixed": lambda t, s, o: chunk_fixed(t, s, o),
    "overlap": lambda t, s, o: chunk_fixed(t, s, max(1, min(o, s - 1))),
    "structure": lambda t, s, o: chunk_structure(t, s),
    "sentences": lambda t, s, o: chunk_sentences(t, s),
}


# ---------------- metrics ----------------

def _find_start(text, chunk, floor):
    start = text.find(chunk, floor)
    if start == -1:
        start = text.find(chunk)
    return start


def word_boundary_violations(text, chunks):
    """Chunk starts that cut a word in half (alnum on both sides)."""
    violations = 0
    floor = 0
    for c in chunks:
        start = _find_start(text, c, floor)
        if start > 0 and text[start - 1].isalnum() and text[start].isalnum():
            violations += 1
        floor = max(floor, start)
    return violations


def containment_ratio(text, chunks):
    if not chunks:
        return 0.0
    contained = sum(1 for c in chunks if c and c in text)
    return contained / len(chunks)


def duplication_ratio(text, chunks):
    """1 - (union of chunk spans) / (sum of chunk lengths). Zero for
    lossless strategies; grows with overlap."""
    spans = []
    floor = 0
    for c in chunks:
        start = _find_start(text, c, floor)
        if start == -1:
            continue
        spans.append((start, start + len(c)))
        floor = start
    if not spans:
        return 0.0
    spans.sort()
    merged, cur_s, cur_e = 0, spans[0][0], spans[0][1]
    for s, e in spans[1:]:
        if s > cur_e:
            merged += cur_e - cur_s
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    merged += cur_e - cur_s
    total = sum(len(c) for c in chunks)
    if total == 0:
        return 0.0
    return max(0.0, 1.0 - merged / total)


def metrics(text, chunks):
    if not chunks:
        return {"n_chunks": 0, "containment": 0.0, "exact_restore": False,
                "boundary_violations": 0, "uniformity": 0.0,
                "duplication": 0.0, "score": 0.0}
    sizes = [len(c) for c in chunks]
    core_sizes = sizes[:-1] if len(sizes) > 1 else sizes
    mean = sum(core_sizes) / len(core_sizes)
    var = sum((s - mean) ** 2 for s in core_sizes) / len(core_sizes)
    uniformity = max(0.0, 1.0 - (var ** 0.5) / mean) if mean else 0.0
    viol = word_boundary_violations(text, chunks)
    cont = containment_ratio(text, chunks)
    score = (100.0 * cont
             * (1.0 - viol / max(1, len(chunks) - 1))
             + (10.0 if "".join(chunks) == text else 0.0))
    score = max(0.0, min(100.0, score))
    return {"n_chunks": len(chunks), "containment": round(cont, 4),
            "exact_restore": "".join(chunks) == text,
            "boundary_violations": viol, "uniformity": round(uniformity, 4),
            "duplication": round(duplication_ratio(text, chunks), 4),
            "score": round(score, 2)}


def bench(text, size=200, overlap=50, strategies=None):
    """Run all (or selected) strategies; returns one metrics row each."""
    names = strategies or list(STRATEGIES)
    unknown = [n for n in names if n not in STRATEGIES]
    if unknown:
        raise ValueError("unknown strategies: %s" % ", ".join(unknown))
    rows = []
    for name in names:
        chunks = STRATEGIES[name](text, size, overlap)
        rows.append({"strategy": name, **metrics(text, chunks)})
    return rows


# ---------------- CLI ----------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="rag-chunk-bench",
        description="Benchmark RAG chunking strategies over restoration "
                    "metrics (deterministic, no model calls).")
    parser.add_argument("--input", required=True, help="text file to chunk")
    parser.add_argument("--size", type=int, default=200)
    parser.add_argument("--overlap", type=int, default=50)
    parser.add_argument("--strategies", default="fixed,overlap,structure,sentences",
                        help="comma-separated subset")
    parser.add_argument("--format", choices=("json", "table"), default="json")
    args = parser.parse_args(argv)

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            text = f.read()
        rows = bench(text, size=args.size, overlap=args.overlap,
                     strategies=[s.strip() for s in
                                 args.strategies.split(",") if s.strip()])
    except OSError as e:
        print("error: cannot read input: %s" % e, file=sys.stderr)
        return 2
    except ValueError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2

    if args.format == "table":
        header = ("%-10s %7s %6s %8s %6s %8s %8s %8s"
                  % ("strategy", "n", "contain", "restore", "bound",
                     "uniform", "dup", "score"))
        print(header)
        for r in rows:
            print("%-10s %7d %6.2f %8s %6d %8.4f %8.4f %8.2f"
                  % (r["strategy"], r["n_chunks"], r["containment"],
                     r["exact_restore"], r["boundary_violations"],
                     r["uniformity"], r["duplication"], r["score"]))
    else:
        print(json.dumps(rows, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
