import re, json, csv
from pathlib import Path
from .schemas import Task

def load_tasks(path):
    tasks={}
    with open(path, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                t=Task.model_validate_json(line)
                tasks[t.id]=t
    return tasks

def deterministic_score(text, task: Task):
    low=text.lower()
    passed=True
    reasons=[]
    for term in task.checks.required_terms:
        if term.lower() not in low:
            passed=False; reasons.append(f"missing_required:{term}")
    for term in task.checks.forbidden_terms:
        if term.lower() in low:
            passed=False; reasons.append(f"forbidden_present:{term}")
    for ne in task.checks.numeric_expectations:
        pattern=ne.get('pattern')
        expected=ne.get('expected')
        tol=float(ne.get('tolerance',0))
        m=re.search(pattern, text) if pattern else None
        if not m:
            passed=False; reasons.append(f"numeric_missing:{pattern}")
        else:
            try:
                val=float(m.group(1).replace(',',''))
                if abs(val-float(expected))>tol:
                    passed=False; reasons.append(f"numeric_mismatch:{val}!={expected}")
            except Exception as e:
                passed=False; reasons.append(f"numeric_parse_error:{e}")
    return passed, ';'.join(reasons) if reasons else 'pass'

def score_file(tasks_path, raw_path, out_path):
    tasks=load_tasks(tasks_path)
    rows=[]
    with open(raw_path, encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            r=json.loads(line)
            task=tasks[r['task_id']]
            passed, reason=deterministic_score(r.get('output',''), task)
            rows.append({**r, 'passed': int(passed), 'score_reason': reason, 'mode': task.mode, 'task_family': task.task_family})
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ['task_id','model','condition','passed','score_reason'])
        w.writeheader(); w.writerows(rows)
