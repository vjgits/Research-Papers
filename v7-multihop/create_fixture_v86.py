#!/usr/bin/env python3
"""PGER V8.6: frozen typed-relation and NLI verification ablation.
Question-disjoint public validation only, pooled passages, retrieval not answers.
No paid APIs, no gold during search/rank, no official competing framework run.
"""
import argparse,collections,hashlib,json,pathlib,time
import numpy as np
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger,gold_2wiki,gold_musique
from benchmark_v7 import make_corpus,chain_scores
from benchmark_musique import pool_documents
import benchmark_v8 as prior
from pger_v8_core import EvidenceMap,build_candidate_rescue
from pger_v84_core import full_pool,directional_bonus_rank
from pger_v85_chain import deterministic_shortlist,ce_plain
from pger_v83_semantic import make_passage
from pger_v86_relation import candidate_claims,score_claims,rerank,lexical_scope,classify_nli,hypothesis,RELATIONS

WIKI_START=1680;WIKI_N=120
MUSIQUE_START=1120;MUSIQUE_N=160
CE_MODEL='cross-encoder/ms-marco-MiniLM-L6-v2'
DENSE_MODEL='sentence-transformers/all-MiniLM-L6-v2'
NLI_MODEL='cross-encoder/nli-MiniLM2-L6-H768'
NLI_REVISION='9aa22b250d25a10ac39ab4a6b2bc28213507cb0c'
BOOT=5000;SEED=20261027
METHODS=['bm25','v71_fast','ce96','v85_sourced','v86_typed','v86_typed_nli']

def stat(a):
    return {'mean_ms':round(float(np.mean(a)),3),'p95_ms':round(float(np.percentile(a,95)),3)} if a else None

def ci(values):
    x=np.asarray(values,dtype=float);rng=np.random.default_rng(SEED)
    samp=rng.integers(0,len(x),size=(BOOT,len(x)))
    return dict(delta_pp=round(float(x.mean()*100),3),ci95_pp=[round(float(t*100),3) for t in np.quantile(x[samp].mean(axis=1),[.025,.975])],wins=int((x>0).sum()),losses=int((x<0).sum()))

def fixture_check(nli,fixture_path):
    from types import SimpleNamespace
    cases=json.loads(fixture_path.read_text())['cases'];start=time.perf_counter()
    xs=np.asarray(nli.predict([(x['premise'],x['hypothesis']) for x in cases],batch_size=32,show_progress_bar=False))
    if xs.shape!=(len(cases),3):raise AssertionError(f'NLI labels shape mismatch: {xs.shape}')
    keys=('contradiction','entailment','neutral')
    pred=[];typed=[];joint=[];rows=[]
    for rec,vec in zip(cases,xs):
        yes,label,p=classify_nli(vec);pred.append(label)
        c=SimpleNamespace(quote=rec['premise'],subject=rec['subject'],object=rec['object'],predicate=rec['relation'],asserted=True)
        t=lexical_scope(c);typed.append(t);joint.append(bool(t and yes))
        rows.append(dict(id=rec['id'],origin=rec['origin'],relation=rec['relation'],expected=rec['expected'],predicted=label,typed=t,verified=bool(t and yes),p_entail=round(float(p[1]),6),p_contradict=round(float(p[0]),6),p_neutral=round(float(p[2]),6)))
    metrics={}
    for name,guess in [('nli_3way',pred)]:
        metrics[name]={'accuracy':round(float(np.mean([a==b for a,b in zip(guess,(x['expected'] for x in cases))])),6),
          'confusion':{gold:{label:sum(x['expected']==gold and v==label for x,v in zip(cases,guess)) for label in keys} for gold in keys}}
    gold=[x['expected']=='entailment' for x in cases]
    for name,guess in [('typed_scope',typed),('nli_entailment',[x=='entailment' for x in pred]),('typed_and_nli',joint)]:
        tp=sum(a and b for a,b in zip(gold,guess));fp=sum(not a and b for a,b in zip(gold,guess));fn=sum(a and not b for a,b in zip(gold,guess))
        metrics[name]={'tp':tp,'fp':fp,'fn':fn,'precision':round(tp/max(1,tp+fp),6),'recall':round(tp/max(1,tp+fn),6),'f1':round(2*tp/max(1,2*tp+fp+fn),6)}
    metrics['n']=len(cases);metrics['model_nli_seconds']=round(time.perf_counter()-start,3)
    return metrics,rows

def evaluate(name,rows,docs,goldfn,dense,ce,nli,out):
    print(name,'docs',len(docs),flush=True)
    bm=SparseMethods(docs);graph=EvidenceLedger(bm);e=EvidenceMap(docs)
    t=time.perf_counter();emb=np.asarray(dense.encode([(d['title']+' '+d.get('text',''))[:1300] for d in docs],batch_size=64,normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=False),dtype=np.float32)
    embed_s=time.perf_counter()-t;ids=bm.ids
    records=[];cost=collections.defaultdict(list)
    for k,r in enumerate(rows):
        q=r['question'];qid=str(r['id'])
        t=time.perf_counter();bmraw=bm.index.search(q,'bm25',100);bm_rank=[i for i,_ in bmraw] or list(range(min(100,len(docs))))
        bm_ms=(time.perf_counter()-t)*1000
        t=time.perf_counter();fast,_=graph.search(q,bm_rank,mode='one-hop',bmraw=bmraw);graph_ms=(time.perf_counter()-t)*1000
        t=time.perf_counter();tf=[i for i,_ in bm.index.search(q,'tfidf',120)]
        qe=np.asarray(dense.encode([q],normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=False)[0],dtype=np.float32)
        ds=emb@qe;den=sorted(range(len(docs)),key=lambda i:(-float(ds[i]),ids[i]))[:150]
        rescue,_,_=build_candidate_rescue(q,fast,bm_rank,e,lambda qq,cap:[i for i,_ in bm.index.search(qq,'bm25',cap)])
        near=sorted(e.nearby(fast[:12]),key=lambda i:ids[i])
        wide,rrf=full_pool(fast,bm_rank,den,tf,sorted(rescue,key=lambda i:ids[i]),near,ids)
        pool=deterministic_shortlist(fast,wide,rrf,docs,q,96)
        retrieval_ms=(time.perf_counter()-t)*1000
        t=time.perf_counter();raw=ce.predict([(q,make_passage(docs[i])) for i in pool],batch_size=32,show_progress_bar=False)
        ce_ms=(time.perf_counter()-t)*1000;scoremap={i:float(v) for i,v in zip(pool,raw)}
        basece=ce_plain(fast,pool,scoremap,ids)
        sourced,_=directional_bonus_rank(fast,pool,scoremap,e)
        claims=candidate_claims(e,pool,fast,q,cap=32)
        typed,typetrace=score_claims(claims,None,require_nli=False)
        t=time.perf_counter()
        verified,nlitrace=score_claims(claims,lambda pairs:np.asarray(nli.predict(pairs,batch_size=16,show_progress_bar=False)),require_nli=True)
        nli_ms=(time.perf_counter()-t)*1000
        ranks={'bm25':bm_rank,'v71_fast':fast,'ce96':basece,'v85_sourced':sourced,
          'v86_typed':rerank(fast,pool,scoremap,ids,typed),'v86_typed_nli':rerank(fast,pool,scoremap,ids,verified)}
        # GOLD ANNOTATIONS FIRST ACCESSED AFTER ALL RANKING IS DONE.
        gold=goldfn(r);assert gold and gold<=set(ids)
        metrics={}
        for method,rank in ranks.items():
            complete,part=chain_scores(rank,gold,ids)
            metrics[method]={**complete,**part,'top10_ids':[ids[i] for i in rank[:10]]}
        gold_idx={i for i,z in enumerate(ids) if z in gold}
        rec=dict(qid=qid,question=q,gold_count=len(gold),gold_ids=sorted(gold),scores=metrics,
           claim_candidate_count=len(claims),typed_positive_count=len(typed),nli_verified_count=len(verified),
           traces=nlitrace[:32],wide_full_gold=gold_idx<=set(wide),ce96_full_gold=gold_idx<=set(pool),
           ms={'bm25':bm_ms,'graph':graph_ms,'candidate_query':retrieval_ms,'ce96':ce_ms,'nli':nli_ms})
        records.append(rec)
        for key,val in rec['ms'].items():cost[key].append(val)
        if (k+1)%20==0:print(name,k+1,'/',len(rows),flush=True)
    summary={}
    for method in METHODS:
        vals=[r['scores'][method]['chain_at_5'] for r in records]
        summary[method]={'complete_at5':sum(vals),'chain_at5':round(float(np.mean(vals)),6),
         'chain_at10':round(float(np.mean([r['scores'][method]['chain_at_10'] for r in records])),6),
         'by_support':{str(h):{'n':sum(r['gold_count']==h for r in records),'complete_at5':sum(r['gold_count']==h and r['scores'][method]['chain_at_5'] for r in records)} for h in sorted(set(r['gold_count'] for r in records))},
         'vs_ce96_at5':ci([r['scores'][method]['chain_at_5']-r['scores']['ce96']['chain_at_5'] for r in records]),
         'vs_v85_sourced_at5':ci([r['scores'][method]['chain_at_5']-r['scores']['v85_sourced']['chain_at_5'] for r in records])}
        print(name,method,'chain@5',summary[method]['chain_at5'],flush=True)
    result=dict(dataset=name,n=len(records),documents=len(docs),split_sha256=hashlib.sha256('\n'.join(sorted(r['qid'] for r in records)).encode()).hexdigest(),
       index_seconds={'bm25':bm.bm_index_seconds,'title_graph':graph.stats['graph_index_seconds'],'relation':e.claims.seconds,'dense':embed_s},
       cost_ms={k:stat(v) for k,v in cost.items()},methods=summary,
       claim_audit={'candidate_total':sum(r['claim_candidate_count'] for r in records),'typed_total':sum(r['typed_positive_count'] for r in records),'nli_verified_total':sum(r['nli_verified_count'] for r in records)},
       candidate_full_gold={'wide192':sum(r['wide_full_gold'] for r in records),'ce96':sum(r['ce96_full_gold'] for r in records)},
       limitations=['same public validation families and pooled per-question passages','NLI model not a reliable factual truth oracle',
          'author-constructed relation fixture not independent human annotations','no answer generation or 5+ hop evaluation','NLI adds CPU and model overhead','paired intervals exploratory'])
    with (out/(name+'_per_question.jsonl')).open('w') as f:
        for item in records:f.write(json.dumps(item,ensure_ascii=False)+'\n')
    (out/(name+'_summary.json')).write_text(json.dumps(result,indent=2))
    return result

def smoke():
    from types import SimpleNamespace
    c=SimpleNamespace(subject='Kalank',object='Karan Johar',predicate='directed_by',asserted=True,
      quote='Kalank was directed by Abhishek Varman and produced by Karan Johar.')
    assert not lexical_scope(c)
    c.predicate='produced_by';assert lexical_scope(c)
    print('V8.6 smoke pass')

def main():
    a=argparse.ArgumentParser();a.add_argument('command',choices=('smoke','run'))
    a.add_argument('--datasets',nargs='+',choices=['2wiki','musique'],default=['2wiki','musique'])
    a.add_argument('--data',type=pathlib.Path,default=pathlib.Path('data'))
    a.add_argument('--out',type=pathlib.Path,default=pathlib.Path('results-v86'))
    args=a.parse_args()
    if args.command=='smoke':smoke();return
    from sentence_transformers import CrossEncoder,SentenceTransformer
    import torch
    torch.set_num_threads(2);args.out.mkdir(parents=True,exist_ok=True)
    t=time.perf_counter();ce=CrossEncoder(CE_MODEL,device='cpu',max_length=192,activation_fn=torch.nn.Sigmoid());load_ce=time.perf_counter()-t
    t=time.perf_counter();dense=SentenceTransformer(DENSE_MODEL,device='cpu');load_dense=time.perf_counter()-t
    t=time.perf_counter();nli=CrossEncoder(NLI_MODEL,device='cpu',max_length=192,revision=NLI_REVISION,activation_fn=torch.nn.Identity());load_nli=time.perf_counter()-t
    ce.predict([('warmup','passage')],batch_size=1)
    nli.predict([('A person is asleep','A person is sleeping')],batch_size=1)
    fm,fr=fixture_check(nli,pathlib.Path(__file__).parent/'contrastive_relation_cases_v86.json')
    (args.out/'contrastive_summary.json').write_text(json.dumps(fm,indent=2))
    with (args.out/'contrastive_per_case.jsonl').open('w') as f:
        for r in fr:f.write(json.dumps(r)+'\n')
    print('contrastive challenge',fm,flush=True)
    reports=[]
    for ds in args.datasets:
        prior.WIKI_START=WIKI_START;prior.WIKI_N=WIKI_N;prior.MUSIQUE_START=MUSIQUE_START;prior.MUSIQUE_N=MUSIQUE_N
        rows,start=prior.load(ds,args.data)
        docs=make_corpus(rows) if ds=='2wiki' else pool_documents(rows)
        key=f'{ds}_fresh_{start+1}_to_{start+len(rows)}'
        reports.append(evaluate(key,rows,docs,gold_2wiki if ds=='2wiki' else gold_musique,dense,ce,nli,args.out))
    (args.out/'summary.json').write_text(json.dumps({'reports':reports,'contrastive_fixture':fm,
       'model_load_s':{'ce':load_ce,'dense':load_dense,'nli':load_nli},'nli_revision':NLI_REVISION,
       'predeclared_threshold':.70,'nli_label_order':['contradiction','entailment','neutral'],
       'fixture_sha256':hashlib.sha256((pathlib.Path(__file__).parent/'contrastive_relation_cases_v86.json').read_bytes()).hexdigest(),
       'not_independent_final_test':True},indent=2))
    print('V8.6 COMPLETE',flush=True)
if __name__=='__main__':main()