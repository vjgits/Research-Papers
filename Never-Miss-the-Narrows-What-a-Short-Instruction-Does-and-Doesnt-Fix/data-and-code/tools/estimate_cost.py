#!/usr/bin/env python3
"""A-priori cost model for v0.5 (BEFORE any live call), and pilot-calibrated projection (AFTER the pilot).

  python3 tools/estimate_cost.py                      # a-priori, assumptions below
  python3 tools/estimate_cost.py --from-pilot outputs/pilot   # uses measured pilot cost per call to project main/replay/judging

A-priori assumptions (stated, not measured): output tokens per DP call (reply + low-effort reasoning) = OUT_DP;
state-builder call output = OUT_STATE; S-arm replies add OUT_S_EXTRA; caching as described in engine_v05.
"""
import argparse, csv, json, math, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import arms_v05 as A  # noqa: E402

OUT_DP, OUT_STATE, OUT_S_EXTRA = 700, 900, 250
JUDGES = {"openai/gpt-6-luna": (0.1e-6, 0.5e-6), "anthropic/claude-haiku-5.5": (0.1e-6, 0.5e-6), "google/gemini-3.5-flash-lite": (0.3e-6, 2.5e-6)}
JUDGE_IN, JUDGE_OUT = 3600, 600  # v0.5.1: judges see all earlier live turns untruncated


def tok(t):
    return math.ceil(len(t) / 3.6)


def jl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def prices(model, snap):
    p = snap["models"][model]
    g = lambda k, d=None: float(p[k]) if p.get(k) not in (None, "") else d  # noqa: E731
    return g("prompt"), g("completion"), g("input_cache_read", g("prompt")), g("input_cache_write", g("prompt"))


def run_cost(case, arm, cfg, snap):
    pin, pout, pread, pwrite = prices(cfg["model"], snap)
    caching = cfg.get("cache") in ("explicit", "auto")
    sys_t = tok(A.system_for(arm))
    frozen = [tok(m["text"]) for m in case["frozen"]]
    F = sum(frozen) + 6 * len(frozen)
    cost = 0.0
    if arm == "S":
        prev = 0
        for cp in case["checkpoints"]:
            seg = sum(frozen[prev:cp]) + 6 * (cp - prev)
            cost += (tok(A.STATE_BUILDER_SYSTEM) + 800 + seg) * pin + OUT_STATE * pout
            prev = cp
    out_dp = OUT_DP + (OUT_S_EXTRA if arm == "S" else 0)
    if case.get("dp_mode") == "independent":
        prev_cut_tokens = 0
        for k, dp in enumerate(case["dps"]):
            cut_t = sum(frozen[:dp["history_upto"]]) + 6 * dp["history_upto"] + sys_t
            new_user = tok(dp["text"]) + (800 if arm == "S" else 0)
            if caching:
                cost += prev_cut_tokens * pread + (cut_t - prev_cut_tokens) * pwrite + new_user * pin
            else:
                cost += (cut_t + new_user) * pin
            prev_cut_tokens = cut_t
            cost += out_dp * pout
        return cost
    hist = 0
    cached_prefix = 0
    for k, dp in enumerate(case["dps"]):
        new_user = tok(dp["text"]) + (800 if arm == "S" else 0)
        total_in = sys_t + F + hist + new_user
        if caching and total_in >= 1024:
            if k == 0:
                cost += (sys_t + F) * pwrite + (hist + new_user) * pin
                cached_prefix = sys_t + F
            else:
                cost += cached_prefix * pread + (total_in - cached_prefix) * pwrite
                cached_prefix = total_in - new_user
        else:
            cost += total_in * pin
        cost += out_dp * pout
        hist += tok(dp["text"]) + out_dp * 0.6  # visible reply ~60% of output tokens
    return cost


def apriori(phase_rows, cases, models, snap):
    by = defaultdict(float)
    for r in phase_rows:
        c = cases[r["case_id"]]
        by[(r["model_slot"], c["tier"])] += run_cost(c, r["arm"], models[r["model_slot"]], snap)
    return by


def judge_cost(n_replies):
    per = sum(JUDGE_IN * a + JUDGE_OUT * b for a, b in JUDGES.values())
    return n_replies * per


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-pilot", default="")
    a = ap.parse_args()
    snap = json.loads((ROOT / "pricing_snapshot_v05.json").read_text())
    models = json.loads((ROOT / "models_v05.json").read_text())["slots"]
    cases = {c["case_id"]: c for c in jl(ROOT / "data/cases_v05.jsonl")}
    rp = ROOT / "private_replay/data/replay_cases_v05.jsonl"
    rcases = {c["case_id"]: c for c in jl(rp)} if rp.exists() else {}
    phases = {p: list(csv.DictReader(open(ROOT / f"data/manifest_{p}.csv"))) for p in ("smoke", "pilot", "main")}
    main_slots = [s for s, m in models.items() if m.get("main", True)]
    phases["replay"] = [{"case_id": cid, "arm": arm, "model_slot": s} for cid in rcases for arm in A.ARMS for s in main_slots]
    phases["replay_astra_optional"] = [{"case_id": cid, "arm": arm, "model_slot": "X"} for cid in rcases for arm in A.ARMS]
    allc = {**cases, **rcases}
    report = {"assumptions": {"out_tokens_per_dp_call": OUT_DP, "out_tokens_state_call": OUT_STATE, "s_arm_extra_out": OUT_S_EXTRA,
                              "judge_in_tokens": JUDGE_IN, "judge_out_tokens": JUDGE_OUT, "judges": list(JUDGES)},
              "phases": {}}
    calib = None
    if a.from_pilot:
        calib = calibrate(Path(a.from_pilot), cases, models, snap)
        report["pilot_calibration"] = calib
    for ph, rows in phases.items():
        by = apriori(rows, allc, models, snap)
        if calib:
            by = {k: v * calib["ratio_by_slot"].get(k[0], calib["ratio_overall"]) for k, v in by.items()}
        per_slot = defaultdict(float)
        for (s, tier), v in by.items():
            per_slot[s] += v
        n_dp = sum(len(allc[r["case_id"]]["dps"]) for r in rows)
        report["phases"][ph] = {"runs": len(rows), "dp_replies": n_dp, "total_usd": round(sum(by.values()), 2),
                                "by_slot_usd": {f"{s} {models[s]['model']}": round(v, 2) for s, v in sorted(per_slot.items())},
                                "by_tier_usd": {t: round(sum(v for (s, tt), v in by.items() if tt == t), 2) for t in sorted({k[1] for k in by})}}
    report["judging"] = {ph: round(judge_cost(report["phases"][ph]["dp_replies"]), 2) for ph in ("main", "replay")}
    print(json.dumps(report, indent=1))
    return report


def calibrate(pilot_dir, cases, models, snap):
    """ratio = measured pilot cost / a-priori modelled cost for the same runs, per model slot."""
    rec = [json.loads(l) for f in ("responses.jsonl", "errors.jsonl") if (pilot_dir / f).exists() for l in open(pilot_dir / f) if l.strip()]
    rec = [r for r in rec if r.get("provenance") == "LIVE_PROVIDER_API" and r.get("case_id") in cases and r.get("n_dps_done") == r.get("n_dps_planned")]
    meas, mod = defaultdict(float), defaultdict(float)
    for r in rec:
        meas[r["model_slot"]] += r["cost_usd"] or 0
        mod[r["model_slot"]] += run_cost(cases[r["case_id"]], r["arm"], models[r["model_slot"]], snap)
    ratio = {s: round(meas[s] / mod[s], 3) for s in meas if mod[s] > 0}
    overall = round(sum(meas.values()) / max(1e-9, sum(mod.values())), 3)
    return {"complete_pilot_runs": len(rec), "measured_usd": round(sum(meas.values()), 4), "modelled_usd": round(sum(mod.values()), 4),
            "ratio_by_slot": ratio, "ratio_overall": overall}


if __name__ == "__main__":
    main()
