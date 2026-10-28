#!/usr/bin/env python3
"""PGER V9.5 controlled, *lexical* set-workspace pilot. No verifier, oracle or LLM.

Two BM25 follow-up searches maximum per non-fast arm; same public SAG2
released corpus and identical passage IDs. This is NOT sealed evidence,
open-world answer verification, or a claimed novel retrieval algorithm.

Precommitted question offsets: [640,760) development, [760,880)
confirmation; previous full V7.1 run has already examined 0..999.
"""
import argparse
import collections
import json
import pathlib
import re
import statistics
import time
import numpy as np

from benchmark_v71_sag2_corpus import download, official_records, SAG2_AUTHOR, RELEASE
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger
from expansion_v92 import propose, rank_fuse, terms
from set_workspace_v95 import Workspace

SEED = 20261028
ARM_NAMES = ("v71_fast", "v92_two_query", "positive_only", "retained_negative", "lexical_gap")
DEV = (640, 760)
CONFIRM = (760, 880)
K_BM = 40
MAX_EXTRA_QUERIES = 2
SOURCE_LIMIT = 2100
RERANK_CANDIDATES = 80
PROTECT = 2
# These are exploratory lexical heuristics, not semantic or decision verification.
NEGATIVE_RESCUE_OVERLAP = .42
NEGATIVE_RESCUE_LINK_BONUS = .008

def cpu_ms(t0):
    return 1000.0 * (time.process_time() - t0)

def unique(seq):
    return list(dict.fromkeys(seq))

def initial(q, methods, graph):
    t = time.process_time()
    raw = methods.index.search(q, "bm25", 100)
    bm = [i for i, _ in raw] or list(range(min(100, len(methods.docs))))
    fast, _ = graph.search(q, bm, mode="one-hop", bmraw=raw)
    return bm, unique(fast), cpu_ms(t)

def two_actions(q, methods, fast, kind="mixed"):
    """No gold/doc labels: proposals are grounded in first-pass passage text."""
    proposed = propose(q, methods.docs, fast, methods.index.idfs,
                       kind=kind, seed_n=4, k=MAX_EXTRA_QUERIES)
    t = time.process_time()
    hits, actions = [], []
    for p in proposed[:MAX_EXTRA_QUERIES]:
        ids = [i for i, _ in methods.index.search(p["term"], "bm25", K_BM)]
        hits.append(ids)
        actions.append({"query":p["term"], "witness_doc":p["witness_doc"],
                        "witness_sentence":p["sentence_index"],
                        "witness_quote":p["quote"], "found":len(ids)})
    assert len(actions) <= MAX_EXTRA_QUERIES
    return hits, actions, cpu_ms(t)

def q_overlap(q, d, idf):
    wanted = set(terms(q))
    if not wanted:
        return 0.0
    observed = set(terms(str(d["title"]) + " " + d.get("text", "")[:SOURCE_LIMIT]))
    return sum(idf.get(t, 0.0) for t in wanted & observed) / max(
        .0001, sum(idf.get(t, 0.0) for t in wanted))

def scoped_order(q, methods, graph, fast, bm, hits, actions, retained=False):
    """Independent invocation for each arm; no information from gold.

    positive_only prioritizes the positive lexical partition, then
    preserves excluded documents as fallback.
    retained_negative preserves that complement in a named workspace and
    admits strongly question-linked or title-linked exclusions for rescue.
    Missing substring is only a LEXICAL negative, not a refuted fact.
    """
    t = time.process_time()
    fused = unique(rank_fuse(fast, bm, hits, mode="fuse",
                              strength=.4, protect=PROTECT, cutoff=150))
    pool = unique(fused[:RERANK_CANDIDATES] + fast[:RERANK_CANDIDATES] +
                  bm[:RERANK_CANDIDATES] + [i for h in hits for i in h])
    ws = Workspace({str(i): methods.docs[i]["title"] + "\n" +
                    methods.docs[i].get("text", "")[:SOURCE_LIMIT] for i in pool})
    yes = set()
    diagnostics = []
    for j, action in enumerate(actions):
        p = ws.partition("all", re.escape(action["query"]), "anchor" + str(j),
                         anchor_tokens=terms(q)[:5])
        yes.update(int(x) for x in ws.get(p.positive))
        assert p.complement_checked and ws.verify_matches(p.positive)
        diagnostics.append({"anchor":action["query"], "positive":p.positive_count,
                            "excluded":p.negative_count,
                            "excluded_query_anchor_warnings":p.rejected_anchor_count})
    no = set(pool) - yes
    protected = unique(fast[:PROTECT])
    if not actions:
        return fast, {"pool":pool, "positive":[], "negative":pool,
                      "partitions":[], "cpu_ms":cpu_ms(t)}
    candidates = [i for i in fused if i not in protected]
    if not retained:
        # Positive-only control: aggressively prioritize matching candidates.
        ranking = protected + [i for i in candidates if i in yes] + \
                  [i for i in candidates if i not in yes]
    else:
        # Retained negative-set rescue. All heuristics frozen pre-run.
        # Include only source-text and indexed title-link signals, never gold.
        linked = {j for i in fast[:3] for j in graph.adj[i]}
        original_rank = {i: r for r, i in enumerate(fused)}
        def priority(i):
            match = i in yes
            overlap = q_overlap(q, methods.docs[i], methods.index.idfs)
            rescue = (i in no and (overlap >= NEGATIVE_RESCUE_OVERLAP or i in linked))
            return (1.0 / (25 + original_rank[i]) +
                    (.015 if match else 0.0) +
                    (.011 if rescue and overlap >= NEGATIVE_RESCUE_OVERLAP else 0.0) +
                    (NEGATIVE_RESCUE_LINK_BONUS if rescue and i in linked else 0.0))
        ranking = protected + sorted(candidates, key=lambda i: (-priority(i), original_rank[i]))
    ranking = unique(ranking + fast + bm)
    assert len(ranking) == len(set(ranking))
    return ranking, {"pool":pool, "positive":sorted(yes), "negative":sorted(no),
                      "partitions":diagnostics, "cpu_ms":cpu_ms(t)}

def lexical_gap(q, methods, graph, fast, bm):
    """Separately budget-matched, but UNVERIFIED lexical follow-up policy."""
    hits, actions, search_cpu = two_actions(q, methods, fast, kind="names")
    t = time.process_time()
    ranking = unique(rank_fuse(fast, bm, hits, mode="fuse",
                                strength=.4, protect=PROTECT, cutoff=150))
    return ranking, actions, search_cpu, cpu_ms(t)

def metric(ranking, ids, gold):
    observed = [ids[i] for i in ranking[:10]]
    return {
        "ae5": int(gold <= set(observed[:5])),
        "ae10": int(gold <= set(observed[:10])),
        "r5": len(gold & set(observed[:5])) / len(gold),
        "r10": len(gold & set(observed[:10])) / len(gold)
    }

def paired(a, b):
    d = np.asarray(a, float) - np.asarray(b, float)
    rng = np.random.default_rng(SEED)
    boot = [float(d[rng.integers(0, len(d), len(d))].mean()) for _ in range(3000)]
    return {"delta_pp": round(float(100 * d.mean()), 3),
            "ci95_pp": [round(float(100*x), 3) for x in np.quantile(boot, [.025, .975])],
            "wins": int((d > 0).sum()), "losses": int((d < 0).sum())}

def summarize(rows):
    result = {}
    for arm in ARM_NAMES:
        stats = {m: round(float(np.mean([r["metrics"][arm][m] for r in rows])), 6)
                 for m in ("ae5", "ae10", "r5", "r10")}
        for comp in ("v71_fast", "v92_two_query", "positive_only"):
            if arm != comp:
                stats["paired_vs_" + comp] = paired(
                    [r["metrics"][arm]["ae5"] for r in rows],
                    [r["metrics"][comp]["ae5"] for r in rows])
        stats["support_breakdown"] = {
            str(n): {"n": sum(r["gold_count"] == n for r in rows),
                     "ae5": sum(r["gold_count"] == n and r["metrics"][arm]["ae5"]
                                for r in rows)}
            for n in sorted(set(r["gold_count"] for r in rows))}
        extra = [r["timings"][arm]["total_cpu_ms"] for r in rows]
        stats["cpu_query_estimate_ms"] = {
            "mean": round(float(np.mean(extra)), 3),
            "p95": round(float(np.percentile(extra, 95)), 3)}
        stats["mean_extra_bm25_calls"] = round(float(np.mean(
            [r["timings"][arm]["extra_calls"] for r in rows])), 3)
        result[arm] = stats
    audits = {"n": len(rows)}
    for field in ("gold_in_initial_top80", "gold_in_shared_pool",
                  "gold_in_positive_partition", "gold_in_negative_partition",
                  "negative_gold_top5_rescues", "negative_full_chain_wins"):
        audits[field] = sum(r["audit"][field] for r in rows)
    return {"methods": result, "audits": audits}

def evaluate(name, root, out):
    file_hashes = download(name, root)
    unique_src, docs, questions = official_records(name, root)
    assert len(docs) == SAG2_AUTHOR[name]["corpus"] and len(questions) == 1000
    src = list(unique_src)
    t = time.process_time()
    methods = SparseMethods(docs)
    bm_index_cpu = cpu_ms(t)
    t = time.process_time()
    graph = EvidenceLedger(methods)
    graph_index_cpu = cpu_ms(t)
    for cohort, (start, end) in (("development", DEV), ("confirmation", CONFIRM)):
        rows = []
        for j, r in enumerate(questions[start:end]):
            q = r["question"]
            # Retrieval is complete before gold is ever accessed.
            bm, fast, fast_cpu = initial(q, methods, graph)
            hits, actions, search_cpu = two_actions(q, methods, fast)
            t = time.process_time()
            nearest = unique(rank_fuse(fast, bm, hits, mode="fuse",
                                       strength=.4, protect=PROTECT, cutoff=150))
            nearest_cpu = cpu_ms(t)
            positive, pos_diag = scoped_order(q, methods, graph, fast, bm,
                                              hits, actions, retained=False)
            retained, neg_diag = scoped_order(q, methods, graph, fast, bm,
                                              hits, actions, retained=True)
            gap, gap_actions, gap_search_cpu, gap_rank_cpu = lexical_gap(
                q, methods, graph, fast, bm)
            rankings = dict(zip(ARM_NAMES, (fast, nearest, positive, retained, gap)))
            gold = set(r["gold"])
            assert gold and gold <= set(src), "Unexpected gold source absent from corpus"
            scored = {arm: metric(ranking, src, gold) for arm, ranking in rankings.items()}
            to_src = lambda rank: {src[i] for i in rank}
            pool = neg_diag["pool"]
            positives = neg_diag["positive"]
            negatives = neg_diag["negative"]
            # Only evaluation/auditing uses gold. Never feed diagnostics into rankers.
            neg_gold_ids = {i for i in negatives if src[i] in gold}
            rec = {
                "id": r["id"], "question": q, "gold_count": len(gold),
                "metrics": scored, "top10_source_ids": {
                    arm: [docs[i]["_id"] for i in ranking[:10]]
                    for arm, ranking in rankings.items()},
                "search_actions": {"common": actions, "lexical_gap": gap_actions},
                "partition_diagnostics": neg_diag["partitions"],
                "audit": {
                    "gold_in_initial_top80": int(gold <= to_src(fast[:80])),
                    "gold_in_shared_pool": int(gold <= to_src(pool)),
                    "gold_in_positive_partition": int(gold <= to_src(positives)),
                    "gold_in_negative_partition": int(gold <= to_src(negatives)),
                    "negative_gold_top5_rescues": int(bool(
                        neg_gold_ids & set(retained[:5])) and
                        not (neg_gold_ids & set(positive[:5]))),
                    "negative_full_chain_wins": int(
                        scored["retained_negative"]["ae5"] >
                        scored["positive_only"]["ae5"]),
                    "missing_gold_at5_count": {
                        arm: len(gold - to_src(ranking[:5]))
                        for arm, ranking in rankings.items()}
                },
                "timings": {
                    "v71_fast": {"total_cpu_ms": fast_cpu, "extra_calls": 0},
                    "v92_two_query": {
                        "total_cpu_ms": fast_cpu + search_cpu + nearest_cpu,
                        "extra_calls": len(actions)},
                    "positive_only": {
                        "total_cpu_ms": fast_cpu + search_cpu + pos_diag["cpu_ms"],
                        "extra_calls": len(actions)},
                    "retained_negative": {
                        "total_cpu_ms": fast_cpu + search_cpu + neg_diag["cpu_ms"],
                        "extra_calls": len(actions)},
                    "lexical_gap": {
                        "total_cpu_ms": fast_cpu + gap_search_cpu + gap_rank_cpu,
                        "extra_calls": len(gap_actions)}
                }
            }
            rows.append(rec)
            if (j + 1) % 40 == 0:
                print(name, cohort, j + 1, "/", end - start, flush=True)
        summary = {
            "dataset": name, "cohort": cohort, "offsets": [start, end],
            "source_release": RELEASE, "source_hashes": file_hashes,
            "n_corpus_docs": len(docs),
            "index_build_cpu_ms": {"bm25": round(bm_index_cpu, 1),
                                   "graph": round(graph_index_cpu, 1)},
            "max_additional_searches_per_nonfast_arm": MAX_EXTRA_QUERIES,
            "shared_question_ids_with_any_v95_cohort": False,
            "public_benchmark_not_sealed": True,
            "run_policy": {"rescue_threshold": NEGATIVE_RESCUE_OVERLAP,
                           "protected_fast_docs": PROTECT,
                           "source_scan_chars": SOURCE_LIMIT},
            "results": summarize(rows),
            "limitations": [
                "Gold is pooled into released reference corpus, not open-world search",
                "V7.1 originally ran all 1000 public questions: no truly untouched corpus",
                "Negative means no exact substring, not relation refutation",
                "No relational entailment, correct answer, or calibrated abstention",
                "CPU times are additive separately timed components, not end-to-end production latency",
                "SAG2 authors' external JEV implementation not rerun",
                "Separate per-arm computations share some candidate proposals; read cost accounting"]
        }
        out.mkdir(parents=True, exist_ok=True)
        prefix = name + "_" + cohort
        (out / (prefix + "_summary.json")).write_text(json.dumps(summary, indent=2))
        with (out / (prefix + "_cases.jsonl")).open("w") as f:
            for rec in rows:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print("RESULT", name, cohort,
              json.dumps(summary["results"]["methods"], sort_keys=True),
              flush=True)

def smoke():
    w = Workspace({"a": "Alice met Bob.", "b": "Bob lives in Paris."})
    report = w.partition("all", "Alice", "a", anchor_tokens=("Bob",))
    assert w.verify_matches(report.positive)
    assert w.get(report.positive) == {"a"}
    assert w.get(report.negative) == {"b"}
    assert report.complement_checked
    print("V9.5 controlled benchmark smoke PASS")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("smoke", "run"))
    p.add_argument("--data", type=pathlib.Path,
                   default=pathlib.Path("data/sag2_official"))
    p.add_argument("--out", type=pathlib.Path,
                   default=pathlib.Path("results-v95-controlled"))
    p.add_argument("--datasets", nargs="+",
                   choices=list(SAG2_AUTHOR),
                   default=list(SAG2_AUTHOR))
    a = p.parse_args()
    if a.command == "smoke":
        return smoke()
    for name in a.datasets:
        evaluate(name, a.data, a.out)
    print("V9.5 controlled lexical-set trial complete", flush=True)

if __name__ == "__main__":
    main()
