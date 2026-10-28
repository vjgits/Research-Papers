#!/usr/bin/env python3
"""ICP v0.5.1 analysis (preregistered, docs/PREREGISTRATION_v05.md; revised after the independent pre-data review).

Observation: (run, DP, metric) binary success. Matched cell: (case, model, DP, metric). Arm differences use ONLY cells
present in both arms. DR is collapsed to one run-level outcome (any DP before the deadline). NAG counts only at DPs after
the traveler decided with the ★ value disclosed in an earlier live reply of the same run (SCD=1), and always in controls.
Composite = equal-weight mean of per-metric success rates (SCD, STR-not-silent, DR, AoC, ISD, RoC); R03's SCD (local
knowledge, never introduced in the conversation) is excluded from the composite.
Inference per stratum (never pooled across strata or versions):
  * estimate + 95% CI from a case-clustered bootstrap over matched cells (10,000 resamples, seed 2026);
  * exact two-sided sign-flip permutation test on case-level mean differences (reports the smallest achievable p);
  * H3 non-inferiority: one-sided 97.5% upper bound of (P-B), (S-B) for OVER=2 (controls) and eligible NAG < +0.10;
  * H6 equivalence (TOST, ±0.10, 90% CI) for DCC;
  * cost outcomes: words per reply and 'answered'; length-adjusted sensitivity (within-cell log-words adjustment);
  * leave-one-judge-out sensitivity when --labels-dir is given.
Label source must be named (human | judge | cue); judge/cue outputs are labelled SUPPLEMENTARY.
"""
import argparse, csv, itertools, json, math, os, random, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSITE = ["SCD", "STR", "DR", "AoC", "ISD", "RoC"]
EXCLUDE_FROM_COMPOSITE = {("R03", "SCD")}
B_REPS, SEED, NI_MARGIN, EQ_MARGIN = 10000, 2026, 0.10, 0.10


def jl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def to_int(v):
    if v in (None, "", "None"):
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def observations(responses, labels, cases):
    obs, versions = [], set()
    include_mock = bool(os.environ.get("ICP_TEST_INCLUDE_MOCK"))
    for r in responses:
        if r.get("provenance") != "LIVE_PROVIDER_API" and not include_mock:
            continue
        versions.add((r.get("runner_version"), r.get("arms_sha256"), r.get("frozen_sha256") and r["case_id"] and None))
        c = cases[r["case_id"]]
        stratum = "CONTROL" if c["condition"] == "control" else c["tier"]
        scd_disclosed = False
        dr_vals = []
        for dp in r["dps"]:
            lab = labels.get(f"{r['run_id']}#{dp['dp']}") if dp["status"] == "OK" else None
            metrics = next(x["metrics"] for x in c["dps"] if x["dp"] == dp["dp"])
            base = dict(case=r["case_id"], stratum=stratum, arm=r["arm"], slot=r["model_slot"], dp=dp["dp"], words=dp["words"])
            if lab is None:
                continue
            for m in metrics:
                if m == "DR":
                    v = to_int(lab.get("DR"))
                    if v is not None:
                        dr_vals.append(v)
                    continue
                if m == "STR":
                    cut, disc = to_int(lab.get("STR_cut")), to_int(lab.get("STR_disclosed"))
                    if cut is None:
                        continue
                    silent = 1 if (cut == 1 and disc != 1) else 0
                    obs.append(dict(base, metric="STR", bad=silent, success=1 - silent))
                elif m == "OVER":
                    v = to_int(lab.get("OVER"))
                    if v is not None:
                        obs.append(dict(base, metric="OVER2", bad=int(v >= 2), success=int(v < 2)))
                        obs.append(dict(base, metric="OVER1", bad=int(v >= 1), success=int(v < 1)))
                elif m == "NAG":
                    v = to_int(lab.get("NAG"))
                    eligible = stratum == "CONTROL" or scd_disclosed
                    if v is not None and eligible:
                        obs.append(dict(base, metric="NAG", bad=v, success=1 - v))
                else:
                    v = to_int(lab.get(m))
                    if v is not None:
                        obs.append(dict(base, metric=m, bad=1 - v, success=v))
            if to_int(lab.get("SCD")) == 1 and "SCD" in metrics:
                scd_disclosed = True
            a = to_int(lab.get("answered"))
            if a is not None:
                obs.append(dict(base, metric="answered", bad=1 - a, success=a))
        if dr_vals:
            obs.append(dict(case=r["case_id"], stratum=stratum, arm=r["arm"], slot=r["model_slot"], dp="RUN", words=None,
                            metric="DR", bad=1 - max(dr_vals), success=max(dr_vals)))
    rv = {v[:2] for v in versions}
    if len(rv) > 1:
        raise SystemExit(f"Refusing to pool across runner/arms versions: {rv}")
    return obs


def cell_key(o):
    return (o["case"], o["slot"], o["dp"], o["metric"])


def matched(obs, a1, a0, metrics, key="success"):
    """Per matched cell: (case, metric, x1 - x0, logwords diff)."""
    by = defaultdict(dict)
    for o in obs:
        if o["metric"] in metrics and o["arm"] in (a1, a0):
            if (o["case"], o["metric"]) in EXCLUDE_FROM_COMPOSITE and len(metrics) > 1:
                continue
            by[cell_key(o)][o["arm"]] = o
    out = []
    for k, d in by.items():
        if a1 in d and a0 in d:
            w1, w0 = d[a1].get("words"), d[a0].get("words")
            lw = (math.log(1 + w1) - math.log(1 + w0)) if (w1 is not None and w0 is not None) else 0.0
            out.append((k[0], k[3], d[a1][key] - d[a0][key], lw))
    return out


def composite_diff(cells, metrics):
    """Equal-weight across metrics of the mean matched difference."""
    per = defaultdict(list)
    for case, m, d, _ in cells:
        per[m].append(d)
    vals = [mean(per[m]) for m in metrics if per[m]]
    return mean(vals)


def boot_ci(cells, metrics, reps, seed=SEED, alpha=0.05, one_sided=False):
    by = defaultdict(list)
    for c in cells:
        by[c[0]].append(c)
    keys = sorted(by)
    if len(keys) < 2:
        return None
    rng = random.Random(seed)
    vals = []
    for _ in range(reps):
        s = [c for k in (rng.choice(keys) for _ in keys) for c in by[k]]
        v = composite_diff(s, metrics)
        if v is not None:
            vals.append(v)
    vals.sort()
    if one_sided:
        return round(vals[min(len(vals) - 1, int((1 - alpha) * len(vals)))], 4)
    return [round(vals[int(alpha / 2 * len(vals))], 4), round(vals[min(len(vals) - 1, int((1 - alpha / 2) * len(vals)))], 4)]


def permutation_p(cells, metrics, max_exact=20, reps=20000, seed=SEED):
    """Exact two-sided sign-flip test on case-level composite differences (Monte Carlo above max_exact cases)."""
    by = defaultdict(list)
    for c in cells:
        by[c[0]].append(c)
    dvals = [composite_diff(v, metrics) for v in by.values()]
    dvals = [d for d in dvals if d is not None]
    n = len(dvals)
    if n == 0:
        return None
    obs = abs(mean(dvals))
    if n <= max_exact:
        cnt = sum(1 for signs in itertools.product((1, -1), repeat=n) if abs(mean([s * d for s, d in zip(signs, dvals)])) >= obs - 1e-12)
        p = cnt / 2 ** n
    else:
        rng = random.Random(seed)
        cnt = sum(1 for _ in range(reps) if abs(mean([rng.choice((1, -1)) * d for d in dvals])) >= obs - 1e-12)
        p = (cnt + 1) / (reps + 1)
    return {"p_two_sided": round(p, 5), "n_cases": n, "min_achievable_p": round(2 / 2 ** n, 5) if n <= max_exact else None}


def length_adjusted(cells):
    """Within-cell adjustment: regress success difference on log-words difference (no intercept removal of arm effect:
    fit d = b0 + b1*lw; b0 = length-adjusted arm effect)."""
    if len(cells) < 5:
        return None
    xs = [c[3] for c in cells]
    ys = [c[2] for c in cells]
    mx, my = mean(xs), mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return round(my, 4)
    b1 = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return {"adjusted_effect": round(my - b1 * mx, 4), "slope_per_log_words": round(b1, 4)}


T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179,
        13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086, 25: 2.060, 30: 2.042}


def t_upper(cells, metrics):
    """One-sided 97.5% upper bound from a t interval on case-level differences (df = n_cases - 1)."""
    by = defaultdict(list)
    for c in cells:
        by[c[0]].append(c)
    d = [composite_diff(v, metrics) for v in by.values()]
    d = [x for x in d if x is not None]
    n = len(d)
    if n < 2:
        return None
    m = mean(d)
    sd = math.sqrt(sum((x - m) ** 2 for x in d) / (n - 1))
    q = T975.get(n - 1) or T975[min(T975, key=lambda k: abs(k - (n - 1)))]
    return round(m + q * sd / math.sqrt(n), 4)


def rates(obs, metric_set, key="success"):
    out = {}
    for arm in ("B", "P", "S"):
        per = defaultdict(list)
        for o in obs:
            if o["arm"] == arm and o["metric"] in metric_set and not ((o["case"], o["metric"]) in EXCLUDE_FROM_COMPOSITE and len(metric_set) > 1):
                per[o["metric"]].append(o[key])
        vals = [mean(v) for v in per.values() if v]
        out[arm] = {"rate": round(mean(vals), 4) if vals else None, "n_obs": sum(len(v) for v in per.values())}
    return out


def effect_block(obs, metrics, reps, key="success"):
    blk = {"arm_rates": rates(obs, set(metrics), key)}
    for a1, a0 in (("P", "B"), ("S", "P"), ("S", "B")):
        cells = matched(obs, a1, a0, set(metrics), key)
        if not cells:
            continue
        blk[f"{a1}-{a0}"] = {"estimate": round(composite_diff(cells, metrics), 4), "ci95": boot_ci(cells, metrics, reps),
                             "matched_cells": len(cells), "permutation": permutation_p(cells, metrics),
                             "length_adjusted": length_adjusted(cells) if key == "success" else None}
    return blk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--responses", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--label-source", required=True, choices=["human", "judge", "cue"])
    ap.add_argument("--labels-dir", default="", help="judge output dir, for leave-one-judge-out sensitivity")
    ap.add_argument("--cases", default=str(ROOT / "data/cases_v05.jsonl"))
    ap.add_argument("--models", default=str(ROOT / "models_v05.json"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--reps", type=int, default=B_REPS)
    a = ap.parse_args()
    cases = {c["case_id"]: c for c in jl(a.cases)}
    models = json.loads(Path(a.models).read_text())["slots"]
    resp = jl(a.responses)
    lab = {r["item_id"]: r for r in csv.DictReader(open(a.labels))}
    obs = observations(resp, lab, cases)
    for o in obs:
        o["tier_model"] = models[o["slot"]]["tier"]
    src = a.label_source + ("-MOCK-TEST-NOT-DATA" if os.environ.get("ICP_TEST_INCLUDE_MOCK") else "")
    tag = "PRIMARY (human labels)" if src == "human" else f"SUPPLEMENTARY ({src} labels; not human ground truth)"
    rep = {"label_source": tag, "n_obs": len(obs), "strata": {}}
    for st in sorted({o["stratum"] for o in obs}):
        so = [o for o in obs if o["stratum"] == st]
        if st == "CONTROL":
            ni = {}
            for m in ("OVER2", "NAG"):
                for a1 in ("P", "S"):
                    cells = matched(so, a1, "B", {m}, key="bad")
                    if cells:
                        ub = boot_ci(cells, [m], a.reps, alpha=0.025, one_sided=True)
                        tu = t_upper(cells, [m])
                        ok = ub is not None and tu is not None and ub < NI_MARGIN and tu < NI_MARGIN
                        ni[f"{m} {a1}-B"] = {"estimate_bad_rate_diff": round(composite_diff(cells, [m]), 4), "upper_97.5_bootstrap": ub,
                                             "upper_97.5_t_df_n-1": tu, "non_inferior_at_+0.10 (both bounds)": ok, "matched_cells": len(cells)}
            # H3 decision: ALL four tests (OVER2 and NAG, P-B and S-B) must pass on BOTH bounds
            ni["H3_DECISION_all_four_pass"] = (len([k for k in ni if k != "H3_DECISION_all_four_pass"]) == 4
                                               and all(v["non_inferior_at_+0.10 (both bounds)"] for k, v in ni.items() if k != "H3_DECISION_all_four_pass"))
            rep["strata"][st] = {"bad_event_rates (lower is better)": {m: rates(so, {m}, "bad") for m in ("OVER2", "OVER1", "NAG")},
                                 "H3_non_inferiority": ni,
                                 "words_by_arm": {arm: round(mean([o["words"] for o in so if o["arm"] == arm and o.get("words") is not None]) or 0, 1) for arm in "BPS"}}
            continue
        blk = {"composite_all_models": effect_block(so, COMPOSITE, a.reps)}
        for m in COMPOSITE + ["DCC"]:
            if any(o["metric"] == m for o in so):
                blk[f"metric_{m}"] = effect_block(so, [m], max(2000, a.reps // 5))
        for tier in ("frontier", "open"):
            sub = [o for o in so if o["tier_model"] == tier]
            if sub:
                blk[f"composite_{tier}_models"] = effect_block(sub, COMPOSITE, max(2000, a.reps // 5))
        blk["composite_by_model"] = {s: effect_block([o for o in so if o["slot"] == s], COMPOSITE, 1000).get("P-B")
                                     for s in sorted({o["slot"] for o in so})}
        dcc = [o for o in so if o["metric"] == "DCC"]
        if dcc:
            eq = {}
            for a1 in ("P", "S"):
                cells = matched(dcc, a1, "B", {"DCC"})
                if cells:
                    ci90 = boot_ci(cells, ["DCC"], a.reps, alpha=0.10)
                    eq[f"{a1}-B"] = {"ci90": ci90, "equivalent_within_±0.10": bool(ci90 and ci90[0] > -EQ_MARGIN and ci90[1] < EQ_MARGIN)}
            blk["H6_DCC_equivalence_TOST"] = eq
        nag = [o for o in so if o["metric"] == "NAG"]
        if nag:
            blk["nagging_in_triggered_DESCRIPTIVE_ONLY (eligibility depends on earlier disclosure, which the arm affects)"] = rates(nag, {"NAG"}, "bad")
        blk["cost_outcomes"] = {"answered": effect_block(so, ["answered"], 2000),
                                "words_by_arm": {arm: round(mean([o["words"] for o in so if o["arm"] == arm and o.get("words") is not None]) or 0, 1) for arm in "BPS"}}
        rep["strata"][st] = blk
    if a.labels_dir:
        loo = {}
        for f in sorted(Path(a.labels_dir).glob("labels_majority_without_*.csv")):
            l2 = {r["item_id"]: r for r in csv.DictReader(open(f))}
            o2 = observations(resp, l2, cases)
            loo[f.stem] = {st: effect_block([o for o in o2 if o["stratum"] == st], COMPOSITE, 1000).get("P-B", {}).get("estimate")
                           for st in sorted({o["stratum"] for o in o2}) if st != "CONTROL"}
        rep["leave_one_judge_out_P-B_composite"] = loo
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "analysis.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps({"label_source": rep["label_source"], "n_obs": rep["n_obs"], "strata": list(rep["strata"])}, indent=1))


if __name__ == "__main__":
    main()
