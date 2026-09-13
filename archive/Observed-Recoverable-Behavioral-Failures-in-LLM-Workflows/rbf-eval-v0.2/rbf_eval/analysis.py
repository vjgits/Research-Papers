import pandas as pd
from pathlib import Path
from .metrics import wilson

def summarize_csv(scores_path, out_path):
    df=pd.read_csv(scores_path)
    group_cols=[c for c in ['model','condition','mode','task_family'] if c in df.columns]
    rows=[]
    for keys,g in df.groupby(group_cols):
        if not isinstance(keys, tuple): keys=(keys,)
        d=dict(zip(group_cols, keys))
        n=len(g); k=int(g['passed'].sum())
        lo,hi=wilson(k,n)
        rows.append({**d,'n':n,'n_pass':k,'pass_rate':k/n if n else None,'wilson_low':lo,'wilson_high':hi})
    res=pd.DataFrame(rows)
    md=res.to_markdown(index=False)
    Path(out_path).write_text('# RBF-Eval Results Summary

'+md+'
', encoding='utf-8')
