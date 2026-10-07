#!/usr/bin/env python3
"""No Poker Face study runner.

  python run.py estimate --phase calibration          # cost estimate, no calls
  python run.py run --phase calibration --mock         # full offline test (synthetic, not data)
  python run.py run --phase calibration --budget 25    # real run; stops before exceeding $25
  python run.py analyze --phase calibration

Keys come from the environment: OPENAI_API_KEY, ANTHROPIC_API_KEY, ANTHROPIC_WORKSPACE_ID.
"""
import argparse
import json
import sys

from npf import prompts as P
from npf.analysis import simulate_power, summarize, write_report
from npf.clients import BudgetExceeded, Client, Ledger, cost_of
from npf.config import (CONDITIONS, FAMILY, JUDGE_MAX_OUT, JUDGES, PHASES, RUNS, SLOTS_PER_CALL, SOLVE_MODES,
                        SOLVERS, WRITERS)
from npf.pipeline import read_jsonl, stage_code, stage_features, stage_secondary, stage_solve, stage_write

TOK = 3.6  # characters per token, conservative for English prose

# Output-token assumptions per call (visible + reasoning). Writers run at provider defaults,
# so GPT reasoning is the main uncertainty; the high case assumes heavy reasoning.
ASSUME = {
    "item_tokens": 230,                                    # stem + 4 options + rationale, per item
    "writer_reasoning": {"anthropic": (0, 0), "openai": (2500, 8000)},  # (expected, high) per 10-slot call
    "solver_out": {"anthropic": 3, "openai": 12},
    "judge_out": {"anthropic": 380, "openai": 900},       # GPT judge includes low-effort reasoning
}


def estimate(phase, secondary=False):
    cfg = PHASES[phase]
    rows = {"write": [0, 0], "solve": [0, 0], "judge": [0, 0], "secondary": [0, 0]}
    calls = {"write": 0, "solve": 0, "judge": 0, "secondary": 0}
    for dom in cfg["domains"]:
        slots = P.BLUEPRINT[dom]["slots"][:cfg["slots_per_domain"]]
        chunks = [slots[i:i + SLOTS_PER_CALL] for i in range(0, len(slots), SLOTS_PER_CALL)]
        for cond in cfg["conditions"]:
            for w in WRITERS:
                fam = FAMILY[w]
                other = "openai" if fam == "anthropic" else "anthropic"
                for _ in range(cfg["samples"]):
                    for ch in chunks:
                        tin = len(P.writer_prompt(dom, cond, ch)) / TOK
                        vis = ASSUME["item_tokens"] * len(ch)
                        for j, (lo_hi) in enumerate(ASSUME["writer_reasoning"][fam]):
                            rows["write"][j] += cost_of(w, tin, vis + lo_hi)
                        calls["write"] += 1
                        for it in ch:
                            item_in = ASSUME["item_tokens"] * 0.8 + 40
                            for s in SOLVERS[other]:
                                n_modes = len(SOLVE_MODES)
                                c = n_modes * cost_of(s, item_in, ASSUME["solver_out"][other])
                                rows["solve"][0] += c
                                rows["solve"][1] += c * 1.3
                                calls["solve"] += n_modes
                            if dom == "fictional":
                                s = SOLVERS[other][-1]
                                c = cost_of(s, item_in + len(P.SPEC) / TOK, ASSUME["solver_out"][other])
                                rows["solve"][0] += c; rows["solve"][1] += c * 1.3; calls["solve"] += 1
                            jin = (len(P.JUDGE_TEMPLATE) + 600 + (len(P.SPEC) if dom == "fictional" else 0)) / TOK + item_in
                            for jm in JUDGES:
                                c = cost_of(jm, jin, ASSUME["judge_out"][FAMILY[jm]])
                                rows["judge"][0] += c; rows["judge"][1] += c * 1.6; calls["judge"] += 1
    if secondary:  # 4 follow-up arms on W, per writer x domain, then solve+judge the new items
        per = sum(rows[k][0] for k in ("write", "solve", "judge")) / (len(cfg["conditions"]) * cfg["samples"])
        rows["secondary"] = [per * 4 * 0.5 * 1.6, per * 4 * 0.5 * 2.4]   # half the slots, longer prompts (history)
    tot = [sum(v[0] for v in rows.values()), sum(v[1] for v in rows.values())]
    return rows, calls, tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["estimate", "run", "analyze", "secondary", "sessions"])
    ap.add_argument("--phase", default="calibration", choices=list(PHASES))
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--budget", type=float, default=0.0, help="hard spend cap in USD for this phase")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--stages", default="write,features,solve,code,analyze")
    a = ap.parse_args()

    # smoke shares calibration's folder and cache: its calls are exactly the first calls calibration makes
    outdir = RUNS / (("calibration" if a.phase == "smoke" else a.phase) + ("_mock" if a.mock else ""))
    if a.cmd == "estimate":
        rows, calls, tot = estimate(a.phase, secondary=True)
        print(f"Phase: {a.phase}  {PHASES[a.phase]}")
        for k, (lo, hi) in rows.items():
            print(f"  {k:<10} calls={calls[k]:>6}  expected ${lo:7.2f}   high ${hi:7.2f}")
        print(f"  TOTAL      expected ${tot[0]:.2f}   high ${tot[1]:.2f}   (Batch API would halve this)")
        return

    if a.cmd in ("run", "secondary", "sessions") and not a.mock and a.budget <= 0:
        sys.exit("Real runs need --budget (approved USD cap).")
    # mock runs are uncapped unless --budget is given (used to test that the cap stops a run)
    ledger = Ledger(outdir / "ledger.jsonl", a.budget if (a.budget > 0 or not a.mock) else 1e9)
    client = Client(outdir / "cache", ledger, mock=a.mock)
    stages = a.stages.split(",")
    try:
        if a.cmd == "sessions" and PHASES[a.phase].get("design") == "v2":
            from npf import sessions_v2 as S2
            from npf.session_analysis_v2 import analyze as a2
            import random as _r
            from npf.estimate_v2 import calibrated as est_v2   # high case, calibrated on the v2 pilot's measured costs
            cfg = PHASES[a.phase]
            # Waves = complete replicates (all subjects x writers x types). Before each wave, the high-case cost of one
            # replicate must fit in the remaining cap, so a budget stop can only fall BETWEEN waves and always leaves a
            # balanced design. Earlier waves are re-read from the cache at no cost.
            wave_cost = cfg.get("wave_high") or est_v2(cfg["subjects"], cfg["stypes"], 1, high=True)["total"]
            for k in range(1, cfg["reps"] + 1):
                if (not a.mock or a.budget > 0) and ledger.spent + wave_cost > ledger.budget:
                    print(f"STOPPED before wave {k}: spent ${ledger.spent:.2f} + wave high-case ${wave_cost:.2f} > cap ${ledger.budget:.2f}. "
                          f"Complete reps: {k - 1}.")
                    break
                sess = S2.design(cfg["subjects"], cfg["stypes"], k, writers=cfg.get("writers"))
                if "write" in stages:
                    trs, probes, items = S2.run_all(client, sess, outdir, workers=min(a.workers, 12))
                    print(f"[wave {k}/{cfg['reps']}] {len(trs)} sessions, {len(items)} questions  spent ${ledger.spent:.2f}")
                items = read_jsonl(outdir / "items.jsonl")
                if "solve" in stages:
                    stage_solve(client, items, outdir, workers=a.workers)
                    print(f"[solve] spent ${ledger.spent:.2f}")
                if "code" in stages:   # judge sample fixed per item (hash of its id), so it is the same whatever the wave
                    import hashlib as _h
                    sample = [it for it in items if int(_h.sha256(it["id"].encode()).hexdigest()[:8], 16) / 16 ** 8 < cfg.get("judge_share", 0.3)]
                    stage_code(client, sample, outdir, workers=a.workers)
                    print(f"[code] {len(sample)} items judged  spent ${ledger.spent:.2f}")
            res, *_ = a2(outdir, mock=a.mock)
            keys = ("MOCK_NOT_DATA", "n_sessions", "loop_valid", "B1_failure_easing", "B2_claimed_mastery", "holm", "part_A_trigger")
            print(json.dumps({k: res.get(k) for k in keys}, indent=1, default=str))
            return
        if a.cmd == "sessions":
            from npf.sessions import run_all, SUBJECTS
            from npf.session_analysis import analyze as s_analyze
            import random as _r
            reps = PHASES[a.phase].get("reps", 1)
            sess = [{"subject": sj, "writer": w, "stype": st, "rep": rp} for sj in PHASES[a.phase]["subjects"]
                    for w in WRITERS for st in ["C", "F", "FT"] for rp in range(reps)]
            if "write" in stages:
                trs, probes, items = run_all(client, sess, outdir, workers=min(a.workers, 12))
                print(f"[sessions] {len(trs)} sessions, {len(items)} questions  spent ${ledger.spent:.2f}")
            items = read_jsonl(outdir / "items.jsonl")
            if "solve" in stages:
                stage_solve(client, items, outdir, workers=a.workers)
                print(f"[solve] spent ${ledger.spent:.2f}")
            if "code" in stages:  # judges on a fixed 30% sample (seeded), both families, for agreement
                rs = _r.Random(7)
                sample = [it for it in items if rs.random() < PHASES[a.phase].get("judge_share", 0.3)]
                stage_code(client, sample, outdir, workers=a.workers)
                print(f"[code] {len(sample)} items judged  spent ${ledger.spent:.2f}")
            res, *_ = s_analyze(outdir)
            print(json.dumps({k: res[k] for k in ("decision", "passes", "loop_valid", "key_check", "tells_adv_r5_7",
                                                  "tricks_hint_pct", "teach_echo_share", "teach_echo_control_F")}, indent=1))
            return
        if a.cmd == "secondary":
            items = read_jsonl(outdir / "items.jsonl")
            sec = stage_secondary(client, items, outdir, workers=min(a.workers, 6))
            sdir = outdir / "secondary"
            stage_features(sec, sdir)
            stage_solve(client, sec, sdir, workers=a.workers)
            stage_code(client, sec, sdir, workers=a.workers)
            print(f"secondary items: {len(sec)}  spent so far ${ledger.spent:.2f}")
            return
        items = None
        if "write" in stages and a.cmd == "run":
            items = stage_write(client, a.phase, outdir, workers=min(a.workers, 6))
            print(f"[write] items: {len(items)}  spent ${ledger.spent:.2f}")
        items = items or read_jsonl(outdir / "items.jsonl")
        if a.mock:  # mock-only marker so the synthetic solver/judge see the planted cue
            for it in items:
                it["_mock_cue"] = "never needs" in it["stem"]
        if "features" in stages:
            stage_features(items, outdir)
        if "solve" in stages and a.cmd == "run":
            s = stage_solve(client, items, outdir, workers=a.workers)
            print(f"[solve] rows: {len(s)}  spent ${ledger.spent:.2f}")
        if "code" in stages and a.cmd == "run":
            c = stage_code(client, items, outdir, workers=a.workers)
            print(f"[code] rows: {len(c)}  spent ${ledger.spent:.2f}")
        if "analyze" in stages or a.cmd == "analyze":
            df, sl, res = summarize(outdir)
            power = simulate_power(sl)
            write_report(outdir, res, power, a.mock)
            df.to_csv(outdir / "item_table.csv", index=False)
            print(f"[analyze] report -> {outdir / 'report.md'}")
    except BudgetExceeded as e:
        print("STOPPED:", e)
    finally:
        print(f"Total spent this phase: ${ledger.spent:.2f}  (ledger: {ledger.path})")


if __name__ == "__main__":
    main()
