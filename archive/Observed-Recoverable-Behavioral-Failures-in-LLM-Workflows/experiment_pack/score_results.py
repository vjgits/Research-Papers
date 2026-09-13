#!/usr/bin/env python3
"""Score RBF pilot outputs using deterministic checks embedded in tasks file."""
import argparse, json, re, csv
from pathlib import Path


def load_tasks(path):
    d={}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                t=json.loads(line); d[t['id']]=t
    return d


def contains_any(text, terms):
    low=text.lower()
    return [t for t in terms if t.lower() in low]


def score(task, output):
    checks=task.get('checks', {})
    failures=[]
    if 'forbidden' in checks:
        hits=contains_any(output, checks['forbidden'])
        if hits:
            failures.append('forbidden_terms:' + '|'.join(hits))
    if 'required_terms' in checks:
        missing=[t for t in checks['required_terms'] if t.lower() not in output.lower()]
        if missing:
            failures.append('missing_required_terms:' + '|'.join(missing))
    # simple numeracy checks for the two QI tasks
    if task['id']=='qi_001':
        expected_cost=0.018*420
        expected_margin=12-expected_cost
        # tolerate if key numbers appear approximately in output
        if not re.search(r'7\.56|\$7\.56', output): failures.append('missing_expected_cost_7.56')
        if not re.search(r'4\.44|\$4\.44', output): failures.append('missing_expected_margin_4.44')
    if task['id']=='qi_002':
        if not re.search(r'75\.6|75\.60|\$75\.60', output): failures.append('missing_expected_cost_75.60')
        if not re.search(r'23\.4|23\.40|\$23\.40', output): failures.append('missing_expected_margin_23.40')
        if not re.search(r'23\.6|23\.64|24%', output.replace(' ','')): failures.append('missing_margin_pct_about_23.6')
    return 1 if failures else 0, ';'.join(failures)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--raw', required=True)
    ap.add_argument('--tasks', default='tasks/evaluation_tasks.jsonl')
    ap.add_argument('--out', required=True)
    args=ap.parse_args()
    tasks=load_tasks(args.tasks)
    rows=[]
    with open(args.raw, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            r=json.loads(line)
            task=tasks.get(r['task_id'])
            if not task or not r.get('ok'):
                fail=1; reason=r.get('error','missing task or failed call')
            else:
                fail, reason=score(task, r.get('output',''))
            rows.append({**r, 'failure': fail, 'failure_reason': reason})
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        fieldnames=['model_spec','task_id','category','ok','failure','failure_reason','latency_sec','output']
        w=csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        w.writeheader(); w.writerows(rows)

if __name__=='__main__':
    main()
