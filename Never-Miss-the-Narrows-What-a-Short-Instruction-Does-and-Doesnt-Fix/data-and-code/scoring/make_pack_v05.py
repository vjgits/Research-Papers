#!/usr/bin/env python3
"""Blinded human-annotation pack for v0.5 (PRIMARY labels once collected).

Stratified sample of decision-point replies: equal per arm within each stratum (RCD, CON, LH, CONTROL), spread across
models and DPs; every item double-annotated (annotator_A.csv, annotator_B.csv, independent random orders). Item ids are
random; model, arm and run are only in key_private.csv. The same checklist fields as the judges, plus free text.
Replay items are NOT included (private; separate pack on request).

  python3 scoring/make_pack_v05.py --responses outputs/main/responses.jsonl --n 192 --out outputs/human_pack_v05
"""
import argparse, csv, json, random, sys, uuid
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scoring"))
from judge_v05 import situation, blind  # noqa: E402

FIELDS = ["SCD", "STR_cut", "STR_disclosed", "DR", "AoC", "ISD", "RoC", "DCC", "NAG", "OVER", "answered", "helpfulness_1to5", "arm_guess_B_P_S_unsure"]


def jl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--responses", required=True)
    ap.add_argument("--n", type=int, default=192)
    ap.add_argument("--seed", type=int, default=505)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cases = {c["case_id"]: c for c in jl(ROOT / "data/cases_v05.jsonl")}
    gold = {g["case_id"]: g for g in jl(ROOT / "data/gold_v05.jsonl")}
    rng = random.Random(a.seed)
    # PAIRED design: a cell = (case, model, DP); a cell is eligible only if all three arms have an OK reply there.
    cells = defaultdict(dict)
    for r in jl(a.responses):
        if r.get("provenance") != "LIVE_PROVIDER_API" and not __import__("os").environ.get("ICP_TEST_INCLUDE_MOCK"):
            continue
        c = cases[r["case_id"]]
        prior = []
        for dp in r["dps"]:
            if dp["status"] == "OK":
                cells[(r["case_id"], r["model_slot"], dp["dp"])][r["arm"]] = (r, dp, list(prior))
            utext = next(x["text"] for x in c["dps"] if x["dp"] == dp["dp"])
            prior.append(f"TRAVELER: {utext}\nASSISTANT: {blind(dp['reply'])}")
    full = {k: v for k, v in cells.items() if set(v) == {"B", "P", "S"}}
    by_stratum = defaultdict(list)
    for k in full:
        c = cases[k[0]]
        by_stratum["CONTROL" if c["condition"] == "control" else c["tier"]].append(k)
    strata = sorted(by_stratum)
    per_stratum = max(1, a.n // (3 * max(1, len(strata))))
    chosen = []
    for st in strata:
        keys = by_stratum[st]
        rng.shuffle(keys)
        # spread across models and cases: round-robin by model slot
        by_slot = defaultdict(list)
        for k in keys:
            by_slot[k[1]].append(k)
        slots = sorted(by_slot)
        picked, i = [], 0
        while len(picked) < per_stratum and any(by_slot.values()):
            s = slots[i % len(slots)]
            if by_slot[s]:
                picked.append(by_slot[s].pop())
            i += 1
        for k in picked:
            for arm in ("B", "P", "S"):
                r, dp, prior = full[k][arm]
                chosen.append((r, dp, prior, (st, arm)))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows, key = [], []
    for r, dp, prior, (st, arm) in chosen:
        c, g = cases[r["case_id"]], gold[r["case_id"]]
        iid = uuid.UUID(int=rng.getrandbits(128)).hex[:10]
        dg = g["dp_gold"][dp["dp"]]
        user = next(x["text"] for x in c["dps"] if x["dp"] == dp["dp"])
        rows.append({"item_id": iid, "situation": situation(c, g), "earlier_turns": "\n---\n".join(prior) if c["tier"] == "LH" else "",
                     "traveler_message": user, "reply_to_score": blind(dp["reply"]), "checklist": json.dumps({m: dg["gold"][m] for m in dg["metrics"]}),
                     **{f: "" for f in FIELDS}, "notes": ""})
        key.append({"item_id": iid, "run_id": r["run_id"], "case_id": r["case_id"], "dp": dp["dp"], "arm": arm, "model_slot": r["model_slot"], "stratum": st})
    for name in ("annotator_A", "annotator_B"):
        order = rows[:]
        rng.shuffle(order)
        with open(out / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(order[0]))
            w.writeheader()
            w.writerows(order)
    with open(out / "key_private.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(key[0]))
        w.writeheader()
        w.writerows(key)
    print(json.dumps({"items": len(rows), "paired_cells_per_stratum": per_stratum, "strata": strata, "out": str(out)}, indent=1))


if __name__ == "__main__":
    main()
