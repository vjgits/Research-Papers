#!/usr/bin/env python3
"""PGER V8.5: fixed-budget source-linked chain selection, honestly falsifiable.

New disjoint question IDs on REPEATED public validation families, pooled corpus.
Retrieval only, not a learned semantically entailed claim or answer correctness.
"""
import argparse,hashlib,json,pathlib,time,collections
import numpy as np
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger,gold_2wiki,gold_musique
from benchmark_v7 import make_corpus,chain_scores
from benchmark_musique import pool_documents
from benchmark_v8 import load as v8_load
import benchmark_v8 as prior
from pger_v8_core import EvidenceMap,build_candidate_rescue
from pger_v84_core import full_pool,directional_bonus_rank
from pger_v85_chain import deterministic_shortlist,ce_plain,connected_beam,early_gate

WIKI_START=1560; WIKI_N=120
MUSIQUE_START=960; MUSIQUE_N=160
BOOT=5000;SEED=20261027
CE_MODEL='cross-encoder/ms-marco-MiniLM-L6-v2'
DENSE_MODEL='sentence-transformers/all-MiniLM-L6-v2'
METHODS=['bm25','v71_fast','ce32','ce64','ce96','ce96_sourced','v85_chain96','v85_early_gate']

def boot(d):
    a=np.asarray(d,float);rng=np.random.default_rng(SEED)
    ix=rng.integers(0,len(a),size=(BOOT,len(a)))
    return dict(delta_pp=round(100*float(a.mean()),3),ci95_pp=[round(100*float(x),3) for x in np.quantile(a[ix].mean(axis=1),[.025,.975])],wins=int((a>0).sum()),losses=int((a<0).sum()))

def stat(a):
    return dict(mean_ms=round(float(np.mean(a)),3),p95_ms=round(float(np.percentile(a,95)),3)) if a else None

def evaluate(name,rows,docs,goldfn,dense,ce,out):
    from pger_v83_semantic import make_passage
    t=time.perf_counter();bm=SparseMethods(docs);graph=EvidenceLedger(bm);e=EvidenceMap(docs)
    indexes={'bm25_s':bm.bm_index_seconds,'graph_s':graph.stats['graph_index_seconds'],
             'source_span_index_s':e.claims.seconds,'source_reverse_index_s':e.build_seconds}
    t=time.perf_counter();emb=np.asarray(dense.encode([(d['title']+' '+d.get('text',''))[:1300] for d in docs],batch_size=64,normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=False),dtype=np.float32);indexes['dense_embed_s']=time.perf_counter()-t
    ids=bm.ids;out.mkdir(parents=True,exist_ok=True)
    print(name,'documents',len(docs),'dense_index_s',round(indexes['dense_embed_s'],2),flush=True)
    records=[];stages=collections.defaultdict(list)
    for n,row in enumerate(rows):
        q=row['question'];qid=str(row['id'])
        t=time.perf_counter();bmraw=bm.index.search(q,'bm25',100)
        bm_rank=[i for i,_ in bmraw] or list(range(min(100,len(docs))))
        base_ms=(time.perf_counter()-t)*1000
        t=time.perf_counter();fast,_=graph.search(q,bm_rank,mode='one-hop',bmraw=bmraw)
        graph_ms=(time.perf_counter()-t)*1000
        gate=early_gate(q,fast,docs)
        # Independent conditional path, executed BEFORE shared ablations.
        # Fast queries truly skip TF-IDF, dense, followups and CE.
        route_start=time.perf_counter()
        routed_ce_pairs=0
        if gate:
            routed=list(fast)
        else:
            route_tf=[i for i,_ in bm.index.search(q,'tfidf',120)]
            route_qe=np.asarray(dense.encode([q],normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=False)[0],dtype=np.float32)
            route_ds=emb@route_qe
            route_dense=sorted(range(len(docs)),key=lambda i:(-float(route_ds[i]),ids[i]))[:150]
            route_rescue,_,_=build_candidate_rescue(q,fast,bm_rank,e,
                 lambda qq,cap:[i for i,_ in bm.index.search(qq,'bm25',cap)])
            route_near=sorted(e.nearby(fast[:12]),key=lambda i:ids[i])
            route_wide,route_rrf=full_pool(fast,bm_rank,route_dense,route_tf,
                  sorted(route_rescue,key=lambda i:ids[i]),route_near,ids)
            route_pool=deterministic_shortlist(fast,route_wide,route_rrf,docs,q,96)
            route_raw=ce.predict([(q,make_passage(docs[i])) for i in route_pool],batch_size=32,show_progress_bar=False)
            route_map={i:float(v) for i,v in zip(route_pool,route_raw)}
            routed,_=connected_beam(fast,route_pool,route_map,ids,docs,e,q,beam=8,width=5)
            routed_ce_pairs=len(route_pool)
        actual_ms=(time.perf_counter()-route_start)*1000
        route_total_ms=base_ms+graph_ms+actual_ms
        # Shared dataset side-by-side ablations, including cases gated fast.
        t=time.perf_counter();tf=[i for i,_ in bm.index.search(q,'tfidf',120)];tf_ms=(time.perf_counter()-t)*1000
        t=time.perf_counter();qe=np.asarray(dense.encode([q],normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=False)[0],dtype=np.float32)
        dense_scores=emb@qe;dense_rank=sorted(range(len(docs)),key=lambda i:(-float(dense_scores[i]),ids[i]))[:150]
        dense_ms=(time.perf_counter()-t)*1000
        t=time.perf_counter();rescue,logs,_=build_candidate_rescue(q,fast,bm_rank,e,lambda qq,cap:[i for i,_ in bm.index.search(qq,'bm25',cap)])
        follow_ms=(time.perf_counter()-t)*1000
        near=sorted(e.nearby(fast[:12]),key=lambda i:ids[i])
        wide,rrf=full_pool(fast,bm_rank,dense_rank,tf,sorted(rescue,key=lambda i:ids[i]),near,ids)
        pools={k:deterministic_shortlist(fast,wide,rrf,docs,q,k) for k in (32,64,96)}
        assert pools[32]==pools[64][:32] and pools[64]==pools[96][:64]
        t=time.perf_counter()
        raw=ce.predict([(q,make_passage(docs[i])) for i in pools[96]],batch_size=32,show_progress_bar=False)
        scoremap={i:float(v) for i,v in zip(pools[96],raw)}
        ce_shared_ms=(time.perf_counter()-t)*1000
        ce32=ce_plain(fast,pools[32],scoremap,ids)
        ce64=ce_plain(fast,pools[64],scoremap,ids)
        ce96=ce_plain(fast,pools[96],scoremap,ids)
        sourced,traces=directional_bonus_rank(fast,pools[96],scoremap,e)
        t=time.perf_counter();chain,chain_traces=connected_beam(fast,pools[96],scoremap,ids,docs,e,q,beam=8,width=5)
        chain_rank_ms=(time.perf_counter()-t)*1000
        # Independent gated path never reuses the shared union CE scores.
        result={'bm25':bm_rank,'v71_fast':fast,'ce32':ce32,'ce64':ce64,'ce96':ce96,
                'ce96_sourced':sourced,'v85_chain96':chain,'v85_early_gate':routed}
        # Gold only read after all retrieval and ranking calls are complete.
        gold=goldfn(row)
        assert gold and gold<=set(ids),'Missing gold sources from constructed corpus'
        gold_i={i for i,z in enumerate(ids) if z in gold}
        met={}
        for method,ranking in result.items():
            c,p=chain_scores(ranking,gold,ids)
            met[method]={**c,**p,'ranked_top10':[ids[i] for i in ranking[:10]]}
        stage={'bm25':base_ms,'graph':graph_ms,'tfidf':tf_ms,'dense':dense_ms,
               'followups':follow_ms,'ce96_shared':ce_shared_ms,'chain_scoring':chain_rank_ms,
               'conditional_all_downstream':actual_ms,'conditional_total':route_total_ms}
        for k,v in stage.items():stages[k].append(v)
        records.append(dict(qid=qid,question=q,support_count=len(gold),gold_ids=sorted(gold),methods=met,
          gate='fast' if gate else 'ce',actual_ce_pairs=routed_ce_pairs,wide_pool=len(wide),
          shortlist_gold_full={str(k):gold_i<=set(pool) for k,pool in pools.items()},
          wide_gold_full=gold_i<=set(wide),fast32_gold_full=gold_i<=set(fast[:32]),
          missing_wide_gold_ids=[ids[i] for i in sorted(gold_i-set(wide))],
          evidence_trail=chain_traces[:15],sourced_trail=traces[:15],stage_ms=stage))
        if (n+1)%20==0:print(name,'completed',n+1,'/',len(rows),flush=True)
    summary={};by_support=sorted({r['support_count'] for r in records})
    for meth in METHODS:
        comp5=[r['methods'][meth]['chain_at_5'] for r in records];comp10=[r['methods'][meth]['chain_at_10'] for r in records]
        summary[meth]={'chain_at5':float(np.mean(comp5)),'chain_at10':float(np.mean(comp10)),
           'evidence_recall_at5':float(np.mean([r['methods'][meth]['evidence_recall_at_5'] for r in records])),
           'by_support_count':{str(h):{'n':sum(r['support_count']==h for r in records),
                 'complete_at5':sum(r['methods'][meth]['chain_at_5'] for r in records if r['support_count']==h),
                 'complete_at10':sum(r['methods'][meth]['chain_at_10'] for r in records if r['support_count']==h)} for h in by_support},
           'paired_vs_v71_top5':boot([r['methods'][meth]['chain_at_5']-r['methods']['v71_fast']['chain_at_5'] for r in records]),
           'paired_vs_ce96_top5':boot([r['methods'][meth]['chain_at_5']-r['methods']['ce96']['chain_at_5'] for r in records])}
        print(name,meth,'chain@5',round(summary[meth]['chain_at5'],6),'chain@10',round(summary[meth]['chain_at10'],6),flush=True)
    coverage={str(k):sum(r['shortlist_gold_full'][str(k)] for r in records) for k in (32,64,96)}
    result_summary=dict(dataset=name,n=len(records),docs=len(docs),protocol=dict(public_validation_reused_family=True,
         question_disjoint_from_previous_pger=True,pooled_context_docs=True,retrieval_only=True,
         no_automatic_answer_generation=True,no_semantic_entailment=True,no_real_5_8_hop_evaluation=True,
         no_gold_in_ranking=True,no_paid_api=True,same_96_scores_for_ce96_and_chain=True,
         model=CE_MODEL,dense_model=DENSE_MODEL,pin_model_revision=False),
       candidate_full_support_coverage={'fast32':sum(r['fast32_gold_full'] for r in records),
          'wide192':sum(r['wide_gold_full'] for r in records),**coverage},
       cost_stage_ms={k:stat(v) for k,v in stages.items()},index_seconds=indexes,
       routed_fast_n=sum(r['gate']=='fast' for r in records),routed_ce_n=sum(r['gate']=='ce' for r in records),
       conditional_ce_actual_pairs=sum(r['actual_ce_pairs'] for r in records),methods=summary,
       question_ids_sha256=hashlib.sha256('\n'.join(sorted(r['qid'] for r in records)).encode()).hexdigest())
    with (out/(name+'_per_question.jsonl')).open('w') as f:
        for r in records:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    (out/(name+'_summary.json')).write_text(json.dumps(result_summary,indent=2))
    return result_summary

def smoke():
    from pger_v85_chain import deterministic_shortlist
    docs=[{'_id':str(i),'title':f'Item {i}','text':''} for i in range(150)]
    ids=list(range(150));rrf={i:1/(i+41) for i in ids}
    p32=deterministic_shortlist(ids,ids,rrf,docs,'Which item?',32)
    p64=deterministic_shortlist(ids,ids,rrf,docs,'Which item?',64)
    assert p32==p64[:32]
    print('V8.5 smoke pass')

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['smoke','run'])
    p.add_argument('--datasets',nargs='+',default=['2wiki','musique'],choices=['2wiki','musique'])
    p.add_argument('--data',type=pathlib.Path,default=pathlib.Path('data'))
    p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('results-v85'))
    a=p.parse_args()
    if a.command=='smoke':smoke();return
    from sentence_transformers import CrossEncoder,SentenceTransformer
    import torch
    torch.set_num_threads(2)
    t=time.perf_counter();ce=CrossEncoder(CE_MODEL,device='cpu',max_length=192,activation_fn=torch.nn.Sigmoid())
    ce_load=time.perf_counter()-t
    t=time.perf_counter();dense=SentenceTransformer(DENSE_MODEL,device='cpu')
    dense_load=time.perf_counter()-t
    ce.predict([('warmup','passage')],batch_size=1)
    a.out.mkdir(exist_ok=True,parents=True)
    reports=[]
    for ds in a.datasets:
        prior.WIKI_START=WIKI_START;prior.WIKI_N=WIKI_N
        prior.MUSIQUE_START=MUSIQUE_START;prior.MUSIQUE_N=MUSIQUE_N
        rows,start=prior.load(ds,a.data)
        docs=make_corpus(rows) if ds=='2wiki' else pool_documents(rows)
        key=f'{ds}_fresh_{start+1}_to_{start+len(rows)}'
        reports.append(evaluate(key,rows,docs,gold_2wiki if ds=='2wiki' else gold_musique,dense,ce,a.out))
    (a.out/'summary.json').write_text(json.dumps({'reports':reports,'model_load_s':{'crossencoder':ce_load,'dense':dense_load},'locked_splits':True},indent=2))
    print('V8.5 FRESH BENCHMARK COMPLETE',flush=True)
if __name__=='__main__':main()