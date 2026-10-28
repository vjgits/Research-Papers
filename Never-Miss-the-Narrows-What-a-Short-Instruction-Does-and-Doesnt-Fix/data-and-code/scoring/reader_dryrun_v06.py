#!/usr/bin/env python3
"""v0.6-dry: decision-outcome DRY RUN with AI readers (method check; NOT human data, never pooled with v0.5).

Question: does a reply leave the traveler able to state what they gain or lose, independent of rubric wording?
  1. READER (two model families, separately): sees ONLY the traveler's message + the blinded reply, answers generic
     questions (options, gain/lose, time-sensitive items, whether to reopen a settled decision). No protocol words.
  2. GRADER (third family): checks the reader's answer against the case's gold tradeoff points (triggered LH DP1-DP5).
Arms B and P only (S excluded). Paired cells only (both arms OK). Hard cost cap; same engine/budget guard as v0.5.

  python3 scoring/reader_dryrun_v06.py --out outputs/dryrun_v06 --max-cost-usd 2.5 [--limit N]
"""
import argparse, json, sys, threading, re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scoring"))
import engine_v05 as E  # noqa: E402
from judge_v05 import blind  # noqa: E402

VERSION = "0.6-dry"
READERS = {"R_openai": "openai/gpt-6-luna", "R_google": "google/gemini-3.5-flash-lite"}
GRADER = "anthropic/claude-haiku-5.5"
ARMS = ("B", "P")

READER_SYS = """You are a traveler on a family trip. You sent your trip assistant the message below and got the reply below.
You have seen NOTHING else, and you know nothing about these places beyond what the reply says. Read it as a normal,
busy traveler would. Answer only from the reply.
Return ONLY JSON:
{"options": [{"choice": "...", "gain": "...", "give_up": "..."}],   // the choices you now understand you could make (empty list if none)
 "time_sensitive": [{"what": "...", "by_when": "..."}],              // anything you must decide or do by a certain time (empty list if none)
 "reopen": true/false,                                               // does this reply make you feel you should reopen something you had already decided?
 "reopen_what": "..." or null,
 "next_step": "one sentence: what you will do next"}"""

GRADER_SYS = """You check what a traveler understood after reading an assistant's reply. You get (a) the traveler's own summary
of what they understood, as JSON, and (b) a list of key points with reference notes. For each point, output 1 only if the
traveler's summary clearly shows they understood that point (paraphrase is fine; vague or missing = 0). Judge only the
traveler's summary, not the reference notes. Return ONLY JSON: {"<point id>": 0 or 1, ..., "note": "<=20 words"}"""


def points_for(gold, dg):
    """Gold tradeoff points a well-informed traveler should be able to state after this decision-point reply."""
    pts, s, b, g = [], gold.get("star") or {}, gold.get("booking") or {}, dg.get("gold", {})
    m = dg["metrics"]
    if "SCD" in m:
        pts.append(("star_value", f"Knows that {s['name']} is special and why: {s['value']}."))
        pts.append(("star_effort", f"Knows roughly what it takes to do it (time/distance/effort): {s['effort_at_dp2']}."))
    if "DR" in m:
        pts.append(("deadline", f"Knows the booking ({b['item']}) can only be cancelled free until a deadline, and why it may no longer fit "
                                f"({b['dependency']}), so a keep/cancel decision is due. Reference: {g.get('DR', '')}"))
    if "AoC" in m:
        pts.append(("two_options", f"Can name at least two realistic options for this decision. Reference: {g.get('AoC', '')}"))
        pts.append(("option_diff", "Knows how the options differ in at least one of time, cost or tiredness."))
    if "ISD" in m:
        pts.append(("spare_time", f"Realises the day will end early, leaving several free hours. Reference: {g.get('ISD', '')}"))
        pts.append(("spare_use", "Knows at least one concrete better use of that time (more sights, driving part of the next "
                                 "day's drive today, or going home early)."))
    return pts


def parse_obj(t):
    mm = re.search(r"\{.*\}", t or "", re.S)
    if not mm:
        return None
    try:
        return json.loads(re.sub(r"//[^\n]*", "", mm.group(0)))
    except ValueError:
        return None


def build_cells():
    cases = {c["case_id"]: c for c in E.load_jsonl(ROOT / "data/cases_v05.jsonl")}
    golds = {g["case_id"]: g for g in E.load_jsonl(ROOT / "data/gold_v05.jsonl")}
    by = {}
    for r in E.load_jsonl(ROOT / "outputs/main/responses.jsonl"):
        if r.get("provenance") != "LIVE_PROVIDER_API" or r["arm"] not in ARMS:
            continue
        for dp in r["dps"]:
            if dp["status"] == "OK" and dp.get("reply"):
                by.setdefault((r["case_id"], r["model_slot"], dp["dp"]), {})[r["arm"]] = (r["run_id"], dp["reply"])
    items = []
    for (cid, slot, dpn), arms in sorted(by.items()):
        if set(arms) != set(ARMS):
            continue
        c, g = cases[cid], golds[cid]
        control = c["condition"] == "control"
        dg = g["dp_gold"][dpn] if "dp_gold" in g else g
        if not control and not (c["tier"] == "LH" and dpn in ("DP1", "DP2", "DP3", "DP4", "DP5")):
            continue
        user = next(x["text"] for x in c["dps"] if x["dp"] == dpn)
        pts = [] if control else points_for(g, dg)
        for arm, (run_id, reply) in arms.items():
            items.append({"item_id": f"{run_id}#{dpn}", "case_id": cid, "tier": c["tier"], "control": control, "slot": slot,
                          "dp": dpn, "arm": arm, "user": user, "reply": blind(reply), "points": pts})
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-cost-usd", type=float, required=True)
    ap.add_argument("--global-cap", type=float, default=50.0)
    ap.add_argument("--limit", type=int, default=0, help="smoke: first N items only")
    a = ap.parse_args()
    import requests
    sys.path.insert(0, str(ROOT))
    out = Path(a.out)
    # v0.5's recorded_spend_all() double-counts copied outputs (e.g. sens_combined duplicates main, so recorded spend exceeded
    # provider-reported usage). The guard therefore uses provider-reported usage since the baseline (authoritative),
    # or this dry run's own recorded spend if larger.
    own = sum(float(j.get("cost_usd") or 0) for d in ROOT.glob("outputs/dryrun_v06*") for j in E.load_jsonl(d / "judgments.jsonl"))
    E.global_guard(ROOT, requests.get, a.max_cost_usd, a.global_cap, own)
    out.mkdir(parents=True, exist_ok=True)
    items = build_cells()
    if a.limit:
        items = items[:a.limit]
    (out / "items.json").write_text(json.dumps({"version": VERSION, "n": len(items)}, indent=1))
    snap = json.loads((ROOT / "pricing_snapshot_v05.json").read_text())
    budget, stop, lock = E.Budget(a.max_cost_usd), threading.Event(), threading.Lock()
    done = {(j["item_id"], j["role"]) for j in E.load_jsonl(out / "judgments.jsonl") if j.get("parsed")}

    def cfg(model):
        return {"provider": "openrouter", "model": model, "cache": "auto",
                "params": {"max_tokens": 1500, "reasoning": {"effort": "low"}, "provider": {"data_collection": "deny"}}}

    def ask(model, system, prompt, call_id):
        rec = E.call(requests.post, cfg(model), E.price(snap, model), budget, system, [{"role": "user", "text": prompt}], set(),
                     out / "attempts.jsonl", call_id)
        return rec, (parse_obj(rec["text"]) if rec["status"] == "OK" else None)

    def log(it, role, model, rec, parsed):
        with lock:
            E.append_jsonl(out / "judgments.jsonl", {"version": VERSION, "item_id": it["item_id"], "case_id": it["case_id"],
                                                     "slot": it["slot"], "dp": it["dp"], "arm": it["arm"], "control": it["control"],
                                                     "role": role, "model": model, "status": rec["status"], "parsed": parsed,
                                                     "cost_usd": rec["cost_usd"], "provenance": "LIVE_PROVIDER_API"})

    def one(it, rn, rmodel):
        if stop.is_set():
            return
        try:
            key = (it["item_id"], rn)
            reading = None
            if key in done:
                reading = next(j["parsed"] for j in E.load_jsonl(out / "judgments.jsonl") if (j["item_id"], j["role"]) == key and j.get("parsed"))
            else:
                rec, reading = ask(rmodel, READER_SYS, f"YOUR MESSAGE:\n{it['user']}\n\nASSISTANT'S REPLY:\n{it['reply']}", f"READ-{rn}-{it['item_id']}")
                log(it, rn, rmodel, rec, reading)
            if reading is None or it["control"] or not it["points"] or (it["item_id"], "G_" + rn) in done:
                return
            pts = "\n".join(f"- {pid}: {txt}" for pid, txt in it["points"])
            rec, grade = ask(GRADER, GRADER_SYS, f"TRAVELER'S SUMMARY (JSON):\n{json.dumps(reading, ensure_ascii=False)}\n\nKEY POINTS:\n{pts}",
                             f"GRADE-{rn}-{it['item_id']}")
            log(it, "G_" + rn, GRADER, rec, grade)
        except E.CapReached:
            stop.set()
        except (E.Ambiguous, E.Fatal) as e:
            with lock:
                E.append_jsonl(out / "judgments.jsonl", {"version": VERSION, "item_id": it["item_id"], "role": rn, "status": f"ERROR:{e}",
                                                         "parsed": None, "cost_usd": getattr(e, "cost_usd", 0.0), "provenance": "LIVE_PROVIDER_API"})

    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(lambda x: one(*x), [(it, rn, m) for it in items for rn, m in READERS.items()]))
    print(json.dumps({"items": len(items), "spend_usd": round(budget.spent, 4), "stopped_by_cap": stop.is_set()}, indent=1))


if __name__ == "__main__":
    main()
