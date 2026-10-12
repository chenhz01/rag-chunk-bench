#!/usr/bin/env python3
"""Self-tests for rag-chunk-bench. Run: python self_test.py"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core

CASES = []


def case(fn):
    CASES.append(fn)
    return fn


def expect(cond, msg="assertion failed"):
    if not cond:
        raise AssertionError(msg)


def expect_raises(exc, fn, *a, **kw):
    try:
        fn(*a, **kw)
    except exc:
        return
    raise AssertionError("expected %s to be raised" % exc.__name__)


DOC = ("# Intro\nalpha beta gamma delta epsilon zeta eta theta.\n"
       "# Body\nThe quick brown fox jumps over the lazy dog. "
       "Pack my box with five dozen liquor jugs.\n"
       "# Notes\nshort tail\n")


# ---------- functional: chunk_fixed ----------

@case
def t_fixed_basic():
    chunks = core.chunk_fixed("abcdefghij", size=4, overlap=0)
    expect(chunks == ["abcd", "efgh", "ij"], "got %r" % chunks)


@case
def t_fixed_text_smaller_than_size():
    expect(core.chunk_fixed("hi", size=200) == ["hi"], "single chunk")


@case
def t_fixed_size_one():
    expect(core.chunk_fixed("abc", size=1) == ["a", "b", "c"], "size 1")


@case
def t_fixed_exact_multiple():
    chunks = core.chunk_fixed("abcd" * 2, size=4, overlap=0)
    expect(chunks == ["abcd", "abcd"], "got %r" % chunks)


@case
def t_fixed_empty_text():
    expect(core.chunk_fixed("", size=4) == [], "empty text")


@case
def t_fixed_unicode():
    chunks = core.chunk_fixed("你好世界 Ünïcode ✓ 文字", size=5, overlap=0)
    expect("".join(chunks) == "你好世界 Ünïcode ✓ 文字", "lossless join fails")


@case
def t_fixed_size_zero_raises():
    expect_raises(ValueError, core.chunk_fixed, "abc", 0)


@case
def t_fixed_negative_overlap_raises():
    expect_raises(ValueError, core.chunk_fixed, "abc", 4, -1)


@case
def t_fixed_overlap_gte_size_raises():
    expect_raises(ValueError, core.chunk_fixed, "abc", 4, 4)


# ---------- functional: overlap ----------

@case
def t_overlap_windows():
    chunks = core.chunk_fixed("abcdefghij", size=6, overlap=3)
    expect(chunks[0] == "abcdef" and chunks[1] == "defghi",
           "windows: %r" % chunks)


@case
def t_overlap_join_not_lossless():
    chunks = core.chunk_fixed("abcdefghij", size=6, overlap=3)
    expect("".join(chunks) != "abcdefghij", "overlap must duplicate")


# ---------- functional: structure ----------

@case
def t_structure_no_cross_heading():
    chunks = core.chunk_structure(DOC, size=60)
    body = [c for c in chunks if "quick brown fox" in c]
    expect(body and "alpha beta gamma" not in body[0],
           "sections mixed: %r" % body)


@case
def t_structure_without_headings():
    chunks = core.chunk_structure("plain text only " * 5, size=20)
    expect(len(chunks) >= 2, "should still pack: %r" % chunks)


@case
def t_structure_all_content_kept():
    chunks = core.chunk_structure(DOC, size=80)
    joined = "\n".join(chunks)
    expect("alpha beta gamma" in joined and "short tail" in joined,
           "content lost")


@case
def t_structure_overlong_line_kept_whole():
    line = "L" * 500
    chunks = core.chunk_structure("# H\n" + line + "\n", size=100)
    expect(any(line in c for c in chunks), "overlong line cut")


@case
def t_structure_size_zero_raises():
    expect_raises(ValueError, core.chunk_structure, "abc", 0)


# ---------- functional: sentences (round-2 addition retained in v0.1.1) --

@case
def t_sentences_no_mid_sentence_cut():
    text = ("First sentence ends here. Second sentence also ends here. "
            "Third one ends too.")
    chunks = core.chunk_sentences(text, size=30)
    for c in chunks:
        s = text.find(c)
        if s > 0 and text[s - 1].isalnum() and text[s].isalnum():
            raise AssertionError("mid-sentence cut at %r" % c)


@case
def t_sentences_all_content_kept():
    chunks = core.chunk_sentences(DOC, size=40)
    expect("quick brown fox" in "\n".join(chunks), "sentence content lost")


@case
def t_sentences_size_zero_raises():
    expect_raises(ValueError, core.chunk_sentences, "abc", 0)


# ---------- functional: metrics ----------

@case
def t_containment_clean_is_one():
    m = core.metrics(DOC, core.chunk_fixed(DOC, size=50))
    expect(m["containment"] == 1.0, "containment: %r" % m)


@case
def t_corruption_detected():
    m = core.metrics(DOC, ["# Intro", "NOT-IN-DOC", "# Body"])
    expect(m["containment"] < 1.0, "corruption not detected: %r" % m)


@case
def t_exact_restore_true_fixed():
    m = core.metrics(DOC, core.chunk_fixed(DOC, size=64))
    expect(m["exact_restore"] is True, "fixed should restore exactly")


@case
def t_exact_restore_false_overlap():
    m = core.metrics(DOC, core.chunk_fixed(DOC, size=64, overlap=16))
    expect(m["exact_restore"] is False, "overlap should not restore")


@case
def t_boundary_violation_counted():
    m = core.metrics("abcd efgh", ["cd e"])
    expect(m["boundary_violations"] == 1, "violation: %r" % m)


@case
def t_boundary_aligned_zero():
    m = core.metrics("abcd efgh", ["abcd ", "efgh"])
    expect(m["boundary_violations"] == 0, "aligned chunks flagged")


@case
def t_uniformity_equal_chunks_one():
    m = core.metrics(DOC, core.chunk_fixed(DOC, size=50))
    expect(m["uniformity"] == 1.0, "uniformity: %r" % m)


@case
def t_uniformity_varied_lower():
    m = core.metrics(DOC, core.chunk_fixed(DOC, size=50, overlap=25))
    expect(m["uniformity"] <= 1.0, "uniformity must be capped at 1")


@case
def t_duplication_zero_for_fixed():
    m = core.metrics(DOC, core.chunk_fixed(DOC, size=50))
    expect(m["duplication"] == 0.0, "fixed duplication: %r" % m)


@case
def t_duplication_positive_for_overlap():
    m = core.metrics(DOC, core.chunk_fixed(DOC, size=64, overlap=32))
    expect(m["duplication"] > 0.0, "overlap duplication: %r" % m)


@case
def t_score_bounds():
    m = core.metrics(DOC, core.chunk_fixed(DOC, size=40))
    expect(0.0 <= m["score"] <= 100.0, "score: %r" % m)


@case
def t_metrics_empty_chunks():
    m = core.metrics(DOC, [])
    expect(m["n_chunks"] == 0 and m["score"] == 0.0, "empty: %r" % m)


@case
def t_metrics_deterministic():
    a = core.metrics(DOC, core.chunk_fixed(DOC, size=40))
    b = core.metrics(DOC, core.chunk_fixed(DOC, size=40))
    expect(a == b, "metrics must be deterministic")


# ---------- functional: bench ----------

@case
def t_bench_all_strategies():
    rows = core.bench(DOC, size=64, overlap=16)
    expect([r["strategy"] for r in rows] ==
           ["fixed", "overlap", "structure", "sentences"], "rows: %r" % rows)


@case
def t_bench_subset():
    rows = core.bench(DOC, size=64, strategies=["fixed"])
    expect(len(rows) == 1 and rows[0]["strategy"] == "fixed", "subset")


@case
def t_bench_unknown_strategy_raises():
    expect_raises(ValueError, core.bench, DOC, strategies=["nope"])


@case
def t_bench_deterministic():
    expect(core.bench(DOC, size=64) == core.bench(DOC, size=64),
           "bench must be deterministic")


@case
def t_bench_json_serializable():
    s = json.dumps(core.bench(DOC, size=64), ensure_ascii=True,
                   sort_keys=True)
    expect("strategy" in s, "serialization failed")


@case
def t_huge_text_fast():
    text = ("Sentence one is here. Sentence two follows it.\n" * 4000)
    rows = core.bench(text, size=200, overlap=50)
    expect(all(r["n_chunks"] > 0 for r in rows), "huge text failed")


# ---------- CLI ----------

def _tmp_file(text):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "doc.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


@case
def t_cli_json_ok():
    expect(core.main(["--input", _tmp_file(DOC)]) == 0, "json run failed")


@case
def t_cli_table_ok():
    expect(core.main(["--input", _tmp_file(DOC), "--format", "table"]) == 0,
           "table run failed")


@case
def t_cli_missing_input_exit_two():
    expect(core.main(["--input", "Z:/no/doc.md"]) == 2, "missing exits 2")


@case
def t_cli_bad_size_exit_two():
    expect(core.main(["--input", _tmp_file(DOC), "--size", "0"]) == 2,
           "size 0 exits 2")


@case
def t_cli_bad_strategy_exit_two():
    expect(core.main(["--input", _tmp_file(DOC),
                      "--strategies", "nope"]) == 2, "bad strategy exits 2")


@case
def t_cli_custom_params():
    expect(core.main(["--input", _tmp_file(DOC), "--size", "32",
                      "--overlap", "8", "--strategies",
                      "fixed,overlap"]) == 0, "params run failed")


@case
def t_cli_unicode_doc():
    expect(core.main(["--input",
                      _tmp_file("你好世界。第二句在这里。# 标题\n正文内容。")]) == 0,
           "unicode doc failed")


def run():
    ok = 0
    for i, fn in enumerate(CASES, 1):
        try:
            fn()
            ok += 1
        except Exception as e:
            print("FAIL %02d %s: %s: %s" % (i, fn.__name__,
                                            type(e).__name__, e))
    total = len(CASES)
    print("SUMMARY: %s %d/%d" % ("PASS" if ok == total else "FAIL", ok, total))
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(run())
