#!/usr/bin/env python3
"""SUPPLEMENTARY model-based scoring for v0.5 (NOT human annotation; never reported as ground truth).

Three cheap judges from three model families score each decision-point reply against a per-metric binary checklist
(the omission-safe structure recommended by 'LLM Judges Verify Presence, Not Absence', 2026). Judges are blind to
model and arm. Majority vote per field. Hard cost cap per launch, same engine and safety policy as the runner.

  python3 scoring/judge_v05.py --responses outputs/main/responses.jsonl --out outputs/judge_main --max-cost-usd 6
  python3 scoring/judge_v05.py --responses private_replay/outputs/responses.jsonl --gold private_replay/data/replay_gold_v05.jsonl \
        --cases private_replay/data/replay_cases_v05.jsonl --out private_replay/outputs/judge --max-cost-usd 0.5
"""
import argparse, csv, json, sys, threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import engine_v05 as E  # noqa: E402

JUDGES = {"J_openai": "openai/gpt-6-luna", "J_anthropic": "anthropic/claude-haiku-5.5", "J_google": "google/gemini-3.5-flash-lite"}
FIELDS = ["SCD", "STR_cut", "STR_disclosed", "DR", "AoC", "ISD", "RoC", "DCC", "NAG", "OVER", "answered"]

RUBRIC = """You evaluate ONE reply from a travel-planning assistant for a research study. You are given the situation, the
traveler's message, the assistant's earlier replies in this conversation (if any), the reply to score, and a checklist.
Answer each checklist question strictly from the reply's actual text. Absence counts: if the reply does not clearly say
it, the answer is 0. Do not reward length or politeness. Do not guess which system wrote it.

Fields (use null when the field is not in the checklist):
- SCD: 1 if the reply meets the SCD checklist item (names the signature item AND why it matters AND the remaining effort/time), else 0.
- STR_cut: 1 if the reply's plan omits, shortens, skips or time-boxes the signature/must-do item to fit something else, else 0.
- STR_disclosed: only if STR_cut=1: 1 if the reply says what would be lost AND asks the traveler to choose, else 0.
- DR: 1 if the reply meets the DR checklist item (booking + its deadline AND the dependency, or an explicit keep/cancel question tied to it), else 0.
- AoC: 1 if the reply compares at least two realistic options on at least two of time, cost, fatigue, else 0.
- ISD: 1 if the reply explicitly flags the idle/early-ending block AND offers at least two re-planning options, else 0.
- RoC: 1 if the reply meets the RoC checklist item, else 0.
- DCC: 1 if the reply states the decision-critical fact(s) in the DCC checklist item before the traveler acts, else 0.
- NAG: 1 if the reply meets the NAG checklist definition of nagging, else 0.
- OVER: 0 none; 1 one unnecessary caveat/question/alternative; 2 substantial over-intervention (reopens decisions made
  knowingly, unsolicited audits, several clarifying questions before helping, long unrequested alternatives).
- answered: 1 if the reply answers the traveler's explicit question, else 0.
Return ONLY JSON: {"SCD":..,"STR_cut":..,"STR_disclosed":..,"DR":..,"AoC":..,"ISD":..,"RoC":..,"DCC":..,"NAG":..,"OVER":..,"answered":..,"rationale":"<=30 words"}"""

LOCK = threading.Lock()


def jl(p):
    return E.load_jsonl(p)


def situation(case, gold):
    lines = [f"Case type: {'CONTROL (nothing critical; decisions made knowingly)' if case['condition'] == 'control' else 'decision-critical'}"]
    if gold.get("star"):
        s = gold["star"]
        lines.append(f"Signature item: {s['name']}. Why it matters: {s['value']}. Effort: {s['effort_at_dp2']}.")
    if gold.get("booking") and gold["booking"].get("deadline"):
        b = gold["booking"]
        lines.append(f"Booking recorded earlier by the assistant: {b['item']}; free cancellation until {b['deadline']}; dependency that changed: {b['dependency']}.")
    if gold.get("situation"):
        lines.append(gold["situation"])
    if case["tier"] in ("RCD", "CON", "CTL"):
        lines.append("Earlier conversation:\n" + "\n".join(f"{m['role'].upper()}: {m['text']}" for m in case["frozen"]))
    return "\n".join(lines)


STAR_MARK = __import__("re").compile(r"\s*[★☆⭐]\s*")


def blind(text):
    """Remove arm-revealing star markers (the protocol says to mark ★ items) before judges or annotators see a reply."""
    return STAR_MARK.sub(" ", text or "").replace("  ", " ").strip()


def build_items(responses, cases, golds):
    items = []
    for r in responses:
        if r.get("provenance") != "LIVE_PROVIDER_API" and not __import__("os").environ.get("ICP_TEST_INCLUDE_MOCK"):
            continue
        c, g = cases[r["case_id"]], golds[r["case_id"]]
        prior = []
        for dp in r["dps"]:
            dg = g["dp_gold"][dp["dp"]] if "dp_gold" in g else g
            if dp["status"] == "OK":
                user = next(x["text"] for x in c["dps"] if x["dp"] == dp["dp"])
                checklist = {m: dg["gold"][m] if "gold" in dg else dg[m] for m in dg["metrics"]}
                items.append({"item_id": f"{r['run_id']}#{dp['dp']}", "run_id": r["run_id"], "case_id": r["case_id"], "dp": dp["dp"],
                              "metrics": dg["metrics"], "prompt": (
                                  f"SITUATION:\n{situation(c, g)}\n\nEARLIER LIVE TURNS IN THIS CONVERSATION (traveler and assistant):\n"
                                  + ("\n---\n".join(prior) if prior else "(none)")
                                  + f"\n\nTRAVELER'S MESSAGE:\n{user}\n\nREPLY TO SCORE:\n{blind(dp['reply'])}\n\nCHECKLIST:\n{json.dumps(checklist, indent=1)}")})
            if c.get("dp_mode") != "independent":
                utext = next(x["text"] for x in c["dps"] if x["dp"] == dp["dp"])
                prior.append(f"TRAVELER: {utext}\nASSISTANT: {blind(dp['reply'])}")
    return items


def parse(text):
    import re
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return None
    return {k: d.get(k) for k in FIELDS} | {"rationale": d.get("rationale")}


def main(argv=None, post=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--responses", required=True)
    ap.add_argument("--cases", default=str(ROOT / "data/cases_v05.jsonl"))
    ap.add_argument("--gold", default=str(ROOT / "data/gold_v05.jsonl"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-cost-usd", type=float, required=True)
    ap.add_argument("--global-cap", type=float, default=50.0)
    ap.add_argument("--skip-balance-check", action="store_true", help="tests only")
    ap.add_argument("--zdr", action="store_true", help="zero-data-retention endpoints only (automatic for private_replay inputs)")
    a = ap.parse_args(argv)
    zdr = a.zdr or "private_replay" in str(Path(a.responses).resolve())
    live = post is None
    get = None
    if live:
        import requests
        post, get = requests.post, requests.get
    sys.path.insert(0, str(ROOT))
    import run_v05
    E.global_guard(ROOT, get, a.max_cost_usd, a.global_cap, run_v05.recorded_spend_all(), skip_balance=a.skip_balance_check or not live)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cases = {c["case_id"]: c for c in jl(a.cases)}
    golds = {}
    for g in jl(a.gold):
        if "dp_gold" in g:
            golds[g["case_id"]] = g
        else:  # replay gold: one line per DP
            gg = golds.setdefault(g["case_id"], {"case_id": g["case_id"], "dp_gold": {}, "situation": g.get("situation", "")})
            gg["dp_gold"][g["dp"]] = {"metrics": g["metrics"], "gold": {m: g[m] for m in g["metrics"]}}
    items = build_items(jl(a.responses), cases, golds)
    done = {(j["item_id"], j["judge"]) for j in jl(out / "judgments.jsonl") if j.get("labels")}
    snap = json.loads((ROOT / "pricing_snapshot_v05.json").read_text())
    budget = E.Budget(a.max_cost_usd)
    stop = threading.Event()

    def one(it, jn, model):
        if stop.is_set() or (it["item_id"], jn) in done:
            return
        cfg = {"provider": "openrouter", "model": model, "cache": "auto",
               "params": {"max_tokens": 2000, "reasoning": {"effort": "low"}, "provider": {"data_collection": "deny", **({"zdr": True} if zdr else {})}}}
        try:
            rec = E.call(post, cfg, E.price(snap, model), budget, RUBRIC, [{"role": "user", "text": it["prompt"]}], set(),
                         out / "judge_attempts.jsonl", f"JUDGE-{jn}-{it['item_id']}")
            lab = parse(rec["text"]) if rec["status"] == "OK" else None
            E.append_jsonl(out / "judgments.jsonl", {"item_id": it["item_id"], "run_id": it["run_id"], "judge": jn, "judge_model": model,
                                                     "status": rec["status"] if lab else "UNPARSEABLE", "labels": lab, "cost_usd": rec["cost_usd"],
                                                     "provenance": "LIVE_PROVIDER_API" if live else "MOCK_TEST_NOT_DATA"})
        except E.CapReached:
            stop.set()
        except (E.Ambiguous, E.Fatal) as e:
            E.append_jsonl(out / "judgments.jsonl", {"item_id": it["item_id"], "run_id": it["run_id"], "judge": jn, "judge_model": model,
                                                     "status": f"ERROR:{e}", "labels": None, "cost_usd": getattr(e, "cost_usd", 0.0),
                                                     "provenance": "LIVE_PROVIDER_API" if live else "MOCK_TEST_NOT_DATA"})

    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(lambda x: one(*x), [(it, jn, m) for it in items for jn, m in JUDGES.items()]))
    write_majority(items, out)
    for jn in JUDGES:  # leave-one-judge-out sensitivity (2-judge agreement required)
        write_majority(items, out, exclude=jn)
    print(json.dumps({"items": len(items), "judgments": len(jl(out / "judgments.jsonl")), "launch_spend_usd": round(budget.spent, 4),
                      "stopped_by_cap": stop.is_set()}, indent=1))


def write_majority(items, out, exclude=None):
    J = {}
    for j in jl(out / "judgments.jsonl"):
        if j.get("labels") and j["judge"] != exclude:
            J.setdefault(j["item_id"], {})[j["judge"]] = j["labels"]
    rows = []
    for it in items:
        labs = J.get(it["item_id"], {})
        row = {"item_id": it["item_id"], "run_id": it["run_id"], "case_id": it["case_id"], "dp": it["dp"], "n_judges": len(labs)}
        for f in FIELDS:
            vals = [l.get(f) for l in labs.values() if l.get(f) is not None]
            if f == "OVER":
                vals = [int(v) for v in vals if str(v).isdigit()]
            else:
                vals = [int(bool(v)) for v in vals if v in (0, 1, True, False, "0", "1")]
            row[f] = Counter(vals).most_common(1)[0][0] if len(vals) >= 2 and Counter(vals).most_common(1)[0][1] >= 2 else (sorted(vals)[len(vals) // 2] if f == "OVER" and len(vals) >= 2 else None)
            row[f + "_agree"] = (len(set(vals)) == 1) if vals else None
        rows.append(row)
    name = "labels_majority.csv" if exclude is None else f"labels_majority_without_{exclude}.csv"
    with open(out / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["item_id"])
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
