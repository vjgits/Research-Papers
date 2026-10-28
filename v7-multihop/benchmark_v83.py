#!/usr/bin/env python3
"""One-shot V8.3 evaluation: question-disjoint public validation, no API.
V8.3 does not generate answers, and source-span validity is not entailment.
"""
import argparse,collections,hashlib,json,pathlib,time
import numpy as np
import benchmark_v8 as prior
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger,gold_2wiki,gold_musique
from benchmark_v7 import make_corpus,chain_scores
from benchmark_musique import pool_documents
from pger_v8_core import EvidenceMap
from pger_v83_core import TitleAnchors,select_guarded_chain

SEED=20261027
BOOT=5000

def ci(xs):
    arr=np.asarray(xs,dtype=float);rng=np.random.default_rng(SEED)
    boot=np.array([np.mean(arr[rng.integers(0,len(arr),len(arr))]) for _ in range(BOOT)])
    return {'delta_pp':round(100*float(arr.mean()),3),
            'ci95_pp':[round(100*float(x),3) for x in np.quantile(boot,[.025,.975])],
            'wins':int((arr>0).sum()),'losses':int((arr<0).sum())}

def evaluate(name,rows,docs,goldfn,out):
    print(name,'documents',len(docs),flush=True)
    bm=SparseMethods(docs); graph=EvidenceLedger(bm);em=EvidenceMap(docs);anchors=TitleAnchors(docs)
    costs=collections.defaultdict(list);per=[]
    for n,r in enumerate(rows):
        q=r['question'];t=time.perf_counter()
        bmraw=bm.index.search(q,'bm25',100)
        bmids=[i for i,_ in bmraw] or list(range(min(len(docs),100)))
        costs['bm25'].append((time.perf_counter()-t)*1000)
        t=time.perf_counter()
        fast,_=graph.search(q,bmids,mode='one-hop',bmraw=bmraw)
        costs['graph'].append((time.perf_counter()-t)*1000)
        t=time.perf_counter()
        guarded,meta=select_guarded_chain(q,fast,em,anchors)
        costs['guard'].append((time.perf_counter()-t)*1000)
        gold=goldfn(r);assert len(gold)>=2 and gold<=set(bm.ids)
        methods={}
        for label,ids in [('bm25',bmids),('v71_fast',fast),('v83_guarded',guarded)]:
            a,b=chain_scores(ids,gold,bm.ids)
            methods[label]={**a,**b,'ranked_top10':[bm.ids[i] for i in ids[:10]]}
        per.append({'id':str(r['id']),'question':q,'gold_count':len(gold),
            'gold_ids':sorted(gold),'activated':meta['activated'],
            'reason':meta['reason'],'anchor_ids':[bm.ids[i] for i in meta['anchors']],
            'source_evidence':meta.get('trail',[]),'methods':methods})
        if (n+1)%40==0:print(name,n+1,'/',len(rows),flush=True)
    summary={}
    for label in ['bm25','v71_fast','v83_guarded']:
        a=[r['methods'][label] for r in per]
        fast=[r['methods']['v71_fast'] for r in per]
        byhop={str(h):{'n':sum(r['gold_count']==h for r in per),
            'complete5':sum(r['methods'][label]['chain_at_5'] for r in per if r['gold_count']==h),
            'complete10':sum(r['methods'][label]['chain_at_10'] for r in per if r['gold_count']==h)}
            for h in sorted(set(r['gold_count'] for r in per))}
        summary[label]={'n':len(per),
           'chain_at5':round(float(np.mean([r['chain_at_5'] for r in a])),6),
           'chain_at10':round(float(np.mean([r['chain_at_10'] for r in a])),6),
           'gold_recall_at5':round(float(np.mean([r['evidence_recall_at_5'] for r in a])),6),
           'by_support':byhop,
           'paired_vs_fast_at5':ci([r['chain_at_5']-b['chain_at_5'] for r,b in zip(a,fast)]),
           'paired_vs_fast_at10':ci([r['chain_at_10']-b['chain_at_10'] for r,b in zip(a,fast)])}
        print(name,label,'@5',summary[label]['chain_at5'],'@10',summary[label]['chain_at10'],flush=True)
    result={'dataset':name,'protocol':{'new_question_ids':True,'public_validation_not_sealed':True,
        'pooled_document_universe':True,'no_gold_in_index_or_ranking':True,
        'no_paid_api':True,'no_answer_generation':True,
        'not_official_IRCoT_or_HippoRAG2':True,
        'v83_extra_BM25_calls':0,
        'qids_sha256':hashlib.sha256('\n'.join(sorted(r['id'] for r in per)).encode()).hexdigest()},
        'index_cost_seconds':{'bm25':bm.bm_index_seconds,'title_graph':graph.stats['graph_index_seconds'],
            'relation_index':em.claims.seconds,'reverse_map':em.build_seconds,
            'question_title_anchors':anchors.seconds},
        'post_index_latency_ms':{k:round(float(np.mean(v)),5) for k,v in costs.items()},
        'activation':{'n':sum(r['activated'] for r in per),
            'reasons':dict(collections.Counter(r['reason'] for r in per))},
        'methods':summary}
    out.mkdir(parents=True,exist_ok=True)
    (out/(name+'_summary.json')).write_text(json.dumps(result,indent=2))
    with (out/(name+'_per_question.jsonl')).open('w') as f:
        for r in per:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['run','smoke'])
    p.add_argument('--datasets',nargs='+',choices=['2wiki','musique'],default=['2wiki','musique'])
    p.add_argument('--data',type=pathlib.Path,default=pathlib.Path('data'))
    p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('results-v83'))
    args=p.parse_args()
    if args.command=='smoke':
        from pger_v8_core import EvidenceMap
        d=[{'_id':'a','title':'Film Alpha Example','text':'Film Alpha Example was directed by Director Carol Example.'},
           {'_id':'b','title':'Film Bravo Example','text':'Film Bravo Example was directed by Director David Example.'},
           {'_id':'c','title':'Director Carol Example','text':'Born in Canada.'},
           {'_id':'d','title':'Director David Example','text':'Born in France.'}]
        m=EvidenceMap(d);titles=TitleAnchors(d)
        r,info=select_guarded_chain('Which director was born earlier, Film Alpha Example or Film Bravo Example?',list(range(4)),m,titles)
        assert info['activated'] and len(r)==4
        print('V8.3 smoke pass');return
    prior.WIKI_START=960;prior.MUSIQUE_START=480
    reports=[]
    for name in args.datasets:
        rows,start=prior.load(name,args.data)
        docs=make_corpus(rows) if name=='2wiki' else pool_documents(rows)
        goldfn=gold_2wiki if name=='2wiki' else gold_musique
        reports.append(evaluate(name+'_fresh_'+str(start+1)+'_to_'+str(start+len(rows)),rows,docs,goldfn,args.out))
    (args.out/'summary.json').write_text(json.dumps({'reports':reports},indent=2))
    print('V8.3 BENCHMARK COMPLETE',flush=True)

if __name__=='__main__':main()
