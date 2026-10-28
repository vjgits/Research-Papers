#!/usr/bin/env python3
"""PGER V8.7 natural DocRED entity-pair conditioned relation & evidence diagnostics.
NEVER label as open-world extraction, verified negative classification or 4-hop QA.
"""
import argparse, collections, hashlib, json, pathlib, time, urllib.request
import numpy as np
from pger_v87_core import TEMPLATES,normalize_doc,evidence_windows,bridge_windows,evaluate_windows

DATASET='thunlp/docred'
NLI='cross-encoder/nli-MiniLM2-L6-H768'
NLI_REV='9aa22b250d25a10ac39ab4a6b2bc28213507cb0c'
SEED=20261027

def get_parquet(outdir):
    outdir.mkdir(parents=True,exist_ok=True)
    manifest_url='https://datasets-server.huggingface.co/parquet?dataset=thunlp%2Fdocred'
    with urllib.request.urlopen(urllib.request.Request(manifest_url,headers={'User-Agent':'PGER-research-v87/1.0'}),timeout=90) as r:
        manifest=json.load(r)
    files=[a for a in manifest.get('parquet_files',[]) if a.get('split')=='validation']
    if not files:raise RuntimeError('Official DocRED validation parquet not found; do not substitute train/test silently')
    import pyarrow.parquet as pq
    rows=[];sha=[]
    for idx,entry in enumerate(files):
        p=outdir/f'original_docred_validation_{idx}.parquet'
        if not p.exists():urllib.request.urlretrieve(entry['url'],p)
        data=p.read_bytes();sha.append(dict(file=p.name,sha256=hashlib.sha256(data).hexdigest(),source_url=entry['url']))
        rows.extend(pq.read_table(p).to_pylist())
    if len(rows)<500:raise RuntimeError('DocRED too few validation rows; check source')
    return rows,sha

def choose_samples(raw,n=100,docs_cap=95):
    """External gold annotation used ONLY to choose positive gold-labeled entity pairs.
    Correct relation and evidence IDs never used in scoring or selecting model premises.
    """
    seen={};eligible=[]
    order=sorted(enumerate(raw),key=lambda t:hashlib.sha256((str(SEED)+'|'+str(t[1].get('title'))+'|'+str(t[0])).encode()).digest())
    doc_count=0
    for orig,r in order:
        d=normalize_doc(r)
        if not d['sents'] or not d['vertexSet']:continue
        groups=collections.defaultdict(lambda:{'gold':set(),'evidence':set()})
        for label in d['labels']:
            rel=str(label.get('r'))
            if rel not in TEMPLATES:continue
            try:h=int(label['h']);t=int(label['t'])
            except (TypeError,ValueError):continue
            if h==t or h<0 or t<0 or h>=len(d['vertexSet']) or t>=len(d['vertexSet']):continue
            if not d['vertexSet'][h] or not d['vertexSet'][t]:continue
            pair=groups[h,t];pair['gold'].add(rel)
            pair['evidence'].update(int(e) for e in label.get('evidence',[]) if e is not None and 0<=int(e)<len(d['sents']))
        if not groups:continue
        doc_count+=1
        for h,t in sorted(groups,key=lambda z:(z[0],z[1]))[:2]:
            x=groups[h,t]
            eligible.append(dict(id=f'{orig}:{h}:{t}',doc_index=orig,doc_title=d['title'],h=h,t=t,
                                 gold=sorted(x['gold']),evidence=sorted(x['evidence']),doc=d))
            if len(eligible)>=n:break
        if len(eligible)>=n or doc_count>=docs_cap:break
    if len(eligible)<min(n,30):raise RuntimeError('Insufficient supported relations in DocRED validation (not substituting synthetic)')
    return eligible

def paired_bootstrap(records,a,b,key='correct',rep=4000):
    grouped=collections.defaultdict(list)
    for r in records:grouped[r['doc_index']].append(int(r['methods'][a][key])-int(r['methods'][b][key]))
    docs=list(grouped);rng=np.random.default_rng(SEED)
    samples=[]
    for i in range(rep):
        ix=rng.integers(0,len(docs),len(docs))
        values=[v for j in ix for v in grouped[docs[j]]]
        samples.append(100*sum(values)/len(values))
    diffs=[int(r['methods'][a][key])-int(r['methods'][b][key]) for r in records]
    return {'delta_pp':round(100*np.mean(diffs),3),'doc_cluster_bootstrap_ci95_pp':[round(float(t),3) for t in np.quantile(samples,[.025,.975])],
            'wins':sum(v>0 for v in diffs),'losses':sum(v<0 for v in diffs),'n_doc_clusters':len(docs)}

def run(out,limit=100,cap=4):
    out.mkdir(parents=True,exist_ok=True)
    rows,sources=get_parquet(out/'cache')
    items=choose_samples(rows,n=limit)
    import torch
    from sentence_transformers import CrossEncoder
    torch.set_num_threads(2)
    t=time.perf_counter();nli=CrossEncoder(NLI,device='cpu',revision=NLI_REV,max_length=256)
    model_s=time.perf_counter()-t
    records=[];timings=[]
    for i,ex in enumerate(items):
        doc=ex['doc'];h,t=ex['h'],ex['t']
        windows={'single':evidence_windows(doc,h,t,cap),'bridge':bridge_windows(doc,h,t,cap)}
        runs={}
        for name,ws in windows.items():
            begin=time.perf_counter()
            # True model inference; same 16 x 4 calls per arm, no paid services.
            def infer(pairs):return np.asarray(nli.predict(pairs,batch_size=32,show_progress_bar=False))
            res=evaluate_windows(doc,h,t,infer,ws)
            duration_ms=1000*(time.perf_counter()-begin)
            res['nli_ms']=duration_ms
            runs[name]=res
        gold=set(ex['gold']);egold=set(ex['evidence']);met={}
        for mode,x in runs.items():
            for method,label in [('lexical',x['lexical']),('nli_ungated',x['ungated']),('nli_abstain',x['predicted'])]:
                key=mode+'_'+method
                cited=set(x['window']['sentence_ids'])
                met[key]={'correct':bool(label in gold),'answered':bool(label),
                          'predicted':label,'citation_support_any':bool(egold&cited) if egold else None,
                          'citation_support_all':bool(egold<=cited) if egold else None}
        records.append(dict(id=ex['id'],doc_index=ex['doc_index'],doc_title=ex['doc_title'],gold=ex['gold'],
                            gold_evidence=ex['evidence'],given_entities=[h,t],methods=met,
                            single_candidates=runs['single']['candidate_sentence_ids'],
                            bridge_candidates=runs['bridge']['candidate_sentence_ids'],
                            selected_citations={m:runs[m]['window']['sentence_ids'] for m in runs},
                            candidates_have_any_gold={m:bool(set(runs[m]['candidate_sentence_ids'])&egold) if egold else None for m in runs},
                            candidates_have_all_gold={m:bool(egold<=set(runs[m]['candidate_sentence_ids'])) if egold else None for m in runs},
                            nli_ms={m:round(runs[m]['nli_ms'],2) for m in runs},
                            inference_pairs={m:runs[m]['pair_count'] for m in runs}))
        if (i+1)%20==0:print('DOCRED',i+1,'/',len(items),flush=True)
    names=list(records[0]['methods'])
    metrics={}
    for name in names:
        z=[r['methods'][name] for r in records];answered=[v for v in z if v['answered']]
        correct=sum(v['correct'] for v in z)
        cite=[v for v in z if v['correct'] and v['citation_support_any'] is not None]
        metrics[name]={'n':len(z),'correct':correct,'correct_rate':round(correct/len(z),6),
                       'coverage':round(len(answered)/len(z),6),
                       'precision_on_annotated_positive_pairs':round(sum(v['correct'] for v in answered)/len(answered),6) if answered else None,
                       'correct_with_any_gold_evidence':sum(v['citation_support_any'] for v in cite),
                       'correct_with_all_gold_evidence':sum(v['citation_support_all'] for v in cite),
                       'correct_with_gold_evidence_n':len(cite)}
    diffs={
      'bridge_nli_vs_single_nli':paired_bootstrap(records,'bridge_nli_ungated','single_nli_ungated'),
      'single_nli_vs_lexical':paired_bootstrap(records,'single_nli_ungated','single_lexical'),
      'bridge_nli_vs_lexical':paired_bootstrap(records,'bridge_nli_ungated','bridge_lexical'),
    }
    summary={'protocol':{'dataset':'thunlp/docred','split':'validation','human_positive_annotations':True,
            'gold_entity_pair_provided_to_extractor':True,'zero_shot_fixed_ontology':sorted(TEMPLATES),
            'model':NLI,'model_revision':NLI_REV,'no_gold_relation_evidence_used_for_scoring':True,
            'negative_labels_not_assumed':True,'relation_precision_open_world_not_measured':True,
            'not_full_qa_or_multi_hop_answer_correctness':True,'unseen_dataset_family_relative_to_prior_PGER_QA':True,
            'not_sealed_test':True,'nli_model_cost_per_arm':len(TEMPLATES)*cap,'sample_seed':SEED,
            'dataset_files_sha256':sources,'question_pair_selection_uses_gold_to_define_positive_cohort':True},
        'n':len(records),'n_doc_clusters':len({x['doc_index'] for x in records}), 'methods':metrics,
        'paired':diffs,'model_load_s':round(model_s,3),
        'mean_nli_ms':{k:round(float(np.mean([r['nli_ms'][k] for r in records])),2) for k in ('single','bridge')},
        'p95_nli_ms':{k:round(float(np.quantile([r['nli_ms'][k] for r in records],.95)),2) for k in ('single','bridge')},
        'multi_sentence_gold_evidence_n':sum(len(r['gold_evidence'])>1 for r in records),
        'annotated_evidence_available_n':sum(bool(r['gold_evidence']) for r in records),
        'sample_pairs_sha256':hashlib.sha256('\n'.join(x['id'] for x in records).encode()).hexdigest()}
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    with (out/'per_relation_pair.jsonl').open('w') as f:
        for r in records:f.write(json.dumps(r)+'\n')
    print('PGER V8.7 DOCRED POSITIVE-PAIR DIAGNOSTIC COMPLETE',flush=True)
    print(json.dumps({'methods':metrics,'paired':diffs},indent=2),flush=True)
    return summary

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['smoke','run']);p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('results-v87'))
    p.add_argument('--pairs',type=int,default=100);p.add_argument('--windows',type=int,default=4)
    a=p.parse_args()
    if a.command=='smoke':
        from pger_v87_core import tokenize
        assert len(TEMPLATES)==16 and 'directed' in tokenize('was directed by')
        print('V8.7 smoke pass');return
    if a.pairs!=100 or a.windows!=4:raise ValueError('Frozen main benchmark uses exactly --pairs 100 and --windows 4; create new named experiment for variations')
    run(a.out,a.pairs,a.windows)
if __name__=='__main__':main()