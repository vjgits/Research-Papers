#!/usr/bin/env python3
"""Build the frozen ICP v0.5 dataset from the scenario sources.

Outputs (data/):
  cases_v05.jsonl     model-facing material only: frozen messages (with timestamps), DP user texts, checkpoints
  gold_v05.jsonl      private scoring material (never sent to models under test)
  manifest_main.csv   every (case, arm, model, trial) run of the main study
  manifest_pilot.csv  pilot subset; manifest_smoke.csv  smoke subset
  build_info.json     dataset version, sha256 of every source/output file, counts
"""
import csv, datetime as dt, hashlib, json, math, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import filler_v05, arms_v05  # noqa: E402
from scenarios_lh_v05 import LH  # noqa: E402
from scenarios_short_v05 import S as SHORT  # noqa: E402

DATASET_VERSION = "0.5.2"
TS_FMT = "%a %d %b %Y, %H:%M"
MODELS_FILE = ROOT / "models_v05.json"


def parse_ts(s):
    return dt.datetime.strptime(s.strip(), TS_FMT)


def fmt_ts(d):
    return d.strftime("%a ") + str(d.day) + d.strftime(" %b %Y, %H:%M")


def daytime_spread(d0, d1, n, start_h=7.5, end_h=23.0):
    """n timestamps evenly spread over the waking hours (07:30-23:00) between d0 and d1 (no night-time messages)."""
    if n <= 0:
        return []
    mins, cur = [], d0
    step = dt.timedelta(minutes=1)
    while cur <= d1:
        h = cur.hour + cur.minute / 60
        if start_h <= h <= end_h:
            mins.append(cur)
        cur += step
    if not mins:
        mins = [d0]
    return [mins[min(len(mins) - 1, round(i * (len(mins) - 1) / max(1, n - 1)))] for i in range(n)]


def tag_user(ts, text):
    return f"[{ts}] {text}"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build_lh(case):
    slots = case["slots"]
    forbidden = [p for p in case["star"].get("name", "").split(" (")[0:1]] + ["cancel", "refund", "deadline", "book"]
    forbidden += [w for w in ("overlook", "inspiration point", "hooker lake", "diamond beach", "yotsutsuji",
                              "great waterfall", "veliki slap", "moro rock", "arthur's seat", "general sherman")]
    script = case["script"]
    n_anchor_msgs = 2 * sum(1 for s in script if s[0] == "A")
    n_fill_pairs = max(0, (case["target_frozen"] - n_anchor_msgs) // 2)
    fill_segs = [i for i, s in enumerate(script) if s[0] == "FILL"]
    by_phase = {"pre": [i for i in fill_segs if script[i][1] == "pre"], "trip": [i for i in fill_segs if script[i][1] == "trip"]}
    share = {"pre": 0.62, "trip": 0.38}
    alloc = {}
    pairs_by_phase = {}
    for ph, segs in by_phase.items():
        if not segs:
            continue
        n_ph = round(n_fill_pairs * share[ph]) if by_phase["pre"] and by_phase["trip"] else n_fill_pairs
        pairs_by_phase[ph] = filler_v05.generate(slots, ph, n_ph, seed=f"{case['case_id']}-{ph}", forbidden=forbidden)
        n_ph = len(pairs_by_phase[ph])
        base, extra = divmod(n_ph, len(segs))
        for k, i in enumerate(segs):
            alloc[i] = base + (1 if k < extra else 0)
    msgs, anchors, cps = [], [], []
    cursor = {"pre": 0, "trip": 0}
    for i, s in enumerate(script):
        if s[0] == "A":
            _, ts, u, a = s
            anchors.append(len(msgs))
            msgs.append({"role": "user", "text": tag_user(ts, u), "ts": ts, "kind": "anchor"})
            msgs.append({"role": "assistant", "text": a, "kind": "anchor"})
            nxt = script[i + 1][0] if i + 1 < len(script) else None
            if nxt == "FILL":
                cps.append(len(msgs))
        else:
            _, ph, t0, t1 = s
            n = alloc.get(i, 0)
            pairs = pairs_by_phase[ph][cursor[ph]:cursor[ph] + n]
            cursor[ph] += n
            times = daytime_spread(parse_ts(t0), parse_ts(t1), len(pairs))
            for k, (u, a) in enumerate(pairs):
                ts = fmt_ts(times[k])
                msgs.append({"role": "user", "text": tag_user(ts, u), "ts": ts, "kind": "filler"})
                msgs.append({"role": "assistant", "text": a, "kind": "filler"})
    if not cps or cps[-1] != len(msgs):
        cps.append(len(msgs))
    # merge tiny checkpoint segments (< 6 messages) into the next one
    merged, prev = [], 0
    for c in cps:
        if c - prev >= 6 or c == len(msgs):
            merged.append(c)
            prev = c
    return msgs, sorted(set(merged))


def build_short(case):
    msgs = []
    for ts, u, a in case["history"]:
        msgs.append({"role": "user", "text": tag_user(ts, u), "ts": ts, "kind": "anchor"})
        msgs.append({"role": "assistant", "text": a, "kind": "anchor"})
    return msgs, [len(msgs)]


def est_tokens(text):
    return math.ceil(len(text) / 3.6)


def main():
    cases, golds = [], []
    for c in LH:
        msgs, cps = build_lh(c)
        cases.append({"case_id": c["case_id"], "tier": "LH", "condition": c["condition"], "title": c["title"],
                      "tags": c["tags"], "frozen": msgs, "checkpoints": cps,
                      "dps": [{"dp": d["dp"], "role": d["role"], "ts": d["ts"], "text": tag_user(d["ts"], d["text"]),
                               "metrics": d["metrics"]} for d in c["dps"]]})
        golds.append({"case_id": c["case_id"], "tier": "LH", "condition": c["condition"], "facts": c["facts"],
                      "star": c["star"], "booking": c["booking"],
                      "dp_gold": {d["dp"]: {"metrics": d["metrics"], "gold": d["gold"], "role": d["role"]} for d in c["dps"]}})
    for c in SHORT:
        msgs, cps = build_short(c)
        cases.append({"case_id": c["case_id"], "tier": c["tier"], "condition": c["condition"], "title": c["title"],
                      "tags": c["tags"], "frozen": msgs, "checkpoints": cps,
                      "dps": [{"dp": d["dp"], "role": d["role"], "ts": d["ts"], "text": tag_user(d["ts"], d["text"]),
                               "metrics": d["metrics"]} for d in c["dps"]]})
        golds.append({"case_id": c["case_id"], "tier": c["tier"], "condition": c["condition"], "facts": c["facts"],
                      "source": c["source"],
                      "dp_gold": {d["dp"]: {"metrics": d["metrics"], "gold": d["gold"], "role": d["role"]} for d in c["dps"]}})
    for c in cases:
        c["n_frozen"] = len(c["frozen"])
        c["n_total_messages"] = len(c["frozen"]) + 2 * len(c["dps"])
        c["est_frozen_tokens"] = sum(est_tokens(m["text"]) for m in c["frozen"])
    data = ROOT / "data"
    with open(data / "cases_v05.jsonl", "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    with open(data / "gold_v05.jsonl", "w", encoding="utf-8") as f:
        for g in golds:
            f.write(json.dumps(g, ensure_ascii=False) + "\n")
    # manifests
    models = json.loads(MODELS_FILE.read_text())["slots"]
    main_slots = [s for s, m in models.items() if m.get("main", True)]
    rows = []
    for c in cases:
        for arm in arms_v05.ARMS:
            for s in main_slots:
                rows.append({"run_id": f"v05-{c['case_id']}-{arm}-{s}-t1", "case_id": c["case_id"], "arm": arm, "model_slot": s, "trial": 1})
    write_manifest(data / "manifest_main.csv", rows)
    pilot_cases = {"LH1", "R06", "C03", "K01"}  # one long case, one RCD, one constructed, one control
    write_manifest(data / "manifest_pilot.csv", [dict(r, run_id=r["run_id"].replace("v05-", "v05pilot-")) for r in rows if r["case_id"] in pilot_cases])
    smoke = [{"run_id": f"v05smoke-R06-{arm}-{s}-t1", "case_id": "R06", "arm": arm, "model_slot": s, "trial": 1}
             for s in main_slots for arm in ("B", "S")]
    write_manifest(data / "manifest_smoke.csv", smoke)
    srcs = ["src/arms_v05.py", "src/filler_v05.py", "src/scenarios_lh_v05.py", "src/scenarios_short_v05.py", "src/build_v05.py",
            "models_v05.json", "data/FACT_LEDGER_v05.csv"]
    outs = ["data/cases_v05.jsonl", "data/gold_v05.jsonl", "data/manifest_main.csv", "data/manifest_pilot.csv", "data/manifest_smoke.csv"]
    info = {"dataset_version": DATASET_VERSION, "built_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "sha256": {p: sha(ROOT / p) for p in srcs + outs},
            "counts": {"cases": len(cases), "by_tier": {t: sum(c["tier"] == t for c in cases) for t in ("LH", "RCD", "CON", "CTL")},
                       "controls": sum(c["condition"] == "control" for c in cases), "dps": sum(len(c["dps"]) for c in cases),
                       "main_runs": len(rows), "pilot_runs": sum(1 for r in rows if r["case_id"] in pilot_cases), "smoke_runs": len(smoke)},
            "lh_lengths": {c["case_id"]: {"frozen": c["n_frozen"], "total": c["n_total_messages"], "est_tokens": c["est_frozen_tokens"]}
                           for c in cases if c["tier"] == "LH"}}
    (data / "build_info.json").write_text(json.dumps(info, indent=1))
    print(json.dumps(info["counts"], indent=1))
    print(json.dumps(info["lh_lengths"], indent=1))


def write_manifest(p, rows):
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["run_id", "case_id", "arm", "model_slot", "trial"])
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
