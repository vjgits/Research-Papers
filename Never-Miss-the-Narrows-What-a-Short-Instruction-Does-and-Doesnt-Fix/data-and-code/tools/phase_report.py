#!/usr/bin/env python3
"""Summarise a finished phase (smoke / pilot / main / replay): status per model, cost per run and per call,
truncation, caching, state-builder parse rate, words. Reads only local output files.

  python3 tools/phase_report.py outputs/smoke
"""
import json, sys
from collections import defaultdict
from pathlib import Path


def jl(p):
    p = Path(p)
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()] if p.exists() else []


def main(d):
    d = Path(d)
    recs = [r for r in jl(d / "responses.jsonl") + jl(d / "errors.jsonl") if "dps" in r]
    att = jl(d / "attempts.jsonl")
    by = defaultdict(lambda: defaultdict(float))
    for r in recs:
        s = by[r["model_slot"] + " " + r.get("requested_model", "")]
        s["runs"] += 1
        s["runs_ok"] += r["status"] == "OK"
        s["cost"] += r["cost_usd"] or 0
        for c in r.get("calls", []):
            s["calls"] += 1
            s["truncated"] += c["status"] == "TRUNCATED"
            u = c.get("usage") or {}
            s["in_tok"] += u.get("input") or 0
            s["cached_tok"] += u.get("cached_input") or 0
            s["out_tok"] += u.get("output") or 0
            s["reported_cost_calls"] += c.get("cost_source") == "provider_reported"
        for dp in r["dps"]:
            s["dps"] += 1
            s["words"] += dp["words"]
        for sc in r.get("state_calls") or []:
            s["state_calls"] += 1
            s["state_parsed"] += sc["parsed"]
    rows = {}
    for k, s in sorted(by.items()):
        rows[k] = {"runs": int(s["runs"]), "runs_ok": int(s["runs_ok"]), "cost_usd": round(s["cost"], 4),
                   "cost_per_run": round(s["cost"] / max(1, s["runs"]), 5), "cost_per_call": round(s["cost"] / max(1, s["calls"]), 5),
                   "truncation_rate": round(s["truncated"] / max(1, s["calls"]), 3),
                   "cached_share_of_input": round(s["cached_tok"] / max(1, s["in_tok"]), 3),
                   "mean_out_tokens": round(s["out_tok"] / max(1, s["calls"])), "mean_words_per_dp": round(s["words"] / max(1, s["dps"]), 1),
                   "state_parse_rate": round(s["state_parsed"] / s["state_calls"], 3) if s["state_calls"] else None,
                   "cost_reported_by_provider_share": round(s["reported_cost_calls"] / max(1, s["calls"]), 3)}
    errs = defaultdict(int)
    for a in att:
        if a["outcome"] != "OK":
            errs[a["outcome"]] += 1
    status = defaultdict(int)
    for r in recs:
        status[r["status"]] += 1
    out = {"phase_dir": str(d), "total_cost_usd": round(sum(r["cost_usd"] or 0 for r in recs), 4), "run_status": dict(status),
           "non_ok_http_attempts": dict(errs), "by_model": rows}
    print(json.dumps(out, indent=1))
    (d / "phase_report.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "outputs/smoke")
