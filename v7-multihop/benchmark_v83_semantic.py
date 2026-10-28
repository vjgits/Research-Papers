#!/usr/bin/env python3
"""PGER V8.3: blinded-per-question public-development cross-encoder ablations.

Fresh relative to versions through V8.3 guarded bridge (first 1200/640 usable
question IDs respectively), but still *public* validation with pooled documents.
No gold enters search, passage scores, gate or rerank. No trained PGER model,
answer generator, entailment judge, reviewer agent, or paid API.
"""
import argparse, collections, hashlib, json, pathlib, statistics, time
import numpy as np
import benchmark_v8 as prior
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger, gold_2wiki, gold_musique
from benchmark_v7 import make_corpus, chain_scores
from benchmark_musique import pool_documents
from pger_v8_core import EvidenceMap, build_candidate_rescue, rank_candidates
from pger_v83_semantic import fixed_pools, predict_union, rank_with_scores, cheap_gate

WIKI_START=1200; WIKI_N=240; MUSIQUE_START=640; MUSIQUE_N=160
MODEL="cross-encoder/ms-marco-MiniLM-L6-v2"
SEED=20261027; BOOT=5000; BATCH=32; MAX_TOKENS=192
METHODS=("bm25","v71_fast","lexical_rescue32","ce_fast32","ce_rescue32",
         "ce_protected32","ce_sourced32","ce_adaptive")

def bootstrap(diffs):
    a=np.asarray(diffs,dtype=float);rng=np.random.default_rng(SEED)
    if not len(a):return None
    draws=np.array([a[rng.integers(len(a),size=len(a))].mean() for _ in range(BOOT)])
    return {"delta_pp":round(100*float(a.mean()),3),
            "ci95_pp":[round(100*float(x),3) for x in np.quantile(draws,[.025,.975])],
            "wins":int((a>0).sum()),"losses":int((a<0).sum())}

def pct(samples):
    if not samples:return None
    return {"mean":round(float(np.mean(samples)),4),"median":round(float(np.median(samples)),4),
            "p95":round(float(np.percentile(samples,95)),4)}

def lexical_control(q,fast,bm,rescue_pool,em):
    """Same candidate set as CE rescue but *no pretrained model*."""
    qterms=__import__('pger_v72_core').terms(q)
    original={d:i for i,d in enumerate(fast)}
    bmrank={d:i for i,d in enumerate(bm)}
    preserve=list(dict.fromkeys(fast[:2]))
    candidates=[i for i in rescue_pool if i not in preserve]
    def val(i):
        title=em.title_tokens[i];body=em.doc_tokens[i]
        return (0.4*len(qterms&title)/max(1,len(title))
               +0.25*len(qterms&body)/max(1,len(qterms))
               +(0.3/(1+original[i]) if i in original else 0)
               +(0.05/(1+bmrank[i]) if i in bmrank else 0))
    candidates.sort(key=lambda i:(-val(i),em.ids[i]))
    return list(dict.fromkeys(preserve+candidates+fast+bm))[:100]

def run_set(name,rows,docs,goldfn,model,out):
    print(name,'indexing',len(docs),'documents',flush=True)
    system=SparseMethods(docs);graph=EvidenceLedger(system);em=EvidenceMap(docs)
    assert all(em.claims.valid(c) for c in em.claims.claims), 'Source span mismatch'
    times=collections.defaultdict(list);per=[]
    activation=0;trail_count=0;edge_valid_count=0;paircounts=[]
    for k,row in enumerate(rows):
        q=row['question'];qid=str(row['id']);timing={}
        t=time.perf_counter();bmraw=system.index.search(q,'bm25',100)
        bm=[i for i,_ in bmraw] or list(range(min(100,len(docs))))
        timing['bm25_ms']=(time.perf_counter()-t)*1000
        t=time.perf_counter();fast,_=graph.search(q,bm,mode='one-hop',bmraw=bmraw)
        timing['graph_ms']=(time.perf_counter()-t)*1000
        def search(query,n):return [i for i,_ in system.index.search(query,'bm25',n)]
        t=time.perf_counter();rescue,followups,internal_ms=build_candidate_rescue(q,fast,bm,em,search)
        timing['rescue_ms']=(time.perf_counter()-t)*1000
        assert len(followups)<=2
        t=time.perf_counter();fpool,rpool=fixed_pools(q,fast,bm,rescue,em)
        timing['pool_ms']=(time.perf_counter()-t)*1000
        # Exactly the same model scores from a SINGLE pass are reused for
        # all variants. Model cost is not falsely added to no-model baselines.
        t=time.perf_counter()
        scores,npairs=predict_union(q,fpool,rpool,docs,
            lambda pairs:model.predict(pairs,batch_size=BATCH,show_progress_bar=False))
        timing['ce_union_ms']=(time.perf_counter()-t)*1000
        paircounts.append(npairs)
        t=time.perf_counter();lex=lexical_control(q,fast,bm,rpool,em)
        timing['lexical_rank_ms']=(time.perf_counter()-t)*1000
        t=time.perf_counter();cef,_=rank_with_scores(fast,fpool,scores,em,'plain')
        timing['ce_fast_rank_ms']=(time.perf_counter()-t)*1000
        t=time.perf_counter();cer,_=rank_with_scores(fast,rpool,scores,em,'plain')
        timing['ce_rescue_rank_ms']=(time.perf_counter()-t)*1000
        t=time.perf_counter();protected,_=rank_with_scores(fast,rpool,scores,em,'protected')
        timing['ce_protected_rank_ms']=(time.perf_counter()-t)*1000
        t=time.perf_counter();sourced,trails=rank_with_scores(fast,rpool,scores,em,'sourced')
        timing['ce_sourced_rank_ms']=(time.perf_counter()-t)*1000
        gate=cheap_gate(q,fast,em)
        adaptive=fast if gate else sourced
        activation+=int(not gate);trail_count+=len(trails)
        for c in trails:
            matching=next((z for z in em.claims.claims if z.source_id==c['source_id']
                and z.target_id==c['target_id'] and z.start==c['start'] and z.end==c['end']),None)
            assert matching is not None and em.claims.valid(matching)
            edge_valid_count+=1
        ranks={'bm25':bm,'v71_fast':fast,'lexical_rescue32':lex,
               'ce_fast32':cef,'ce_rescue32':cer,'ce_protected32':protected,
               'ce_sourced32':sourced,'ce_adaptive':adaptive}
        gold=goldfn(row);assert len(gold)>=2 and gold<=set(system.ids)
        gold_idx={i for i,docid in enumerate(system.ids) if docid in gold}
        audits={'fast32_gold_fraction':len(gold_idx&set(fpool))/len(gold_idx),
                'rescue32_gold_fraction':len(gold_idx&set(rpool))/len(gold_idx),
                'fast32_full_gold':bool(gold_idx<=set(fpool)),
                'rescue32_full_gold':bool(gold_idx<=set(rpool)),
                'missing_fast32':[system.ids[i] for i in sorted(gold_idx-set(fpool))],
                'missing_rescue32':[system.ids[i] for i in sorted(gold_idx-set(rpool))]}
        metrics={}
        for method,order in ranks.items():
            c,p=chain_scores(order,gold,system.ids)
            metrics[method]={**c,**p,'top10':[system.ids[i] for i in order[:10]]}
        per.append({'id':qid,'question':q,'gold_supports':len(gold),'gold_ids':sorted(gold),
                    'candidate_audit':audits,'candidate_counts':{'fast':len(fpool),'rescue':len(rpool),'shared_model_pairs':npairs},
                    'followup_count':len(followups),'fast_gate':gate,
                    'source_edges':trails,'timing_ms':timing,'results':metrics})
        for key,v in timing.items():times[key].append(v)
        if (k+1)%40==0:print(name,k+1,'/',len(rows),flush=True)
    by={x['id']:x for x in per}
    summary={}
    for method in METHODS:
        a=[r['results'][method] for r in per];fb=[r['results']['v71_fast'] for r in per]
        group={str(h):{'n':sum(r['gold_supports']==h for r in per),
                        'complete5':sum(r['results'][method]['chain_at_5'] for r in per if r['gold_supports']==h),
                        'complete10':sum(r['results'][method]['chain_at_10'] for r in per if r['gold_supports']==h)}
               for h in sorted({r['gold_supports'] for r in per})}
        summary[method]={'chain_at5':round(float(np.mean([x['chain_at_5'] for x in a])),6),
                         'chain_at10':round(float(np.mean([x['chain_at_10'] for x in a])),6),
                         'recall_at5':round(float(np.mean([x['evidence_recall_at_5'] for x in a])),6),
                         'by_support_count':group,
                         'paired_vs_fast_at5':bootstrap([x['chain_at_5']-y['chain_at_5'] for x,y in zip(a,fb)]),
                         'paired_vs_fast_at10':bootstrap([x['chain_at_10']-y['chain_at_10'] for x,y in zip(a,fb)])}
        print(name,method,'chain@5',summary[method]['chain_at5'],'@10',summary[method]['chain_at10'],flush=True)
    log={'dataset':name,'protocol':{'public_validation_cohort':True,
          'question_ids_disjoint_from_prior_v7_to_v83_guard':True,
          'same_frozen_corpus_all_arms':True,'pooled_gold_present_by_construction':True,
          'no_gold_in_search_rank_or_gate':True,'retrieval_only':True,
          'model':MODEL,'max_tokens':MAX_TOKENS,'batch_size':BATCH,'candidate_cap':32,
          'model_pairs_shared_once_per_query':True,'no_paid_api':True,
          'no_official_ircot_hipporag':True,
          'no_final_answer_accuracy':True,
          'not_a_source_entailment_judge':True,
          'selected_qid_sha256':hashlib.sha256('\n'.join(sorted(by)).encode()).hexdigest()},
         'indexes_seconds':{'bm25':system.bm_index_seconds,'v71_graph':graph.stats['graph_index_seconds'],
              'claim_index':em.claims.seconds,'reverse_links':em.build_seconds},
         'query_stage_cpu_ms':{k:pct(v) for k,v in times.items()},
         'shared_model_pair_count':pct(paircounts),
         'hypothetical_gated_ce_calls':activation,'source_trails':trail_count,
         'provenance_verified_trails':edge_valid_count,
         'candidate_coverage':{'fast32_full':sum(r['candidate_audit']['fast32_full_gold'] for r in per),
           'rescue32_full':sum(r['candidate_audit']['rescue32_full_gold'] for r in per),
           'fast32_mean_gold_recall':round(float(np.mean([r['candidate_audit']['fast32_gold_fraction'] for r in per])),6),
           'rescue32_mean_gold_recall':round(float(np.mean([r['candidate_audit']['rescue32_gold_fraction'] for r in per])),6),
           'paired_recall_delta':bootstrap([r['candidate_audit']['rescue32_gold_fraction']-r['candidate_audit']['fast32_gold_fraction'] for r in per])},
         'methods':summary}
    out.mkdir(parents=True,exist_ok=True)
    (out/(name+'_summary.json')).write_text(json.dumps(log,indent=2))
    with (out/(name+'_per_question.jsonl')).open('w') as f:
        for r in per:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    return log

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['smoke','run'])
    p.add_argument('--datasets',nargs='+',choices=['2wiki','musique'],default=['2wiki','musique'])
    p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('results-v83-semantic'))
    p.add_argument('--data',type=pathlib.Path,default=pathlib.Path('data'))
    a=p.parse_args()
    if a.command=='smoke':
        from pger_v83_semantic import rank_with_scores
        ids=[{'_id':str(i),'title':'Title '+str(i),'text':'Text '+str(i)} for i in range(3)]
        em=EvidenceMap(ids)
        res,edges=rank_with_scores([0,1,2],[0,1,2],{0:.5,1:.8,2:.2},em,'protected')
        assert res[:2]==[0,1] and not edges
        print('V8.3 SEMANTIC SMOKE PASS');return
    import torch
    from sentence_transformers import CrossEncoder
    torch.set_num_threads(2)
    t=time.perf_counter()
    model=CrossEncoder(MODEL,device='cpu',max_length=MAX_TOKENS,
                       activation_fn=torch.nn.Sigmoid())
    model_load_seconds=time.perf_counter()-t
    warmt=time.perf_counter()
    model.predict([('Who wrote Alpha?','Alpha was written by Beta.')],batch_size=1)
    warm_seconds=time.perf_counter()-warmt
    prior.WIKI_START=WIKI_START;prior.MUSIQUE_START=MUSIQUE_START
    reports=[]
    for dataset in a.datasets:
        rows,start=prior.load(dataset,a.data)
        docs=make_corpus(rows) if dataset=='2wiki' else pool_documents(rows)
        goldfn=gold_2wiki if dataset=='2wiki' else gold_musique
        reports.append(run_set(f'{dataset}_fresh_{start+1}_to_{start+len(rows)}',rows,docs,goldfn,model,a.out))
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'summary.json').write_text(json.dumps({'model_load_seconds':model_load_seconds,
          'model_warmup_seconds':warm_seconds,'reports':reports},indent=2))
    print('PGER V8.3 SEMANTIC COMPLETE',flush=True)
if __name__=='__main__':main()