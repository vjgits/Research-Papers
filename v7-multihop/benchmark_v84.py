#!/usr/bin/env python3
"""PGER V8.4 controlled pilot: dense candidate rescue + 64-pair CE + actual gated CPU.
All existing primitives are standard. Not an end-to-end answer system or SOTA test.
MoreHopQA reports prior-context evidence only, NEVER added last-hop answer accuracy.
"""
import argparse, collections, hashlib, json, pathlib, time, urllib.request
import numpy as np
import benchmark_v8 as prior
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger,gold_2wiki,gold_musique
from benchmark_v7 import make_corpus,chain_scores
from benchmark_musique import pool_documents
from pger_v8_core import EvidenceMap, build_candidate_rescue
from pger_v83_semantic import fixed_pools, predict_union, rank_with_scores
from pger_v84_core import full_pool,short_rerank_pool,sorted_ce,directional_bonus_rank,corpus_gate,context_rows

WIKI_START=1440; WIKI_N=120
MUSIQUE_START=800; MUSIQUE_N=160
MOREHOP_N=80
MOREHOP_URL='https://huggingface.co/datasets/alabnii/morehopqa/resolve/main/verified/test-00000-of-00001.parquet'
CE_MODEL='cross-encoder/ms-marco-MiniLM-L6-v2'
DENSE_MODEL='sentence-transformers/all-MiniLM-L6-v2'
BOOTS=3000;SEED=20261027;BATCH=32;TOKEN_LIMIT=192
METHODS=['bm25','v71_fast','v83_protected32','v84_ce64','v84_ce64_sourced','v84_actual_route']

def bootstrap(diffs):
    a=np.asarray(diffs,dtype=np.float32)
    if not len(a):return None
    rng=np.random.default_rng(SEED)
    ix=rng.integers(0,len(a),size=(BOOTS,len(a)))
    return {'delta_pp':round(100*float(a.mean()),3),
       'ci95_pp':[round(100*float(x),3) for x in np.quantile(a[ix].mean(axis=1),[.025,.975])],
       'wins':int((a>0).sum()),'losses':int((a<0).sum())}

def stat(vals):
    if not vals:return None
    return {'mean':round(float(np.mean(vals)),3),'p95':round(float(np.percentile(vals,95)),3)}

def load_morehop(folder):
    import pyarrow.parquet as pq
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/'morehop_verified_test.parquet'
    if not path.exists():urllib.request.urlretrieve(MOREHOP_URL,path)
    rows=pq.read_table(path).to_pylist()
    # The official dataset provides no canonical per-row ID. Sort stable
    # hashes of question + previous question (not answers, support labels).
    rows.sort(key=lambda r:hashlib.sha256((str(r.get('question'))+'|'+str(r.get('previous_question'))).encode()).digest())
    chosen=[]
    for raw in rows:
        ps,gold=context_rows(raw)
        titles={t.strip().casefold() for t,_ in ps}
        if len(ps)>=2 and len(gold)>=1 and gold<=titles:
            chosen.append({'id':hashlib.sha256((str(raw.get('question'))+'|'+str(raw.get('previous_question'))).encode()).hexdigest()[:24],
                 'question':str(raw['question']),'previous_question':str(raw['previous_question']),
                 'context':{'title':[x[0] for x in ps],'sentences':[[x[1]] for x in ps]},
                 'support_titles':sorted(gold),'added_reasoning_type':str(raw.get('reasoning_type')),
                 'added_hops':raw.get('no_of_hops')})
            if len(chosen)>=MOREHOP_N:break
    if not chosen:raise ValueError('No MoreHopQA rows with annotated supplied context titles')
    return chosen

def gold_morehop(r):return set(r['support_titles'])

def encode_index(docs,encoder):
    t=time.perf_counter()
    embs=encoder.encode([(d['title']+' '+d.get('text',''))[:1300] for d in docs],
         batch_size=64,normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=False)
    return np.asarray(embs,dtype=np.float32),time.perf_counter()-t

def measure_set(name,rows,docs,goldfn,ce,dense_encoder,out,mode):
    system=SparseMethods(docs); graph=EvidenceLedger(system); evidence=EvidenceMap(docs)
    dense_emb,emb_s=encode_index(docs,dense_encoder)
    assert all(evidence.claims.valid(c) for c in evidence.claims.claims)
    title_density=sum(len(v) for v in graph.adj)/max(1,len(docs))
    allrows=[]; query_cost=collections.defaultdict(list);gate_counter=collections.Counter()
    print(name,'documents',len(docs),'graph_density',round(title_density,3),'dense_index_s',round(emb_s,2),flush=True)
    for k,r in enumerate(rows):
        q=r['question'];qid=str(r['id']);t0=time.perf_counter()
        bmraw=system.index.search(q,'bm25',100)
        bm=[j for j,_ in bmraw] or list(range(min(100,len(docs))))
        base_ms=1000*(time.perf_counter()-t0)
        t=time.perf_counter();fast,_=graph.search(q,bm,mode='one-hop',bmraw=bmraw)
        fast_ms=1000*(time.perf_counter()-t)
        t=time.perf_counter()
        tf=[j for j,_ in system.index.search(q,'tfidf',100)]
        tfms=1000*(time.perf_counter()-t)
        t=time.perf_counter();qe=dense_encoder.encode([q],normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=False)[0]
        scores_dense=dense_emb@np.asarray(qe,dtype=np.float32)
        dense_rank=sorted(range(len(docs)),key=lambda i:(-float(scores_dense[i]),system.ids[i]))[:120]
        dense_ms=1000*(time.perf_counter()-t)
        def bmsearch(qq,n):return [j for j,_ in system.index.search(qq,'bm25',n)]
        t=time.perf_counter();rescue,fol,internal=build_candidate_rescue(q,fast,bm,evidence,bmsearch)
        follow_ms=1000*(time.perf_counter()-t)
        near=sorted(evidence.nearby(fast[:12]),key=lambda i:system.ids[i])
        wide,rrf=full_pool(fast,bm,dense_rank,tf,sorted(rescue,key=lambda i:system.ids[i]),near,system.ids)
        f32,r32=fixed_pools(q,fast,bm,rescue,evidence)
        pool64=short_rerank_pool(fast,wide,rrf,docs,q)
        assert len(set(pool64))==len(pool64) and len(pool64)<=64
        # Matched candidate recall is computed *after* retrieval from gold only.
        # The rerank arms share one CE score batch over their union.
        t=time.perf_counter();scoremap,num=predict_union(q,r32,pool64,docs,lambda pairs:ce.predict(pairs,batch_size=BATCH,show_progress_bar=False))
        cems=1000*(time.perf_counter()-t)
        v83,_=rank_with_scores(fast,r32,scoremap,evidence,'protected')
        v84=sorted_ce(fast,pool64,scoremap,system.ids)
        sourced,traces=directional_bonus_rank(fast,pool64,scoremap,evidence)
        gate=corpus_gate(q,fast,evidence,title_density);gate_counter[gate]+=1
        # ACTUAL gated inference: if route fast, NO cross-encoder call in this
        # separate timer; if route CE, independent CE.predict on exact pool64.
        gt=time.perf_counter()
        if gate=='fast':
            routed=list(fast);actual_ce_calls=0
        else:
            pairs=[(q,str(docs[i]['title'])+'\n'+str(docs[i].get('text') or '')[:1000]) for i in pool64]
            # Deployed arm never uses the full-union score cache.
            ss=ce.predict(pairs,batch_size=BATCH,show_progress_bar=False)
            deployed={i:float(sc) for i,sc in zip(pool64,ss)}
            routed,_=directional_bonus_rank(fast,pool64,deployed,evidence)
            actual_ce_calls=len(pairs)
        actual_ms=1000*(time.perf_counter()-gt)
        results={'bm25':bm,'v71_fast':fast,'v83_protected32':v83,
                 'v84_ce64':v84,'v84_ce64_sourced':sourced,'v84_actual_route':routed}
        gold=goldfn(r)
        assert gold and gold<=set(system.ids),'Gold source not in constructed pool'
        gidx={i for i,ident in enumerate(system.ids) if ident in gold}
        audit={'fast32_complete':gidx<=set(f32),'v83_rescue32_complete':gidx<=set(r32),
               'v84_pool64_complete':gidx<=set(pool64),'v84_wide192_complete':gidx<=set(wide),
               'fast32_gold_recall':len(gidx&set(f32))/len(gidx),
               'pool64_gold_recall':len(gidx&set(pool64))/len(gidx),
               'wide192_gold_recall':len(gidx&set(wide))/len(gidx),
               'missing_gold_wide192':[system.ids[i] for i in sorted(gidx-set(wide))]}
        scored={}
        for method,ranking in results.items():
            c,p=chain_scores(ranking,gold,system.ids)
            scored[method]={**c,**p,'top10':[system.ids[j] for j in ranking[:10]]}
        cost={'bm25_ms':base_ms,'graph_ms':fast_ms,'tfidf_ms':tfms,'dense_query_ms':dense_ms,
              'followups_ms':follow_ms,'ce_shared_union_ms':cems,'actual_gated_ce_ms':actual_ms}
        for metric,val in cost.items():query_cost[metric].append(val)
        allrows.append({'id':qid,'question':q,'support_count':len(gold),'gold_ids':sorted(gold),
            'score_unit':'supplied_preceding_context_only' if mode=='morehop' else 'complete_annotated_source_set',
            'morehop_added_hops':r.get('added_hops') if mode=='morehop' else None,
            'candidate_audit':audit,'pairs_shared':num,'pairs_gated':actual_ce_calls,
            'route':gate,'followup_count':len(fol),'timing_ms':cost,'sourced_trails':traces,'methods':scored})
        if (k+1)%20==0:print(name,k+1,'/',len(rows),flush=True)
    out.mkdir(parents=True,exist_ok=True)
    with (out/(name+'_per_question.jsonl')).open('w') as f:
        for r in allrows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    methods={}
    for m in METHODS:
        a=[r['methods'][m] for r in allrows];b=[r['methods']['v71_fast'] for r in allrows]
        methods[m]={'chain_at5':round(float(np.mean([x['chain_at_5'] for x in a])),6),
              'chain_at10':round(float(np.mean([x['chain_at_10'] for x in a])),6),
              'recall_at5':round(float(np.mean([x['evidence_recall_at_5'] for x in a])),6),
              'paired_vs_v71_at5':bootstrap([x['chain_at_5']-y['chain_at_5'] for x,y in zip(a,b)]),
              'paired_vs_v71_at10':bootstrap([x['chain_at_10']-y['chain_at_10'] for x,y in zip(a,b)]),
              'by_source_count':{str(n):{'n':sum(r['support_count']==n for r in allrows),
                    'complete5':sum(r['methods'][m]['chain_at_5'] for r in allrows if r['support_count']==n),
                    'complete10':sum(r['methods'][m]['chain_at_10'] for r in allrows if r['support_count']==n)}
                      for n in sorted({r['support_count'] for r in allrows})}}
        print(name,m,'@5',methods[m]['chain_at5'],'@10',methods[m]['chain_at10'],flush=True)
    coverage={label:{'complete':sum(r['candidate_audit'][key] for r in allrows),
                         'mean_gold_recall':round(float(np.mean([r['candidate_audit'][recall] for r in allrows])),6)}
         for label,key,recall in [('fast32','fast32_complete','fast32_gold_recall'),
          ('v84_pool64','v84_pool64_complete','pool64_gold_recall'),
          ('wide192','v84_wide192_complete','wide192_gold_recall')]}
    summary={'dataset':name,'n':len(rows),'corpus_documents':len(docs),'evaluation_type':('previous_context_only_not_extended_question_answer' if mode=='morehop' else 'complete_annotated_supporting_sources'),
       'dataset_public_validation_or_verified_test':True,'not_sealed_or_external_final_eval':True,
       'no_gold_in_index_candidate_gate_or_ranking':True,'source_provenance_offsets_not_fact_entailment':True,
       'no_final_answer_generator':True,'no_8hop_recovery_claim':True,
       'model':CE_MODEL,'dense_model':DENSE_MODEL,
       'index_seconds':{'bm25':system.bm_index_seconds,'graph':graph.stats['graph_index_seconds'],
          'relation':evidence.claims.seconds,'dense_embeddings':emb_s},
       'graph_density':title_density,'candidate_coverage':coverage,
       'gate_counts':dict(gate_counter),
       'query_stage_times_ms':{k:stat(v) for k,v in query_cost.items()},
       'methods':methods,'sha256_ids':hashlib.sha256('\n'.join(sorted(r['id'] for r in allrows)).encode()).hexdigest()}
    (out/(name+'_summary.json')).write_text(json.dumps(summary,indent=2))
    return summary

def smoke():
    from pger_v84_core import full_pool,context_rows
    docs=[{'_id':str(i),'title':'A'+str(i),'text':'B'} for i in range(5)]
    pool,_=full_pool([0,1],[0,1],[2,3],[4],[],[],[d['_id'] for d in docs]); assert set(pool)==set(range(5))
    assert context_rows({'context':{'title':['A'],'paragraphs':[['hello']]},'question_decomposition':{'paragraph_support_title':['A']}})[1]=={'a'}
    print('V8.4 SMOKE PASS')

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=('smoke','run'))
    p.add_argument('--datasets',nargs='+',default=['2wiki','musique','morehop'],choices=['2wiki','musique','morehop'])
    p.add_argument('--data',type=pathlib.Path,default=pathlib.Path('data'))
    p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('results-v84'))
    args=p.parse_args()
    if args.command=='smoke':smoke();return
    import torch
    from sentence_transformers import CrossEncoder,SentenceTransformer
    torch.set_num_threads(2);t=time.perf_counter()
    ce=CrossEncoder(CE_MODEL,device='cpu',max_length=TOKEN_LIMIT,activation_fn=torch.nn.Sigmoid())
    ce_load=time.perf_counter()-t
    t=time.perf_counter();dense=SentenceTransformer(DENSE_MODEL,device='cpu')
    dense_load=time.perf_counter()-t
    ce.predict([('a question','a passage')],batch_size=1)
    outputs=[]
    for ds in args.datasets:
        if ds=='morehop':
            rows=load_morehop(args.data); docs=make_corpus(rows)
            goldfn=gold_morehop;key='morehop_verified_context'
        else:
            prior.WIKI_START=WIKI_START;prior.MUSIQUE_START=MUSIQUE_START
            prior.WIKI_N=WIKI_N;prior.MUSIQUE_N=MUSIQUE_N
            rows,start=prior.load(ds,args.data)
            docs=make_corpus(rows) if ds=='2wiki' else pool_documents(rows)
            goldfn=gold_2wiki if ds=='2wiki' else gold_musique
            key=f'{ds}_fresh_{start+1}_to_{start+len(rows)}'
        outputs.append(measure_set(key,rows,docs,goldfn,ce,dense,args.out,ds))
    (args.out/'summary.json').write_text(json.dumps({'report':outputs,'models_load_seconds':{
        'cross_encoder':ce_load,'dense_encoder':dense_load},'no_paid_apis':True,
        'research_only':True},indent=2))
    print('PGER V8.4 BENCHMARK COMPLETE',flush=True)
if __name__=='__main__':main()