#!/usr/bin/env python3
"""End-to-end mock test: runner -> judges -> majority -> analysis -> human pack. All outputs in a temp dir, marked MOCK."""
import csv, json, os, random, shutil, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import atexit
from fixture_snapshot import placeholder_snapshot  # mock-test placeholder prices only
_snap = placeholder_snapshot(); _snap.__enter__(); atexit.register(lambda: _snap.__exit__(None, None, None))
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests")); sys.path.insert(0, str(ROOT / "scoring"))
os.environ["OPENROUTER_API_KEY"] = "sk-or-MOCK"
os.environ["ICP_TEST_INCLUDE_MOCK"] = "1"
import run_v05 as R, judge_v05 as J
from test_run_v05_mock import MockPost, get_balance, Resp

class JudgePost:
    def __init__(self): self.n = 0; self.rng = random.Random(1)
    def __call__(self, url, headers=None, json=None, timeout=None):
        self.n += 1
        lab = {k: self.rng.choice([0, 1]) for k in J.FIELDS}; lab["OVER"] = self.rng.choice([0, 1, 2])
        import json as js
        return Resp(200, {"model": json["model"], "choices": [{"message": {"content": js.dumps(lab)}, "finish_reason": "stop"}],
                          "usage": {"prompt_tokens": 500, "completion_tokens": 80, "cost": 0.0001}})

d = Path(tempfile.mkdtemp()); ok = True
try:
    rows = [r for r in csv.DictReader(open(ROOT / "data/manifest_main.csv")) if r["case_id"] in {"LH1", "LH7", "R06", "C03", "K01", "R05"} and r["model_slot"] in {"A", "E"}]
    m = d / "m.csv"
    with open(m, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    R.main(["--phase", "main", "--confirm-main", "--manifest", str(m), "--output-dir", str(d / "main"), "--max-cost-usd", "5", "--skip-balance-check", "--global-cap", "1000"], post=MockPost(), get=get_balance(100))
    jp = JudgePost()
    J.main(["--responses", str(d / "main/responses.jsonl"), "--out", str(d / "judge"), "--max-cost-usd", "1", "--skip-balance-check", "--global-cap", "1000"], post=jp)
    labs = list(csv.DictReader(open(d / "judge/labels_majority.csv")))
    n_items = sum(r2["n_dps_done"] for r2 in map(json.loads, open(d / "main/responses.jsonl")))
    print("judge items", len(labs), "expected", n_items, "judge calls", jp.n); ok &= len(labs) == n_items and jp.n == 3 * n_items
    r = subprocess.run([sys.executable, str(ROOT / "scoring/analysis_v05.py"), "--responses", str(d / "main/responses.jsonl"), "--labels", str(d / "judge/labels_majority.csv"),
                        "--label-source", "judge", "--labels-dir", str(d / "judge"), "--out", str(d / "an"), "--reps", "200"], capture_output=True, text=True, env=os.environ)
    print(r.stdout[-600:], r.stderr[-800:]); ok &= r.returncode == 0
    an = json.loads((d / "an/analysis.json").read_text())
    print("strata", list(an["strata"]), "label_source", an["label_source"]); ok &= "MOCK" in an["label_source"] and {"LH", "RCD", "CON", "CONTROL"} <= set(an["strata"])
    r = subprocess.run([sys.executable, str(ROOT / "scoring/make_pack_v05.py"), "--responses", str(d / "main/responses.jsonl"), "--n", "24", "--out", str(d / "pack")], capture_output=True, text=True, env=os.environ)
    print(r.stdout[-400:], r.stderr[-600:]); ok &= r.returncode == 0
    A = list(csv.DictReader(open(d / "pack/annotator_A.csv"))); K = list(csv.DictReader(open(d / "pack/key_private.csv")))
    blind = all("arm" not in row and "model_slot" not in row and "run_id" not in row for row in A)
    print("pack items", len(A), "blind", blind); ok &= blind and len(A) == len(K) > 0
    # mock-fill the human pack (random labels, MOCK) and run the agreement / kappa / arm-guess / PPI script
    rng = random.Random(7)
    for nm in ("annotator_A", "annotator_B"):
        rows2 = list(csv.DictReader(open(d / f"pack/{nm}.csv")))
        for row in rows2:
            for f in J.FIELDS:
                row[f] = str(rng.choice([0, 1]))
            row["arm_guess_B_P_S_unsure"] = rng.choice(["B", "P", "S", "unsure"])
        with open(d / f"pack/{nm}.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows2[0])); w.writeheader(); w.writerows(rows2)
    r = subprocess.run([sys.executable, str(ROOT / "scoring/human_agreement_v05.py"), "--pack", str(d / "pack"), "--judge-labels", str(d / "judge/labels_majority.csv"),
                        "--out", str(d / "agree")], capture_output=True, text=True)
    ag = json.loads((d / "agree/agreement.json").read_text()) if r.returncode == 0 else {}
    print("agreement keys", sorted(ag), r.stderr[-400:]); ok &= r.returncode == 0 and "arm_guess" in ag and "kappa_human_vs_judge" in ag
    an2 = json.loads((d / "an/analysis.json").read_text())
    ok &= "H3_DECISION_all_four_pass" in an2["strata"]["CONTROL"]["H3_non_inferiority"]
    r = subprocess.run([sys.executable, str(ROOT / "scoring/screen_v05.py"), "--responses", str(d / "main/responses.jsonl"), "--out", str(d / "screen.csv")], capture_output=True, text=True)
    ok &= r.returncode == 0
finally:
    shutil.rmtree(d, ignore_errors=True)
print("PIPELINE MOCK TEST:", "PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
