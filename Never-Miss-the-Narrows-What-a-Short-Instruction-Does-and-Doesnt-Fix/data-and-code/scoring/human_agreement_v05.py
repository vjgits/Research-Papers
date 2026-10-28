#!/usr/bin/env python3
"""Human-label analysis for v0.5.1 (written BEFORE any labels exist; preregistered rules).

Inputs: annotator_A.csv, annotator_B.csv (filled), key_private.csv, optional adjudicated.csv (item_id + fields, used where
A and B disagree), judge labels_majority.csv, the main responses.jsonl.
Outputs (agreement.json):
  * per-field Cohen's kappa A-vs-B and human(consensus)-vs-judge-majority;
  * RULE: a field with judge-human kappa < 0.40 is flagged EXCLUDE_FROM_JUDGE_REPORTING;
  * arm-guess blinding check: proportion correct vs chance 1/3, exact one-sided binomial p (p < 0.05 => blinding failed);
  * PPI (prediction-powered) estimate of the P-B composite difference per stratum, for fields passing the kappa rule:
      theta_PPI = Delta_judge(all matched cells) + mean over human-labelled matched cells of (Delta_human - Delta_judge),
    with a 95% CI from a case-clustered bootstrap that resamples both terms.
"""
import argparse, csv, json, math, random, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ["SCD", "STR_cut", "STR_disclosed", "DR", "AoC", "ISD", "RoC", "DCC", "NAG", "OVER", "answered"]
KAPPA_MIN = 0.40


def rd(p):
    return list(csv.DictReader(open(p, encoding="utf-8")))


def iv(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def kappa(pairs):
    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    n = len(pairs)
    if n < 5:
        return None
    cats = sorted({x for p in pairs for x in p})
    po = sum(a == b for a, b in pairs) / n
    pe = sum((sum(a == c for a, _ in pairs) / n) * (sum(b == c for _, b in pairs) / n) for c in cats)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


def binom_sf(k, n, p):
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", required=True, help="folder with annotator_A.csv, annotator_B.csv, key_private.csv [, adjudicated.csv]")
    ap.add_argument("--judge-labels", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    pack = Path(a.pack)
    A = {r["item_id"]: r for r in rd(pack / "annotator_A.csv")}
    B = {r["item_id"]: r for r in rd(pack / "annotator_B.csv")}
    K = {r["item_id"]: r for r in rd(pack / "key_private.csv")}
    ADJ = {r["item_id"]: r for r in rd(pack / "adjudicated.csv")} if (pack / "adjudicated.csv").exists() else {}
    J = {r["item_id"]: r for r in rd(a.judge_labels)}
    human = {}
    for iid in K:
        h = {}
        for f in FIELDS:
            x, y = iv(A.get(iid, {}).get(f)), iv(B.get(iid, {}).get(f))
            h[f] = x if x == y else iv(ADJ.get(iid, {}).get(f))
        human[iid] = h
    res = {"n_items": len(K), "kappa_A_vs_B": {}, "kappa_human_vs_judge": {}, "judge_fields_excluded": []}
    for f in FIELDS:
        res["kappa_A_vs_B"][f] = kappa([(iv(A[i].get(f)), iv(B[i].get(f))) for i in K if i in A and i in B])
        jk = f"{K[next(iter(K))]['run_id']}#" if K else ""
        res["kappa_human_vs_judge"][f] = kappa([(human[i][f], iv(J.get(f"{K[i]['run_id']}#{K[i]['dp']}", {}).get(f))) for i in K])
        k = res["kappa_human_vs_judge"][f]
        if k is not None and k < KAPPA_MIN:
            res["judge_fields_excluded"].append(f)
    # blinding check
    guesses = [(A[i].get("arm_guess_B_P_S_unsure", "").strip().upper(), K[i]["arm"]) for i in K if i in A] + \
              [(B[i].get("arm_guess_B_P_S_unsure", "").strip().upper(), K[i]["arm"]) for i in K if i in B]
    g = [(x, y) for x, y in guesses if x in ("B", "P", "S")]
    if g:
        kc = sum(x == y for x, y in g)
        p = binom_sf(kc, len(g), 1 / 3)
        res["arm_guess"] = {"n_guesses": len(g), "correct": kc, "rate": round(kc / len(g), 3), "p_one_sided_vs_1/3": round(p, 5),
                            "blinding_failed": p < 0.05}
    # PPI for the P-B composite per stratum (fields passing the kappa rule only)
    metric_fields = {"SCD": "SCD", "DR": "DR", "AoC": "AoC", "ISD": "ISD", "RoC": "RoC"}
    ok = [m for m, f in metric_fields.items() if f not in res["judge_fields_excluded"]]
    by_cell = defaultdict(dict)  # (stratum, case, slot, dp) -> arm -> (human_vec, judge_vec)
    for i, k in K.items():
        jl_ = J.get(f"{k['run_id']}#{k['dp']}", {})
        by_cell[(k["stratum"], k["case_id"], k["model_slot"], k["dp"])][k["arm"]] = (
            {m: human[i][metric_fields[m]] for m in ok}, {m: iv(jl_.get(metric_fields[m])) for m in ok})
    ppi = {}
    for st in sorted({c[0] for c in by_cell}):
        rows = []
        for c, d in by_cell.items():
            if c[0] == st and "P" in d and "B" in d:
                for m in ok:
                    hp, hb, jp, jb = d["P"][0][m], d["B"][0][m], d["P"][1][m], d["B"][1][m]
                    if None not in (hp, hb, jp, jb):
                        rows.append((c[1], (hp - hb) - (jp - jb)))
        if rows:
            corr = sum(r[1] for r in rows) / len(rows)
            rng = random.Random(2026)
            cases = sorted({r[0] for r in rows})
            byc = defaultdict(list)
            for r in rows:
                byc[r[0]].append(r[1])
            bs = sorted(sum(sum(byc[k]) for k in s) / max(1, sum(len(byc[k]) for k in s))
                        for s in ([rng.choice(cases) for _ in cases] for _ in range(5000)))
            ppi[st] = {"rectifier_mean_(human-judge)_P-B": round(corr, 4), "rectifier_ci95": [round(bs[125], 4), round(bs[4874], 4)],
                       "n_labelled_cells": len(rows), "note": "theta_PPI = judge P-B (analysis_v05, same fields) + this rectifier"}
    res["ppi_rectifier"] = ppi
    res["fields_used_for_ppi"] = ok
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "agreement.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
