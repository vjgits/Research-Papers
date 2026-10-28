#!/usr/bin/env python3
"""V9.6A: question-anchored versus source-adaptive TWO-query retrieval.

PGER exploratory experiment. No gold at inference, no semantic edge verifier.
This tests candidate discovery, not novelty or answer correctness. All arms
share unchanged V7.1 initial ranking and identical BM25+rank_fuse scoring.
No paid APIs. Public SAG2 questions: development offsets 640:760,
previously untested-by-V95 new confirmation offsets 880:1000.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import time
import unicodedata
from collections import Counter

import numpy as np

from benchmark_v95_controlled import initial, two_actions, metric, paired, unique, cpu_ms
from benchmark_v71_sag2_corpus import download, official_records, SAG2_AUTHOR, RELEASE
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger
from expansion_v92 import propose, rank_fuse, terms

SEED = 20261028
DEVELOPMENT = (640, 760)
NEW_CONFIRMATION = (880, 1000)
MAX_QUERIES = 2
BM_DEPTH = 40
MAX_TITLED_NGRAM = 6
MAX_BRIDGE_DOCS = 4
METHODS = ("v71_fast", "v95_two_query", "v96_question_anchor", "v96_adaptive_bridge")
WORD = re.compile(r"[A-Za-z][A-Za-z0-9'-]*")
CAP_SEQ = re.compile(r"\b(?:[A-Z][A-Za-z0-9'-]*|[A-Z]{2,})(?:\s+(?:[A-Z][A-Za-z0-9'-]*|[A-Z]{2,})){0,4}")
IGNORE = frozenset(("the", "who", "what", "when", "where", "which",
                    "whose", "why", "how", "did", "does", "was", "were",
                    "is", "are", "it", "of", "and", "for", "to", "in",
                    "on", "by", "a", "an", "with", "from", "into", "that",
                    "state", "city", "country", "region", "town",
                    "person", "year", "date", "time", "capital"))
QUESTION_RELATIONS = frozenset(("born", "birthplace", "birth", "founded",
                                "published", "written", "wrote",
                                "located", "directed", "died",
                                "established", "capital", "border",
                                "child", "parent", "spouse", "record",
                                "label", "produced", "hosted",
                                "performed", "river", "flow"))

def normalized(s):
    s = unicodedata.normalize("NFKC", str(s)).casefold()
    return " ".join(WORD.findall(s))

def tokenize(s):
    return WORD.findall(str(s))

def title_map(docs):
    """Build once per corpus, solely from available titles, no labels."""
    out = {}
    for i, d in enumerate(docs):
        key = normalized(d["title"])
        if key and len(key.split()) <= MAX_TITLED_NGRAM:
            out.setdefault(key, []).append(i)
    return out

def anchor_candidates(q, mapping, idf, fast=(), docs=()):
    tokens = tokenize(q)
    candidates = {}
    raw = q.casefold()
    def add(value, origin, exact, pos):
        key = normalized(value)
        toks = key.split()
        if not toks or len(key) < 3 or len(toks) > MAX_TITLED_NGRAM:
            return
        if len(toks) == 1 and (toks[0] in IGNORE or len(toks[0]) < 4):
            return
        if all(t in IGNORE for t in toks):
            return
        rarity = sum(float(idf.get(t, 0.0)) for t in toks if t not in IGNORE)
        if rarity <= 0.1:
            return
        # Penalize anchors already visibly present in highest-ranked passages.
        # A mention is NOT a verified fact.
        first_texts = (str(docs[i]["title"]) + " " +
                       docs[i].get("text", "")[:800] for i in fast[:5])
        already = any(key in normalized(t) for t in first_texts)
        score = rarity / max(1., len(toks)**.45) + (5.0 if exact else 0.0) + \
                (1.0 if len(toks) > 1 else 0.0) - (2.0 if already else 0.0)
        if key not in candidates or score > candidates[key]["score"]:
            candidates[key] = {"query": value.strip(), "key": key,
                               "source": origin, "exact_title": bool(exact),
                               "score": round(score, 6),
                               "offset": int(pos), "already_seen": bool(already)}
    lower = [t.casefold() for t in tokens]
    # Exhaustive ngram lookup, bounded O(length(question) * 6), not corpus scan.
    for start in range(len(tokens)):
        for span in range(1, min(MAX_TITLED_NGRAM, len(tokens)-start) + 1):
            key = normalized(" ".join(tokens[start:start+span]))
            if key in mapping and len(mapping[key]) <= 8:
                add(" ".join(tokens[start:start+span]), "question_exact_title", True, start)
    # Capitalized named phrases not necessarily corpus titles.
    for m in CAP_SEQ.finditer(q):
        phrase = m.group()
        add(phrase, "question_capitalized", normalized(phrase) in mapping,
            len(tokenize(q[:m.start()])))
    # Preserve rare uppercase/acronyms even if they do not match title.
    for k, tok in enumerate(tokens):
        if (tok.isupper() and len(tok)>=3) or ("-" in tok and any(c.isupper() for c in tok)):
            add(tok, "question_acronym_or_hyphen", normalized(tok) in mapping, k)
    return sorted(candidates.values(),
                  key=lambda c: (-c["score"], -len(c["key"]), c["offset"], c["key"]))

def pick_question_anchors(q, mapping, idf, fast, docs, n=2):
    ranked = anchor_candidates(q, mapping, idf, fast, docs)
    chosen = []
    for a in ranked:
        # Diversity by token overlap; two aliases of the same noun phrase
        # do not deserve two searches.
        tok = set(a["key"].split())
        if any(len(tok & set(x["key"].split())) /
               max(1, min(len(tok), len(x["key"].split()))) >= .75 for x in chosen):
            continue
        chosen.append(a)
        if len(chosen) == n:
            break
    return chosen

def execute_query(search_index, action):
    t = time.process_time()
    found = [i for i, _ in search_index.search(action["query"], "bm25", BM_DEPTH)]
    return found, cpu_ms(t)

def anchored_search(q, methods, fast, mapping, bridge_mode=False):
    """Two searches; only second may use first retrieved source text.

    First query is a literal phrase in question. Optional second query is
    either a different question phrase, or a source-grounded bridge phrase
    from new evidence, chosen without answers, gold or dataset ID.
    """
    clock = time.process_time()
    anchors = pick_question_anchors(q, mapping, methods.index.idfs,
                                    fast, methods.docs, 3)
    hits = []
    actions = []
    if not anchors:
        # Deterministic fallback, still at most two BM25 calls.
        old_hits, old_actions, old_cpu = two_actions(q, methods, fast)
        for h, a in zip(old_hits, old_actions):
            actions.append(dict(a, action_type="fallback_v95"))
        return old_hits, actions, cpu_ms(clock), old_cpu
    first = dict(anchors[0], action_type="question_anchor")
    h1, first_search_cpu = execute_query(methods.index, first)
    first["n_hits"] = len(h1)
    hits.append(h1);actions.append(first)
    second = next((dict(a, action_type="second_question_anchor")
                   for a in anchors[1:]), None)
    if bridge_mode and h1:
        bridge = propose(q, methods.docs, unique(h1[:MAX_BRIDGE_DOCS] + fast[:2]),
                         methods.index.idfs, kind="names", seed_n=MAX_BRIDGE_DOCS,
                         k=12)
        q_tokens = set(terms(q))
        best = []
        for p in bridge:
            phrase = p["term"]
            key = normalized(phrase)
            if not key or key == first["key"]:
                continue
            # At least one of the original question's rare anchors or relation
            # words must occur in the source sentence, not just any name.
            quote_tokens = set(terms(p["quote"]))
            source_anchor = set(terms(first["query"]))
            if not ((source_anchor & quote_tokens) or
                    (q_tokens & quote_tokens & QUESTION_RELATIONS)):
                continue
            toks = set(terms(phrase))
            if not toks or toks <= q_tokens:
                continue
            score = (sum(methods.index.idfs.get(t, 0.0) for t in toks) /
                     max(1, len(toks)**.5))
            # Do not claim that named co-mentions are verified relationships.
            best.append((score, key, p))
        if best:
            _, _, witness = sorted(best, key=lambda x: (-x[0], x[1]))[0]
            candidate = {"query": witness["term"], "key": normalized(witness["term"]),
                         "source": "first_result_source_quote",
                         "action_type": "lexical_source_bridge",
                         "witness_doc": int(witness["witness_doc"]),
                         "witness_quote": witness["quote"],
                         "witness_sha256": hashlib.sha256(
                             (methods.docs[witness["witness_doc"]]["title"] + "\n" +
                              methods.docs[witness["witness_doc"]].get("text", "")).encode()
                          ).hexdigest()}
            # Prefer a bridge only if it is not duplicating the distinct
            # question anchor and its lexical IDF provides new information.
            if second is None or candidate["key"] not in (
                    first["key"], second["key"]):
                second = candidate
    if second is not None and second["key"] != first["key"]:
        h2, second_search_cpu = execute_query(methods.index, second)
        second["n_hits"] = len(h2)
        hits.append(h2);actions.append(second)
        total_search_cpu = first_search_cpu + second_search_cpu
    else:
        total_search_cpu = first_search_cpu
    assert len(actions) <= MAX_QUERIES
    return hits, actions, cpu_ms(clock), total_search_cpu

def eval_dataset(name, datadir, outdir):
    hashes = download(name, datadir)
    src_to_doc, docs, rows = official_records(name, datadir)
    assert len(rows) == 1000 and len(docs) == SAG2_AUTHOR[name]["corpus"]
    src = list(src_to_doc)
    t = time.process_time(); methods = SparseMethods(docs)
    index_ms = cpu_ms(t)
    t = time.process_time(); graph = EvidenceLedger(methods)
    graph_ms = cpu_ms(t)
    t = time.process_time(); tmap = title_map(docs)
    mapping_ms = cpu_ms(t)
    for cohort, (begin, end) in (
        ("development", DEVELOPMENT), ("confirmation", NEW_CONFIRMATION)):
        outcomes = []
        for iteration, row in enumerate(rows[begin:end]):
            question = row["question"]
            bm, fast, base_ms = initial(question, methods, graph)
            old_hits, old_actions, old_ms = two_actions(question, methods, fast)
            h_anchor, actions_anchor, anchor_ms, anchor_search_cpu = anchored_search(
                question, methods, fast, tmap, False)
            h_bridge, actions_bridge, bridge_ms, bridge_search_cpu = anchored_search(
                question, methods, fast, tmap, True)
            t = time.process_time()
            ranking = {
                "v71_fast": fast,
                "v95_two_query": unique(rank_fuse(fast, bm, old_hits,
                         mode="fuse", strength=.4, protect=2, cutoff=150)),
                "v96_question_anchor": unique(rank_fuse(fast, bm, h_anchor,
                         mode="fuse", strength=.4, protect=2, cutoff=150)),
                "v96_adaptive_bridge": unique(rank_fuse(fast, bm, h_bridge,
                         mode="fuse", strength=.4, protect=2, cutoff=150))}
            ranking_ms = cpu_ms(t) / 3.0  # shared lower-bound estimate only
            # Absolute gold access begins below. Not used by any retrieval rule.
            gold = set(row["gold"])
            assert gold and gold <= set(src)
            as_src = lambda rr: {src[i] for i in rr}
            pools = {
                "v71_fast": unique(fast[:80]),
                "v95_two_query": unique(fast[:80] + [i for h in old_hits for i in h]),
                "v96_question_anchor": unique(fast[:80] + [i for h in h_anchor for i in h]),
                "v96_adaptive_bridge": unique(fast[:80] + [i for h in h_bridge for i in h])}
            totals = {
                "v71_fast": (base_ms, 0),
                "v95_two_query": (base_ms + old_ms + ranking_ms, len(old_actions)),
                "v96_question_anchor": (base_ms + anchor_ms + ranking_ms, len(actions_anchor)),
                "v96_adaptive_bridge": (base_ms + bridge_ms + ranking_ms, len(actions_bridge))}
            cases = {
                "id": row["id"], "question": question,
                "support_count": len(gold),
                "metrics": {a: metric(rr, src, gold) for a, rr in ranking.items()},
                "candidate_audit": {
                    a: {
                        "full_support_in_pool": int(gold <= as_src(pool)),
                        "evidence_recall": len(gold & as_src(pool))/len(gold),
                        "all_support_in_top80": int(gold <= as_src(rr[:80]))}
                    for a, (pool, rr) in
                    ((a, (pools[a], ranking[a])) for a in METHODS)},
                "search_traces": {"v95_two_query": old_actions,
                                  "v96_question_anchor": actions_anchor,
                                  "v96_adaptive_bridge": actions_bridge},
                "timing": {
                    a: {"cpu_ms_estimate": round(totals[a][0], 4),
                        "extra_bm25_calls": totals[a][1]} for a in METHODS},
                "top10_source_ids": {a: [docs[i]["_id"] for i in rr[:10]]
                                     for a, rr in ranking.items()},
                "oracle_only_missing_support_count": {
                    a: len(gold - as_src(rr[:5])) for a, rr in ranking.items()}
            }
            outcomes.append(cases)
            if (iteration + 1) % 40 == 0:
                print(name, cohort, iteration + 1, "of", end - begin, flush=True)
        result = {"dataset": name, "cohort": cohort,
                  "offset_range": [begin, end], "source_hashes": hashes,
                  "source_release": RELEASE, "corpus_docs": len(docs),
                  "index_cpu_ms": {"sparse": round(index_ms, 2),
                                   "title_graph": round(graph_ms, 2),
                                   "title_map": round(mapping_ms, 2)},
                  "methods": {},
                  "constraints": {
                      "public_repeatedly_inspected_corpus": True,
                      "confirmation_question_ids_new_to_V95": (cohort == "confirmation"),
                      "maximum_extra_bm25": MAX_QUERIES,
                      "fixed_ranking": "rank_fuse strength .4 protect 2",
                      "no_answer_labels_or_gold_for_retrieval": True,
                      "source_quote_validity_is_not_entailment": True,
                      "no_semantic_verifier": True,
                      "no_new_originality_claims": True}}
        for arm in METHODS:
            samples = [q["metrics"][arm]["ae5"] for q in outcomes]
            stats = {key: round(float(np.mean([q["metrics"][arm][key]
                                    for q in outcomes])), 6)
                     for key in ("ae5", "ae10", "r5", "r10")}
            stats["candidate_full"] = sum(q["candidate_audit"][arm][
                                          "full_support_in_pool"] for q in outcomes)
            stats["candidate_evidence_recall"] = round(float(np.mean(
                [q["candidate_audit"][arm]["evidence_recall"] for q in outcomes])), 6)
            stats["by_support_count"] = {
                str(n): {"n": sum(q["support_count"] == n for q in outcomes),
                         "full_candidate": sum(q["support_count"] == n and
                             q["candidate_audit"][arm]["full_support_in_pool"]
                             for q in outcomes),
                         "ae5": sum(q["support_count"] == n and
                                    q["metrics"][arm]["ae5"] for q in outcomes)}
                for n in sorted(set(q["support_count"] for q in outcomes))}
            stats["mean_cpu_ms_estimate"] = round(float(np.mean(
                [q["timing"][arm]["cpu_ms_estimate"] for q in outcomes])), 3)
            stats["mean_extra_bm25_calls"] = round(float(np.mean(
                [q["timing"][arm]["extra_bm25_calls"] for q in outcomes])), 3)
            for comparator in ("v71_fast", "v95_two_query", "v96_question_anchor"):
                if arm != comparator:
                    stats["paired_vs_" + comparator] = paired(
                        samples, [q["metrics"][comparator]["ae5"] for q in outcomes])
            result["methods"][arm] = stats
        result["query_stats"] = {
            arm: Counter(a["action_type"] for rec in outcomes
                         for a in rec["search_traces"][arm])
            for arm in ("v96_question_anchor", "v96_adaptive_bridge")}
        # Convert Counter for deterministic JSON serialization.
        result["query_stats"] = {k: dict(v) for k, v in result["query_stats"].items()}
        outdir.mkdir(parents=True, exist_ok=True)
        base = name + "_" + cohort
        (outdir / (base + "_summary.json")).write_text(
            json.dumps(result, indent=2, sort_keys=True))
        with (outdir / (base + "_cases.jsonl")).open("w") as f:
            for rec in outcomes:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print("V96_RESULT", name, cohort,
              json.dumps(result["methods"], sort_keys=True), flush=True)
    print("COMPLETE", name, flush=True)

def smoke():
    docs = [{"title": "A Don", "text": "Song by Maya"},
            {"title": "Jackson Township", "text": "The town of Jackson"},
            {"title": "El Dorado", "text": "El Dorado borders a city"}]
    mapping = title_map(docs)
    anchors = anchor_candidates("Where is A Don from Jackson Township?",
                                mapping,
                                {"don": 6.0, "jackson": 5.0,
                                 "township": 4.0}, (1,), docs)
    assert any(a["key"] == "a don" for a in anchors)
    assert any(a["key"] == "jackson township" for a in anchors)
    assert all(a["source"].startswith("question_") for a in anchors)
    print("V9.6A lexical-anchor smoke PASS")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("smoke", "run"))
    p.add_argument("--data", type=pathlib.Path,
                   default=pathlib.Path("data/sag2_official"))
    p.add_argument("--out", type=pathlib.Path,
                   default=pathlib.Path("results-v96"))
    p.add_argument("--datasets", nargs="+",
                   choices=list(SAG2_AUTHOR), default=list(SAG2_AUTHOR))
    args = p.parse_args()
    if args.command == "smoke":
        return smoke()
    for name in args.datasets:
        eval_dataset(name, args.data, args.out)

if __name__ == "__main__":
    main()
