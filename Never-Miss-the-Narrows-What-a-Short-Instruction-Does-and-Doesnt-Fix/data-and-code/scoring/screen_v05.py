#!/usr/bin/env python3
"""Deterministic cue screen (free, no API). A crude keyword proxy used ONLY as a cross-check on the LLM judges and to
triage the human pack. Never reported as an outcome measure on its own.

  python3 scoring/screen_v05.py --responses outputs/main/responses.jsonl --out outputs/screen_main.csv
"""
import argparse, csv, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPTION = re.compile(r"(^|\n)\s*(option\s*[a-c1-3]|[a-c][\).:]|\d[\).]\s|\*\*option)|\bor\b.*\binstead\b|\balternativ|\bvs\.?\b|\bversus\b", re.I | re.M)
IDLE = re.compile(r"\b(idle|free (afternoon|evening|time)|nothing (planned|scheduled)|early finish|done early|extra time|spare (time|afternoon)|gap)\b", re.I)
SHIFT = re.compile(r"\b(drive (home|on|partway|part of the way)|head home|go home|earlier flight|move .* to today|tonight instead|push)\b", re.I)


def jl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--responses", required=True)
    ap.add_argument("--gold", default=str(ROOT / "data/gold_v05.jsonl"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    gold = {g["case_id"]: g for g in jl(a.gold)}
    rows = []
    for r in jl(a.responses):
        g = gold.get(r["case_id"], {})
        sp = [re.compile(p, re.I) for p in (g.get("star") or {}).get("patterns", [])]
        bp = [re.compile(p, re.I) for p in (g.get("booking") or {}).get("patterns", [])]
        for dp in r["dps"]:
            t = dp["reply"]
            rows.append({"item_id": f"{r['run_id']}#{dp['dp']}", "case_id": r["case_id"], "arm": r["arm"], "slot": r["model_slot"], "dp": dp["dp"],
                         "cue_star": int(any(p.search(t) for p in sp)) if sp else "",
                         "cue_booking_and_deadline": int(all(p.search(t) for p in bp)) if bp else "",
                         "cue_options": len(OPTION.findall(t)), "cue_idle": int(bool(IDLE.search(t))), "cue_shift": int(bool(SHIFT.search(t))),
                         "words": dp["words"]})
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["item_id"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} replies screened -> {a.out}")


if __name__ == "__main__":
    main()
