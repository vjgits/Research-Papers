#!/usr/bin/env python3
"""Validate the frozen v0.5 dataset against the preregistered design rules. Exit 1 on any FAIL."""
import csv, datetime as dt, itertools, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import arms_v05  # noqa: E402

RES = []


def check(name, ok, detail=""):
    RES.append({"check": name, "ok": bool(ok), "detail": detail})


def jl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def ts(s):
    return dt.datetime.strptime(s, "%a %d %b %Y, %H:%M")


def main():
    cases = jl(ROOT / "data/cases_v05.jsonl")
    gold = {g["case_id"]: g for g in jl(ROOT / "data/gold_v05.jsonl")}
    ledger = {r["fact_id"]: r for r in csv.DictReader(open(ROOT / "data/FACT_LEDGER_v05.csv", encoding="utf-8"))}
    ids = [c["case_id"] for c in cases]
    check("unique case ids", len(ids) == len(set(ids)))
    check("gold for every case", set(ids) == set(gold))
    n = len(cases)
    controls = sum(c["condition"] == "control" for c in cases)
    check(">=25% no-nag controls", controls / n >= 0.25, f"{controls}/{n} = {controls / n:.1%}")
    disr = sum(c["tags"]["disruption"] for c in cases)
    check("disruptions 20-30% of scenarios", 0.20 <= disr / n <= 0.30, f"{disr}/{n} = {disr / n:.1%}")
    ctl_disr = sum(c["tags"]["disruption"] for c in cases if c["condition"] == "control")
    check("no disruptions in controls", ctl_disr == 0)
    ml = sum(c["tags"]["more_lodging_efficient"] for c in cases)
    check(">=4 more-lodging/more-time-efficient scenarios", ml >= 4, str(ml))
    UTAH = re.compile(r"\b(utah|zion|bryce|st\.? george|snow canyon|moab|arches national|canyonlands|capitol reef|hurricane, ut|springdale|kanab|salt lake)\b", re.I)
    hits = [c["case_id"] for c in cases if UTAH.search(json.dumps({k: v for k, v in c.items() if k != "tags"})) or UTAH.search(json.dumps(gold[c["case_id"]]))]
    check("no Utah locations anywhere in the test set", not hits, ",".join(hits))
    # unique (region, primary mechanism, calendar) triples; tag Jaccard <= 0.5
    triples = [(c["tags"]["region"], c["tags"]["mechanisms"][0], c["tags"]["calendar"]) for c in cases]
    dup = [t for t in set(triples) if triples.count(t) > 1]
    check("unique (region, mechanism, calendar) triples", not dup, str(dup))

    def tagset(c):
        t = c["tags"]
        return {"r:" + t["region"], "t:" + t["trip_type"], "p:" + t["party"], "c:" + t["calendar"]} | {"m:" + m for m in t["mechanisms"]}
    worst = max(((len(tagset(a) & tagset(b)) / len(tagset(a) | tagset(b)), a["case_id"], b["case_id"])
                 for a, b in itertools.combinations(cases, 2)), default=(0, "", ""))
    check("pairwise tag Jaccard <= 0.5", worst[0] <= 0.5, f"max {worst[0]:.2f} ({worst[1]},{worst[2]})")
    # LH structure
    for c in cases:
        cid, g = c["case_id"], gold[c["case_id"]]
        fr = c["frozen"]
        check(f"{cid}: roles alternate user/assistant", all(m["role"] == ("user" if i % 2 == 0 else "assistant") for i, m in enumerate(fr)))
        tss = [ts(m["ts"]) for m in fr if m["role"] == "user"]
        check(f"{cid}: frozen timestamps non-decreasing", all(a <= b for a, b in zip(tss, tss[1:])))
        dts = [ts(d["ts"]) for d in c["dps"]]
        check(f"{cid}: DPs chronological and after frozen history", all(a < b for a, b in zip(dts, dts[1:])) and (not tss or tss[-1] < dts[0]))
        check(f"{cid}: every DP metric has gold", all(set(d["metrics"]) <= set(g["dp_gold"][d["dp"]]["gold"]) for d in c["dps"]))
        check(f"{cid}: facts exist in ledger", all(f in ledger for f in g["facts"]), str([f for f in g["facts"] if f not in ledger]))
        check(f"{cid}: checkpoints valid", c["checkpoints"] and c["checkpoints"][-1] == len(fr) and all(0 < x <= len(fr) and x % 2 == 0 for x in c["checkpoints"]))
        if c["tier"] == "LH":
            check(f"{cid}: total messages 100-250", 100 <= c["n_total_messages"] <= 250, str(c["n_total_messages"]))
            pats = [re.compile(p, re.I) for p in g["star"]["patterns"]]
            star_idx = [i for i, m in enumerate(fr) if any(p.search(m["text"]) for p in pats)]
            anchors = [i for i, m in enumerate(fr) if m["kind"] == "anchor"]
            early = set(anchors[:4])
            if c["condition"] == "triggered":
                check(f"{cid}: ★ mentioned in frozen history only in the first two anchor exchanges", set(star_idx) <= early and len(star_idx) >= 1,
                      f"idx={star_idx}")
            if c["condition"] == "triggered":
                dist = len(fr) - max(star_idx) if star_idx else None
                check(f"{cid}: ★ last mention >= 90 messages before DP1", dist is not None and dist >= 90, f"distance={dist}")
                bk = g["booking"]
                dl = [i for i, m in enumerate(fr) if re.search(r"free cancellation until|refund", m["text"], re.I) and m["role"] == "assistant"]
                check(f"{cid}: deadline recorded by the assistant in exactly one frozen turn", len(dl) == 1, f"idx={dl}")
                check(f"{cid}: has all six DP roles", {d["role"] for d in c["dps"]} == {"star_day_plan", "star_approach", "deadline_window", "commitment", "final_day_plan", "midday_change"})
                ddl = ts(bk["deadline"].replace("2026 ", "2026, ") if "," not in bk["deadline"] else bk["deadline"])
                dw = [ts(d["ts"]) for d in c["dps"] if d["role"] == "deadline_window"][0]
                hrs = (ddl - dw).total_seconds() / 3600
                check(f"{cid}: deadline window DP is 0-7 h before the deadline", 0 < hrs <= 7, f"{hrs:.1f} h")
        if c["tier"] == "LH":
            night = [m["ts"] for m in fr if m["role"] == "user" and m["kind"] == "filler" and not (7 * 60 + 30 <= ts(m["ts"]).hour * 60 + ts(m["ts"]).minute <= 23 * 60)]
            check(f"{cid}: no night-time filler messages", not night, str(night[:3]))
            filler_txt = " ".join(m["text"] for m in fr if m["kind"] == "filler")
            bad = re.findall(r"easy one to skip|fine to skip|time to rest|rest before dinner|the afternoon light\b|keep stops (a little )?shorter|drop on the day|won't regret", filler_txt, re.I)
            check(f"{cid}: filler has no skip/idle-endorsing phrasing", not bad, str(bad[:3]))
            plans = [m["text"] for m in fr if m["kind"] == "filler" and m["role"] == "assistant" and "**" in m["text"]]
            reps = [p for p in plans if len(re.findall(r"\*\*\d{1,2}:\d{2}\*\* ([^:*]+):", p)) != len(set(re.findall(r"\*\*\d{1,2}:\d{2}\*\* ([^:*]+):", p)))]
            check(f"{cid}: no filler day plan repeats a sight", not reps, f"{len(reps)} plans")
            bad2 = re.findall(r"\brest (in|hour|for)\b|use evenings to rest|shorten the", filler_txt, re.I)
            check(f"{cid}: no leftover rest/shorten phrasing", not bad2, str(bad2[:3]))
            ends = [int(h) * 60 + int(mm) for h, mm in re.findall(r"\*\*(\d{1,2}):(\d{2})\*\* Drive back to", filler_txt)]
            check(f"{cid}: filler day plans end at or after 16:30", all(e >= 16 * 60 + 30 for e in ends), str(sorted(ends)[:3]))
            anchors_a = [m["text"] for m in fr if m["kind"] == "anchor" and m["role"] == "assistant"]
            check(f"{cid}: no anchor dismisses the dependency", not any(re.search(r"change their minds|start is fine|looks good;|makes sense: kansai|cooler morning", x, re.I) for x in anchors_a))
        # no gold leakage into model-facing text
        facing = json.dumps(c["frozen"]) + json.dumps(c["dps"])
        check(f"{cid}: no gold vocabulary in model-facing text", not re.search(r"SILENT TRADEOFF|NAGGING|over-intervention|= fail|= pass", facing))
    # facts used by scored triggered cases should be verified
    weak = sorted({f for c in cases if c["condition"] == "triggered" for f in gold[c["case_id"]]["facts"]
                   if ledger[f]["status"] == "UNVERIFIED"})
    check("WARN-ONLY unverified facts in triggered cases (gold avoids exact values)", True, ",".join(weak))
    # arms
    check("arms: protocol block verbatim present in P and S, absent in B",
          arms_v05.PROTOCOL_BLOCK in arms_v05.system_for("P") and arms_v05.PROTOCOL_BLOCK in arms_v05.system_for("S")
          and "PLANNING PROTOCOL" not in arms_v05.system_for("B"))
    # manifests
    for name in ("main", "pilot", "smoke"):
        rows = list(csv.DictReader(open(ROOT / f"data/manifest_{name}.csv")))
        check(f"manifest_{name}: unique run ids", len(rows) == len({r['run_id'] for r in rows}), str(len(rows)))
        check(f"manifest_{name}: all cases exist", all(r["case_id"] in ids for r in rows))
    main_rows = list(csv.DictReader(open(ROOT / "data/manifest_main.csv")))
    pilot_ids = {r["case_id"] for r in csv.DictReader(open(ROOT / "data/manifest_pilot.csv"))}
    check("pilot cases are a strict subset of main cases", pilot_ids < set(ids))
    fails = [r for r in RES if not r["ok"]]
    out = {"n_checks": len(RES), "n_fail": len(fails), "fails": fails, "all": RES}
    (ROOT / "docs/validation_dataset_v05.json").write_text(json.dumps(out, indent=1))
    for r in RES:
        if not r["ok"] or r["check"].startswith("WARN") or "Jaccard" in r["check"] or "%" in r["detail"]:
            print(("PASS " if r["ok"] else "FAIL ") + r["check"] + (f"  [{r['detail']}]" if r["detail"] else ""))
    print(f"{len(RES) - len(fails)}/{len(RES)} checks passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
