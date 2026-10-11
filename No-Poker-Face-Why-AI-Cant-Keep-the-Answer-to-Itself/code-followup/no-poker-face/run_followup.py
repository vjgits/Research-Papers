#!/usr/bin/env python3
"""Follow-up study (Addendum 2) runner.
  python run_followup.py estimate                 # exact cost from the main run's measured per-call costs; no calls
  python run_followup.py run --mock               # offline test (synthetic; never data)
  python run_followup.py run --budget 100         # real run, hard cap
  python run_followup.py analyze [--mock]
"""
import argparse, json, sys
from collections import defaultdict
from pathlib import Path

from npf.clients import Client, Ledger
from npf.config import RUNS
from npf import followup as FU
from npf.followup_analysis import analyze

MEASURED = Path("/home/claude/main_run/npf-frozen/runs/main_sessions/ledger.jsonl")
MEASURED_G = Path("/home/claude/gemini_arm_run/npf/runs/gemini_arm/ledger.jsonl")


def per_session_costs():
    """Mean measured cost per C session, by writer and call kind, from the main run and Gemini arm ledgers."""
    tot, sess = defaultdict(float), defaultdict(set)
    for path in (MEASURED, MEASURED_G):
        if not path.exists():
            continue
        for l in path.open():
            r = json.loads(l); t = r["tag"].split("|")
            if t[0] in ("session2", "learner2"):
                sid = t[1:5]
            elif t[0] == "panel":
                sid = t[2:6]
            elif t[0] == "probe2" and t[1] in ("nohist", "spec"):
                sid = t[3:7]
            else:
                continue
            if len(sid) < 4 or sid[2] != "C":
                continue
            kind = {"session2": "writer", "learner2": "learner", "panel": "panel", "probe2": "probes"}[t[0]]
            tot[(sid[0], kind)] += r["cost_usd"]; sess[sid[0]].add("|".join(sid))
    return {(w, k): v / len(sess[w]) for (w, k), v in tot.items()}


def wave_cost(sessions, high=True):
    pc = per_session_costs()
    c = 0.0
    for s in sessions:
        w = s["writer"]
        wm = (1.5 if high else 1.15) if s["stype"] == "CFIX" else (1.3 if high else 1.0)
        c += pc[(w, "writer")] * wm + sum(pc.get((w, k), 0) for k in ("learner", "panel", "probes")) * (1.3 if high else 1.0)
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["estimate", "run", "analyze"])
    ap.add_argument("--mock", action="store_true"); ap.add_argument("--budget", type=float, default=0.0)
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    outdir = RUNS / ("followup" + ("_mock" if a.mock else ""))
    if a.cmd == "estimate":
        pc = per_session_costs()
        for k, v in sorted(pc.items()):
            print(f"  measured per C session {k}: ${v:.3f}")
        allss = FU.all_sessions()
        print(f"sessions: {len(allss)}  expected ${wave_cost(allss, False):.2f}  high ${wave_cost(allss, True):.2f}")
        for grp in ("confirm", "gemini"):
            ss = [s for s in allss if s["group"] == grp]
            print(f"  {grp}: {len(ss)} sessions  expected ${wave_cost(ss, False):.2f}  high ${wave_cost(ss, True):.2f}")
        return
    if a.cmd == "analyze":
        print(json.dumps(analyze(outdir, mock=a.mock), indent=1, default=str)); return
    if not a.mock and a.budget <= 0:
        sys.exit("Real runs need --budget (approved USD cap).")
    ledger = Ledger(outdir / "ledger.jsonl", a.budget if a.budget > 0 else 1e9)
    client = Client(outdir / "cache", ledger, mock=a.mock)
    FU.run(client, ledger, outdir, wave_high=lambda ss: wave_cost(ss, True) if not a.mock or a.budget > 0 else 0, workers=a.workers)
    print(json.dumps(analyze(outdir, mock=a.mock), indent=1, default=str))
    print(f"Total spent: ${ledger.spent:.2f}")


if __name__ == "__main__":
    main()
