#!/usr/bin/env python3
"""PGER V9.1: honest real-QA *lexical gap proxy* test with two BM25 calls.
No answer generation, verified semantic counterfactuals, official competitors or SOTA.
No gold labels available to retrieval / follow-up planning / ranking.
"""
import argparse, collections, hashlib, json, pathlib, time
import numpy as np
from benchmark_v8 import load as oldload
import benchmark_v8 as prior
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger,gold_2wiki,gold_musique
from benchmark_v7 import make_corpus,chain_scores
from benchmark_musique import pool_documents
from pger_v91_core import query_once,valid_source,gap_slots

SEED=20261028; BOOT=4000; WIKI_START=1800; WIKI_N=120; MUSIQUE_START=1280; MUSIQUE_N=160
POLICIES=('fast','original2','frontier2','gap2')

def paired_ci(vals):
    a=np.asarray(vals,dtype=float);rng=np.random.default_rng(SEED)
    if not len(a):return None
    ix=rng.integers(0,len(a),size=(BOOT,len(a)))
    return {'delta_pp':round(float(100*a.mean()),3),
      'ci95_pp':[round(float(x),3) for x in 100*np.quantile(a[ix].mean(axis=1),[.025,.975])],
      'wins':int((a>0).sum()),'losses':int((a<0).sum())}

def summarize(records,name,indexcost):
    result={'dataset':name,'n_questions':len(records),'n_documents':indexcost['documents'],
            'index_build_seconds':indexcost,'methods':{},'limitations':[
            'question-id-disjoint but publicly inspected benchmark families',
            'source documents pooled from question contexts with annotated sources present',
            'all multi-hop tasks; no independent single-hop routing benchmark',
            'gap prioritization is lexical proxy not verified decision-changing proof',
            'no final answer reader or genuine 5+hop test',
            'matching BM25 call budgets do not imply identical CPU time',
            'no reproduced HippoRAG2, IRCoT, S2G or AdaKG head-to-head']}
    for p in POLICIES:
        a=[r['scores'][p]['chain_at_5'] for r in records]
        b=[r['scores'][p]['chain_at_10'] for r in records]
        costs=[r['cpu_ms'][p] for r in records]
        meta=[r['meta'][p]['extra_queries'] for r in records]
        by={}
        for n in sorted(set(r['gold_count'] for r in records)):
            arr=[r for r in records if r['gold_count']==n]
            by[str(n)]={'n':len(arr),'complete5':sum(r['scores'][p]['chain_at_5'] for r in arr),
                        'complete10':sum(r['scores'][p]['chain_at_10'] for r in arr)}
        result['methods'][p]={'chain_at5':round(float(np.mean(a)),6),'chain_at10':round(float(np.mean(b)),6),
            'mean_ms_including_common_bm25_graph':round(float(np.mean(costs)),4),
            'p95_ms':round(float(np.percentile(costs,95)),4),'extra_bm25_calls_mean':float(np.mean(meta)),
            'support_breakdown':by,
            'paired_vs_fast_5':paired_ci([r['scores'][p]['chain_at_5']-r['scores']['fast']['chain_at_5'] for r in records]),
            'paired_vs_frontier_5':paired_ci([r['scores'][p]['chain_at_5']-r['scores']['frontier2']['chain_at_5'] for r in records]),
            'paired_vs_frontier_10':paired_ci([r['scores'][p]['chain_at_10']-r['scores']['frontier2']['chain_at_10'] for r in records])}
    result['data_question_id_sha256']=hashlib.sha256('\n'.join(sorted(r['id'] for r in records)).encode()).hexdigest()
    return result

def evaluate(name,rows,docs,out,goldfn):
    t=time.perf_counter();engine=SparseMethods(docs);bmindex_s=time.perf_counter()-t
    t=time.perf_counter();graph=EvidenceLedger(engine);graphindex_s=time.perf_counter()-t
    indexcost={'documents':len(docs),'bm25_and_vector_index_s':round(bmindex_s,4),'graph_index_s':round(graphindex_s,4)}
    records=[];out.mkdir(parents=True,exist_ok=True)
    for k,row in enumerate(rows):
        q=str(row['question']);qid=str(row['id'])
        t=time.perf_counter();bmraw=engine.index.search(q,'bm25',100)
        bm=[i for i,_ in bmraw] or list(range(min(100,len(docs))))
        bm_ms=(time.perf_counter()-t)*1000
        t=time.perf_counter();fast,_=graph.search(q,bm,mode='one-hop',bmraw=bmraw)
        graph_ms=(time.perf_counter()-t)*1000
        ranks={'fast':fast};meta={'fast':{'extra_queries':0,'actions':[],'extra_ms':0}}
        costs={'fast':bm_ms+graph_ms}
        def search(qq,cap):return [i for i,_ in engine.index.search(qq,'bm25',cap)]
        for policy,label in [('original','original2'),('frontier','frontier2'),('gap','gap2')]:
            found,info=query_once(q,bmraw,fast,docs,search,policy=policy,calls=2,cap=60)
            assert info['extra_queries']==2
            assert all(a['witness'] is None or valid_source(a['witness'],docs) for a in info['actions'])
            assert len(found)==len(set(found))
            ranks[label]=found;meta[label]=info;costs[label]=bm_ms+graph_ms+info['extra_ms']
        # Gold labels exclusively used from here onward for metrics.
        gold=goldfn(row)
        assert len(gold)>=2 and gold<=set(engine.ids)
        scored={}
        for p,rank in ranks.items():
            c,r=chain_scores(rank,gold,engine.ids)
            scored[p]={**c,**r,'top10':[engine.ids[i] for i in rank[:10]],'top100_gold_count':sum(engine.ids[i] in gold for i in rank[:100])}
        rec={'id':qid,'question':q,'gold_count':len(gold),'gold_ids':sorted(gold),
             'question_relation_slots':gap_slots(q),'scores':scored,'meta':meta,'cpu_ms':costs}
        records.append(rec)
        if (k+1)%40==0:print('V9.1',name,k+1,'/',len(rows),flush=True)
    with (out/f'{name}_per_question.jsonl').open('w') as f:
        for r in records:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    s=summarize(records,name,indexcost)
    (out/f'{name}_summary.json').write_text(json.dumps(s,indent=2))
    for meth,m in s['methods'].items():
        print(name,meth,'@5',m['chain_at5'],'@10',m['chain_at10'],'mean_ms',m['mean_ms_including_common_bm25_graph'],flush=True)
    return s

def smoke():
    from pger_v91_core import plan_queries
    docs=[{'_id':'a','title':'Alpha Person','text':'Alpha Person was born in Beta City.'},
          {'_id':'b','title':'Beta City','text':'Beta City is in Gamma Country.'}]
    for p in ('gap','frontier','original'):
        plan=plan_queries('Where was Alpha Person born?',list(range(2)),docs,p)
        assert len(plan)==2 and all(a['witness'] is None or valid_source(a['witness'],docs) for a in plan)
    print('V9.1 smoke PASS')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['smoke','run'])
    parser.add_argument('--out',type=pathlib.Path,default=pathlib.Path('results-v91'))
    parser.add_argument('--data',type=pathlib.Path,default=pathlib.Path('data'))
    parser.add_argument('--datasets',nargs='+',choices=('2wiki','musique'),default=['2wiki','musique'])
    args=parser.parse_args()
    if args.command=='smoke':smoke();return
    prior.WIKI_START=WIKI_START;prior.WIKI_N=WIKI_N
    prior.MUSIQUE_START=MUSIQUE_START;prior.MUSIQUE_N=MUSIQUE_N
    reports=[]
    for name in args.datasets:
        rows,st=oldload(name,args.data)
        docs=make_corpus(rows) if name=='2wiki' else pool_documents(rows)
        reports.append(evaluate(name,rows,docs,args.out,gold_2wiki if name=='2wiki' else gold_musique))
    (args.out/'summary.json').write_text(json.dumps({'reports':reports},indent=2))
    print('PGER V9.1 REAL-QA GAP PROXY COMPLETE',flush=True)
if __name__=='__main__':main()