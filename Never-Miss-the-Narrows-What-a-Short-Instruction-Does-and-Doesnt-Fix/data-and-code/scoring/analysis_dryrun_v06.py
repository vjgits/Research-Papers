#!/usr/bin/env python3
"""Analysis for the v0.6-dry decision-outcome dry run (AI readers). Never pooled with v0.5 judge results.
  python3 scoring/analysis_dryrun_v06.py --run outputs/dryrun_v06 --out outputs/analysis_dryrun_v06
"""
import argparse, csv, itertools, json, random, statistics as st, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import engine_v05 as E  # noqa: E402

READERS = ["R_openai", "R_google"]
POINTS_FOR_FIELD = {"SCD": ["star_value", "star_effort"], "DR": ["deadline"], "AoC": ["two_options", "option_diff"],
                    "ISD": ["spare_time", "spare_use"]}


def boot_ci(case_means, n=10000, seed=7):
    rng = random.Random(seed)
    xs = list(case_means)
    bs = sorted(st.mean(rng.choice(xs) for _ in xs) for _ in range(n))
    return bs[int(0.025 * n)], bs[int(0.975 * n) - 1]


def signflip_p(case_means):
    xs = list(case_means)
    obs = abs(st.mean(xs))
    hits = tot = 0
    for signs in itertools.product((1, -1), repeat=len(xs)):
        tot += 1
        hits += abs(st.mean(s * x for s, x in zip(signs, xs))) >= obs - 1e-12
    return hits / tot


def kappa(a, b):
    n = len(a)
    if not n:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else round((po - pe) / (1 - pe), 3)


def paired_effect(vals):
    """vals: {(case, slot, dp): {"B": x, "P": y}} -> P-B estimate clustered by case."""
    by_case = defaultdict(list)
    for (case, _, _), d in vals.items():
        if "B" in d and "P" in d:
            by_case[case].append(d["P"] - d["B"])
    cm = [st.mean(v) for v in by_case.values()]
    if not cm:
        return None
    lo, hi = boot_ci(cm)
    rate = lambda arm: round(st.mean(d[arm] for d in vals.values() if "B" in d and "P" in d), 3)  # noqa: E731
    return {"B": rate("B"), "P": rate("P"), "P_minus_B": round(st.mean(cm), 3), "ci95": [round(lo, 3), round(hi, 3)],
            "exact_signflip_p": round(signflip_p(cm), 4) if len(cm) <= 16 else None, "n_cases": len(cm),
            "n_cells": sum(len(v) for v in by_case.values()), "cases_positive": sum(c > 0 for c in cm)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    J = [j for j in E.load_jsonl(Path(a.run) / "judgments.jsonl") if j.get("parsed") is not None and "arm" in j]
    reads = {(j["item_id"], j["role"]): j for j in J if j["role"] in READERS}
    grades = {(j["item_id"], j["role"][2:]): j for j in J if j["role"].startswith("G_")}
    judge = {r["item_id"]: r for r in csv.DictReader(open(ROOT / "outputs/judge_main/labels_majority.csv"))}
    res = {"version": "0.6-dry", "note": "AI readers and an AI grader; a method check, not human evidence.",
           "spend_usd": round(sum(float(j.get("cost_usd") or 0) for j in E.load_jsonl(Path(a.run) / "judgments.jsonl")), 4)}

    # ---- triggered: recovered tradeoff points
    def gscore(g):
        p = {k: v for k, v in g["parsed"].items() if k != "note" and v in (0, 1, "0", "1", True, False)}
        return {k: int(v in (1, "1", True)) for k, v in p.items()}

    item_scores = {}  # (item, reader) -> {point: 0/1}
    for (iid, rn), g in grades.items():
        sc = gscore(g)
        if sc:
            item_scores[(iid, rn)] = (g, sc)
    trig = {}
    for rn in READERS + ["mean"]:
        cells = defaultdict(dict)
        per_point = defaultdict(lambda: defaultdict(dict))
        for (iid, r), (g, sc) in item_scores.items():
            if rn != "mean" and r != rn:
                continue
            key = (g["case_id"], g["slot"], g["dp"])
            val = st.mean(sc.values())
            if rn == "mean":
                cells[key].setdefault(g["arm"] + "_list", []).append(val)
            else:
                cells[key][g["arm"]] = val
                for pt, v in sc.items():
                    per_point[pt][key][g["arm"]] = v
        if rn == "mean":
            cells = {k: {arm: st.mean(d[arm + "_list"]) for arm in ("B", "P") if arm + "_list" in d and len(d[arm + "_list"]) == 2}
                     for k, d in cells.items()}
        trig[rn] = {"composite_recovered": paired_effect(cells),
                    "by_point": {pt: paired_effect(v) for pt, v in sorted(per_point.items())} if rn != "mean" else None}
    res["triggered_LH"] = trig

    # reader agreement (same item, same point)
    a_, b_ = [], []
    for (iid, r), (g, sc) in item_scores.items():
        if r == "R_openai" and (iid, "R_google") in item_scores:
            sc2 = item_scores[(iid, "R_google")][1]
            for pt in sc:
                if pt in sc2:
                    a_.append(sc[pt]); b_.append(sc2[pt])
    res["reader_agreement"] = {"n_point_pairs": len(a_), "pct_agree": round(sum(x == y for x, y in zip(a_, b_)) / max(1, len(a_)), 3),
                               "kappa": kappa(a_, b_)}

    # judge vs reader validity: judge field label vs "reader recovered all points for that field"
    val = {}
    for field, pts in POINTS_FOR_FIELD.items():
        for rn in READERS:
            jv, rv = [], []
            for (iid, r), (g, sc) in item_scores.items():
                if r != rn or iid not in judge or judge[iid].get(field) in (None, "", "None"):
                    continue
                if not all(p in sc for p in pts):
                    continue
                jv.append(int(judge[iid][field])); rv.append(int(all(sc[p] for p in pts)))
            if jv:
                val[f"{field}|{rn}"] = {"n": len(jv), "judge_rate": round(st.mean(jv), 3), "reader_rate": round(st.mean(rv), 3),
                                        "pct_agree": round(sum(x == y for x, y in zip(jv, rv)) / len(jv), 3), "kappa": kappa(jv, rv)}
    res["judge_vs_reader"] = val

    # ---- controls: reader wants to reopen a settled decision
    ctrl = {}
    for rn in READERS:
        cells = defaultdict(dict)
        jo, ro = [], []
        for (iid, r), j in reads.items():
            if r != rn or not j.get("control"):
                continue
            v = int(j["parsed"].get("reopen") in (True, "true", 1, "1"))
            cells[(j["case_id"], j["slot"], j["dp"])][j["arm"]] = v
            if iid in judge and judge[iid].get("OVER") not in (None, "", "None"):
                jo.append(int(int(judge[iid]["OVER"]) == 2)); ro.append(v)
        ctrl[rn] = {"reopen_rate": paired_effect(cells),
                    "vs_judge_OVER2": {"n": len(jo), "kappa": kappa(jo, ro),
                                       "reopen_rate_when_judge_OVER2": round(st.mean([r for j, r in zip(jo, ro) if j]), 3) if any(jo) else None,
                                       "reopen_rate_when_judge_not_OVER2": round(st.mean([r for j, r in zip(jo, ro) if not j]), 3) if not all(jo) else None}}
    res["controls"] = ctrl
    res["parse"] = {"reads_ok": len(reads), "grades_ok": len(item_scores)}
    (out / "analysis.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
