#!/usr/bin/env python3
"""V9.4 frozen two-stage source expansion, matched 64 cross-encoder pairs per arm.
Per question: 32 shared initial pairs, 32 each of fast tail versus newly rescued.
Pretrained MS MARCO relevance ≠ factual entailment or necessary evidence proof.
"""
import argparse,collections,hashlib,json,pathlib,time
import numpy as np
from benchmark_v71_sag2_corpus import download,official_records,SAG2_AUTHOR,RELEASE
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger
from expansion_v92 import propose,rank_fuse
from sentence_transformers import CrossEncoder
SEED=20261028
MODEL='cross-encoder/ettin-reranker-17m-v1'
K=32
METHODS=('v71_fast','ce_fast64','ce_fast64_prot2','ce_expand64','ce_expand64_prot2')
def score(ce,q,docs,indices):
    if not indices:return {},0.
    pairs=[(q,docs[i]['title']+'\n'+docs[i].get('text','')[:1050]) for i in indices]
    t=time.perf_counter()
    scores=ce.predict(pairs,batch_size=24,show_progress_bar=False)
    ms=(time.perf_counter()-t)*1000
    return {i:float(v) for i,v in zip(indices,np.asarray(scores).reshape(-1))},ms
def ranked(indices,scores,fast,protect=0):
    unique=list(dict.fromkeys(indices))
    anchors=[i for i in fast[:protect] if i in unique]
    return anchors+sorted((i for i in unique if i not in anchors),key=lambda i:(-scores.get(i,-999.),i))
def fresh_candidates(q,docs,fast,bm,index,seed_indices,exclusions,K=32):
    original=list(dict.fromkeys(seed_indices+[i for i in fast[:2]]))
    candidates=propose(q,docs,original,index.index.idfs,kind='mixed',seed_n=4,k=8)
    hits=[];trace=[]
    for p in candidates:
        ranked_hits=[i for i,_ in index.index.search(p['term'],'bm25',40)]
        if not ranked_hits:continue
        hits.append(ranked_hits)
        trace.append({**p,'returned':len(ranked_hits)})
    fused=rank_fuse(fast,bm,hits,mode='fuse',strength=.4,protect=2,cutoff=250)
    choices=[];seen=set(exclusions)
    for i in fused+list(fast)+list(bm):
        if i not in seen:
            seen.add(i);choices.append(i)
            if len(choices)>=K:break
    return choices,trace
def bench(name,root,out,start,n,ce):
    sha=download(name,root);unique,docs,rows=official_records(name,root)
    assert len(rows)==1000 and len(docs)==SAG2_AUTHOR[name]['corpus']
    docs_text=list(unique)
    t=time.perf_counter();bm=SparseMethods(docs);bm_index=time.perf_counter()-t
    t=time.perf_counter();graph=EvidenceLedger(bm);graph_index=time.perf_counter()-t
    per=[];cost=collections.defaultdict(list)
    for tnum,row in enumerate(rows[start:start+n]):
        q=row['question'];gold=set(row['gold'])
        t=time.perf_counter();base_raw=bm.index.search(q,'bm25',100)
        b=[i for i,_ in base_raw] or list(range(min(len(docs),100)))
        fast,_=graph.search(q,b,mode='one-hop',bmraw=base_raw)
        cost['fast_ms'].append((time.perf_counter()-t)*1000)
        # Exactly first 32 same CE pairs for each arm.
        first=list(dict.fromkeys(fast+b))[:K]
        first_score,first_ms=score(ce,q,docs,first)
        seed=ranked(first,first_score,fast)[:3]
        # Fast comparator: next 32 passages, no expanded retrieval.
        fasttail=[i for i in list(dict.fromkeys(fast+b)) if i not in first][:K]
        fasttail_score,tail_ms=score(ce,q,docs,fasttail)
        # Source-anchored search seeded from first-stage *semantic* evidence.
        t=time.perf_counter()
        new,trace=fresh_candidates(q,docs,fast,b,bm,seed,set(first),K)
        expansion_ms=(time.perf_counter()-t)*1000
        new_score,new_ms=score(ce,q,docs,new)
        fc=first+fasttail
        ec=first+new
        allrank={'v71_fast':fast,
          'ce_fast64':ranked(fc,first_score|fasttail_score,fast),
          'ce_fast64_prot2':ranked(fc,first_score|fasttail_score,fast,protect=2),
          'ce_expand64':ranked(ec,first_score|new_score,fast),
          'ce_expand64_prot2':ranked(ec,first_score|new_score,fast,protect=2)}
        metrics={}
        for m,inds in allrank.items():
            retrieved=[docs_text[i] for i in inds[:10]]
            metrics[m]={'ae5':int(gold<=set(retrieved[:5])),
              'ae10':int(gold<=set(retrieved[:10])),
              'r5':len(gold&set(retrieved[:5]))/max(1,len(gold)),
              'r10':len(gold&set(retrieved[:10]))/max(1,len(gold))}
        goldids={i for i,s in enumerate(docs_text) if s in gold}
        per.append({'id':row['id'],'n_gold':len(gold),'metrics':metrics,
         'candidate_full':{'ce_fast64':int(goldids<=set(fc)),'ce_expand64':int(goldids<=set(ec))},
         'source_queries':trace,'seed_titles':[docs[i]['title'] for i in seed],
         'top5_titles':{m:[docs[i]['title'] for i in pred[:5]] for m,pred in allrank.items()}})
        for key,ms in [('initial_ce',first_ms),('fast_tail_ce',tail_ms),('expanded_tail_ce',new_ms),('source_expansion',expansion_ms)]:
            cost[key].append(ms)
        if (tnum+1)%25==0:print(name,start+tnum+1,'/',start+n,flush=True)
    summary={}
    for method in METHODS:
        summary[method]={field:round(float(np.mean([p['metrics'][method][field] for p in per])),6) for field in ('ae5','ae10','r5','r10')}
        delta=np.array([p['metrics'][method]['ae5']-p['metrics']['v71_fast']['ae5'] for p in per])
        rng=np.random.default_rng(SEED);bs=np.array([np.mean(delta[rng.integers(0,len(delta),len(delta))]) for _ in range(3000)])
        summary[method].update(wins=int(np.sum(delta>0)),losses=int(np.sum(delta<0)),ci95_pp=[round(100*x,2) for x in np.quantile(bs,[.025,.975])])
        if method.startswith('ce_'):summary[method]['full_gold_in_64_candidates']=sum(p['candidate_full']['ce_fast64' if 'fast64' in method else 'ce_expand64'] for p in per)
        summary[method]['by_required_sources']={str(k):{'n':sum(p['n_gold']==k for p in per),'ae5':sum(p['n_gold']==k and p['metrics'][method]['ae5'] for p in per)} for k in sorted(set(p['n_gold'] for p in per))}
    elapsed={k:{'mean_ms':round(float(np.mean(v)),2),'p95_ms':round(float(np.percentile(v,95)),2)} for k,v in cost.items()}
    elapsed['arm_inference_ms']={'fast64':round(float(np.mean(cost['initial_ce'])+np.mean(cost['fast_tail_ce'])),2),
                                  'expanded64':round(float(np.mean(cost['initial_ce'])+np.mean(cost['expanded_tail_ce'])),2)}
    out.mkdir(parents=True,exist_ok=True)
    data={'dataset':name,'range':[start,start+n],'documents':len(docs),'file_hashes':sha,
      'model':MODEL,'model_revision':getattr(ce.model.config,'_commit_hash',None) or 'unresolved','source_release':RELEASE,
      'results':summary,'cpu_cost':elapsed,
      'limitations':['Question-ID-disjoint but repeatedly used public benchmark','Equal 64 scoring pairs per method; benchmark shares initial scores, scores two tails physically','No independent SAG2 JEV execution','No answer reader or semantic evidence entailment','Methods frozen, no automatic result-driven hyperparameter changes']}
    (out/f'{name}_{start}_{start+n}_summary.json').write_text(json.dumps(data,indent=2))
    with (out/f'{name}_{start}_{start+n}_cases.jsonl').open('w') as f:
        for p in per:f.write(json.dumps(p,ensure_ascii=False)+'\n')
    print('RESULT',name,start,json.dumps(summary),flush=True)
    return data
def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['run','smoke'])
    p.add_argument('--datasets',nargs='+',default=['musique','2wikimultihopqa'])
    p.add_argument('--start',type=int,default=0);p.add_argument('--limit',type=int,default=50)
    p.add_argument('--data',type=pathlib.Path,default=pathlib.Path('data/sag2_official'))
    p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('results-v94'))
    a=p.parse_args()
    if a.command=='smoke':
        assert ranked([4,1],{4:2,1:4},[4,1],protect=1)==[4,1]
        print('V9.3 smoke PASS');return
    import torch
    torch.set_num_threads(2)
    t=time.perf_counter();ce=CrossEncoder(MODEL,max_length=224,device='cpu');print('model load s',round(time.perf_counter()-t,2),flush=True)
    for name in a.datasets:bench(name,a.data,a.out,a.start,a.limit,ce)
    print('V9.3 FROZEN RUN COMPLETE',flush=True)
if __name__=='__main__':main()
