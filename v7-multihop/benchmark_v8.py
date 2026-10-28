#!/usr/bin/env python3
"""PGER V7.3-V8.2: frozen cohort, retriever-only, matched candidate budgets.

Public validation question-disjoint from all V7.1/V7.2 development cohorts,
not a sealed independent benchmark. Causal novelty NOT claimed.
"""
import argparse,collections,hashlib,json,pathlib,time
import numpy as np
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger,gold_2wiki,gold_musique
from benchmark_v7 import DATA_URL, SEED as WIKI_SEED, make_corpus, chain_scores
from benchmark_musique import URL as MUSIQUE_URL, SEED as MUSIQUE_SEED, pool_documents
from pger_v8_core import EvidenceMap, build_candidate_rescue, rank_candidates, route_cost, missing_terms

SEED=20261027; BOOT=5000
# V7.1 first 480 Wiki, V7.2 next 240; V7.1 first 160 MuSiQue,
# V7.2 next 160. V8 final question-disjoint held-out slice in same public dev.
WIKI_START=720; WIKI_N=240; MUSIQUE_START=320; MUSIQUE_N=160


def load(name,folder):
    import pyarrow.parquet as pq,urllib.request
    folder.mkdir(parents=True,exist_ok=True)
    if name=='2wiki':
        p=folder/'2wiki_validation.parquet';url=DATA_URL;seed=WIKI_SEED
        st=WIKI_START;n=WIKI_N;cols=['id','question','type','supporting_facts','context']
    else:
        p=folder/'musique_validation.parquet';url=MUSIQUE_URL;seed=MUSIQUE_SEED
        st=MUSIQUE_START;n=MUSIQUE_N;cols=['id','question','paragraphs','answerable']
    if not p.exists():urllib.request.urlretrieve(url,p)
    a=pq.read_table(p,columns=cols).to_pylist()
    a.sort(key=lambda r:hashlib.sha256((seed+'|'+str(r['id'])).encode()).digest())
    rows=[]
    for r in a:
        if name=='2wiki':
            ctx=r.get('context') or {};titles=ctx.get('title') or []
            ps=ctx.get('sentences') or [];sf=r.get('supporting_facts') or {}
            gold={str(t).strip().casefold() for t in sf.get('title') or [] if t}
            ok=bool(titles and len(titles)==len(ps) and len(gold)>=2 and gold<={str(t).strip().casefold() for t in titles})
        else:
            pars=r.get('paragraphs') or [];g=[x for x in pars if x.get('is_supporting')]
            ok=bool(r.get('answerable') and 2<=len(g)<=4 and all(x.get('title') and x.get('paragraph_text') for x in pars))
        if ok:rows.append(r)
        if len(rows)>=st+n:break
    if len(rows)<st+n:raise AssertionError('Insufficient untouched questions: '+name)
    selected=rows[st:st+n]
    assert len({str(r['id']) for r in rows[:st] if r})==st
    assert not ({str(r['id']) for r in rows[:st]}&{str(r['id']) for r in selected})
    return selected,st


def lexical_budget(question,base,bm,engine,search,calls=2,limit=100):
    """Two lexical followup calls, same count and cap as candidate rescue.
    No source graph/semantic question rewriting; preserves fast base pool.
    """
    t=time.perf_counter();pool=set(base[:80])|set(bm[:80]);logs=[]
    missing=missing_terms(question,engine.doc_tokens,base)
    for k in range(calls):
        anchor=bm[k] if k<len(bm) else -1
        q=' '.join([engine.docs[anchor]['title']] + missing[:7]) if anchor>=0 else question
        hits=search(q,limit);pool.update(hits)
        logs.append({'type':'lexical_control','query':q,'anchor':engine.ids[anchor] if anchor>=0 else None,'returned':len(hits)})
    return pool,logs,(time.perf_counter()-t)*1000


def ci(values):
    v=np.asarray(values,dtype=float)
    rng=np.random.default_rng(SEED)
    if not len(v):return {}
    ix=rng.integers(len(v),size=(BOOT,len(v)))
    bs=v[ix].mean(axis=1)
    return {'delta_pp':round(100*float(v.mean()),3),
            'ci95_pp':[round(100*float(x),3) for x in np.quantile(bs,[.025,.975])],
            'wins':int((v>0).sum()),'losses':int((v<0).sum())}


def score(name,rows,docs,goldfn,output):
    t=time.perf_counter();system=SparseMethods(docs);graph=EvidenceLedger(system)
    em=EvidenceMap(docs)
    assert all(em.claims.valid(x) for x in em.claims.claims)
    index={'bm25_seconds':system.bm_index_seconds,'title_graph_seconds':graph.stats['graph_index_seconds'],
           'relation_index_seconds':em.claims.seconds,'reverse_map_seconds':em.build_seconds,
           'doc_count':len(docs),'source_edges':len(em.claims.claims),
           'directional_cue_edges':sum(c.asserted for c in em.claims.claims)}
    print(name,'indexed',len(docs),'in',round(time.perf_counter()-t,3),'s',flush=True)
    records=[]
    names=['bm25','v71_fast','v73_lexical_control','v73_rescue','v80_joint','v81_proofgap','v82_adaptive']
    for k,r in enumerate(rows):
        q=r['question'];qid=str(r['id'])
        t=time.perf_counter();bmraw=system.index.search(q,'bm25',100);bm=[i for i,_ in bmraw]
        if not bm:bm=list(range(min(100,len(docs))))
        bm_ms=(time.perf_counter()-t)*1000
        t=time.perf_counter();fast,_=graph.search(q,bm,mode='one-hop',bmraw=bmraw)
        fast_ms=(time.perf_counter()-t)*1000
        def search(query,limit):return [i for i,_ in system.index.search(query,'bm25',limit)]
        oldpool,oldlog,oldms=lexical_budget(q,fast,bm,em,search)
        pool,log,retrieval_ms=build_candidate_rescue(q,fast,bm,em,search)
        t=time.perf_counter();ctl,ctlmeta=rank_candidates(q,fast,bm,em,oldpool,'rescue');ctlms=(time.perf_counter()-t)*1000
        t=time.perf_counter();v73,v73meta=rank_candidates(q,fast,bm,em,pool,'rescue');v73ms=(time.perf_counter()-t)*1000
        t=time.perf_counter();v80,v80meta=rank_candidates(q,fast,bm,em,pool,'joint');v80ms=(time.perf_counter()-t)*1000
        t=time.perf_counter();v81,v81meta=rank_candidates(q,fast,bm,em,pool,'proofgap');v81ms=(time.perf_counter()-t)*1000
        route=route_cost(q,fast,em)
        v82=fast if route=='fast' else v81
        allrank={'bm25':bm,'v71_fast':fast,'v73_lexical_control':ctl,'v73_rescue':v73,
                 'v80_joint':v80,'v81_proofgap':v81,'v82_adaptive':v82}
        gold=goldfn(r)
        assert gold <= set(system.ids) and len(gold)>=2
        gold_idx={i for i,docid in enumerate(system.ids) if docid in gold}
        # Purely post-hoc audits; candidate lists never receive this information.
        diag={
           'old_candidate_gold_recall':len(oldpool&gold_idx)/len(gold_idx),
           'rescue_candidate_gold_recall':len(pool&gold_idx)/len(gold_idx),
           'missing_old_gold_ids':sorted(system.ids[i] for i in gold_idx-oldpool),
           'missing_rescue_gold_ids':sorted(system.ids[i] for i in gold_idx-pool),
           'rescue_candidate_n':len(pool),'control_candidate_n':len(oldpool)}
        costs={'bm':bm_ms,'graph':fast_ms,'lexical_candidates':oldms,
               'rescue_candidates':retrieval_ms,'rescue_rank':v73ms,'joint_rank':v80ms,'proofgap_rank':v81ms,
               'control_rank':ctlms}
        meta={'v80_joint':v80meta,'v81_proofgap':v81meta}
        for method,rank in allrank.items():
            comp,part=chain_scores(rank,gold,system.ids)
            records.append({'id':qid,'question':q,'method':method,'gold_count':len(gold),
                            'gold_ids':sorted(gold),**comp,**part,
                            'ranked_top10':[system.ids[i] for i in rank[:10]],
                            'candidate_audit':diag,'route':route,'timing_ms':costs,
                            'rescue_followups':log,'lexical_followups':oldlog,
                            'evidence_dependency':meta.get(method,{}).get('dependency_edges',[])})
        if (k+1)%40==0:print(name,k+1,'/',len(rows),flush=True)
    group=collections.defaultdict(dict)
    for r in records:group[r['id']][r['method']]=r
    summary={}
    for m in names:
        a=[g[m] for g in group.values()]
        mean=lambda key:round(float(np.mean([x[key] for x in a])),6)
        byhop={}
        for h in sorted({x['gold_count'] for x in a}):
            subset=[x for x in a if x['gold_count']==h]
            byhop[str(h)]={'n':len(subset),'complete5':sum(x['chain_at_5'] for x in subset),
                           'complete10':sum(x['chain_at_10'] for x in subset)}
        ref={'v73_rescue':'v73_lexical_control','v80_joint':'v73_rescue',
             'v81_proofgap':'v80_joint','v82_adaptive':'v71_fast'}.get(m,'v71_fast')
        intervals={f'vs_{ref}_at{z}':ci([x[f'chain_at_{z}']-g[ref][f'chain_at_{z}'] for x,g in ((g[m],g) for g in group.values())])
                   for z in (5,10)} if m!=ref else {}
        costpart={
           'bm':a[0]['timing_ms']['bm'],
           'graph':a[0]['timing_ms']['graph'],
        }
        costs=[r['timing_ms'] for r in a]
        mean_ms=lambda key:round(float(np.mean([x[key] for x in costs])),4)
        path_ms={'bm25':mean_ms('bm'),'v71_fast':mean_ms('bm')+mean_ms('graph'),
           'v73_lexical_control':mean_ms('bm')+mean_ms('graph')+mean_ms('lexical_candidates')+mean_ms('control_rank'),
           'v73_rescue':mean_ms('bm')+mean_ms('graph')+mean_ms('rescue_candidates')+mean_ms('rescue_rank'),
           'v80_joint':mean_ms('bm')+mean_ms('graph')+mean_ms('rescue_candidates')+mean_ms('joint_rank'),
           'v81_proofgap':mean_ms('bm')+mean_ms('graph')+mean_ms('rescue_candidates')+mean_ms('proofgap_rank'),
           'v82_adaptive':mean_ms('bm')+mean_ms('graph')+float(np.mean([
             0 if r['route']=='fast' else (r['timing_ms']['rescue_candidates']+r['timing_ms']['proofgap_rank']) for r in a]))}
        summary[m]={'n':len(a),'chain_at5':mean('chain_at_5'),'chain_at10':mean('chain_at_10'),
                    'evidence_recall_at5':mean('evidence_recall_at_5'),'by_support':byhop,
                    'estimated_path_ms':round(path_ms[m],4),**intervals}
        print(name,m,'@5',summary[m]['chain_at5'],'@10',summary[m]['chain_at10'],flush=True)
    audits=[g['v73_rescue']['candidate_audit'] for g in group.values()]
    meths=[g['v82_adaptive'] for g in group.values()]
    rsum={'dataset':name,'protocol':{'fresh_question_disjoint':True,'public_validation':True,
        'pooled_documents':True,'no_gold_during_retrieval':True,'no_reader_accuracy':True,
        'same_pool_v73_v80_v81':True,'both_candidate_generation_arms_two_bm25_calls':True,
        'no_api':True,'not_official_ircot_or_hipporag':True,
        'seed':SEED,'sha256_qids':hashlib.sha256('\n'.join(sorted(group)).encode()).hexdigest()},
        'index_cost':index,'methods':summary,'candidate_audit':{
          'old_recall_mean':round(float(np.mean([x['old_candidate_gold_recall'] for x in audits])),6),
          'rescue_recall_mean':round(float(np.mean([x['rescue_candidate_gold_recall'] for x in audits])),6),
          'paired_ci':ci([x['rescue_candidate_gold_recall']-x['old_candidate_gold_recall'] for x in audits]),
          'full_old_candidate_coverage':sum(x['old_candidate_gold_recall']==1. for x in audits),
          'full_rescue_candidate_coverage':sum(x['rescue_candidate_gold_recall']==1. for x in audits),
          'missed_rescue_source_occurrences':sum(len(x['missing_rescue_gold_ids']) for x in audits),
          'missed_old_source_occurrences':sum(len(x['missing_old_gold_ids']) for x in audits)},
        'adaptive_routing':{'cheap_path_n':sum(x['route']=='fast' for x in meths),
            'extra_search_n':sum(x['route']!='fast' for x in meths)},
        'limitations':['public validation sampled multiple times across versions; not independent sealed test',
              'retrieval-only; citation spans do not imply factual entailment',
              '5-8 hops require separate independently adjudicated benchmark',
              'matched search calls do not imply matched total CPU, report index cost',
              'no verified causal counterfactuals or answer abstention']}
    output.mkdir(parents=True,exist_ok=True)
    (output/(name+'_summary.json')).write_text(json.dumps(rsum,indent=2))
    with (output/(name+'_per_question.jsonl')).open('w') as f:
        for r in records:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    return rsum


def smoke():
    from pger_v8_core import EvidenceMap,rank_candidates,build_candidate_rescue
    d=[{'_id':'a','title':'Alpha Man','text':'Alpha Man was born in Beta Town.'},
       {'_id':'b','title':'Beta Town','text':'Beta Town is located in Gamma State.'},
       {'_id':'c','title':'Gamma State','text':'Gamma State is large.'}]
    m=EvidenceMap(d)
    assert all(m.claims.valid(c) for c in m.claims.claims)
    assert any(len(t)>=2 for t in m.chain(0,{0,1,2},max_edges=8))
    p,logs,_=build_candidate_rescue('Where was Alpha Man born?', [0],[0],m,lambda q,n:[1,2])
    assert len(logs)==2
    for mode in ('rescue','joint','proofgap'):
        out,_=rank_candidates('Where was Alpha Man born?',list(range(3)),list(range(3)),m,p,mode)
        assert len(out)==len(set(out))
    print('PGER V8 smoke pass')


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=('smoke','run'))
    p.add_argument('--datasets',nargs='+',choices=['2wiki','musique'],default=['2wiki','musique'])
    p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('results-v8'))
    p.add_argument('--data',type=pathlib.Path,default=pathlib.Path('data'))
    args=p.parse_args()
    if args.command=='smoke':smoke();return
    reports=[]
    for name in args.datasets:
        rows,start=load(name,args.data)
        docs=make_corpus(rows) if name=='2wiki' else pool_documents(rows)
        goldfn=gold_2wiki if name=='2wiki' else gold_musique
        reports.append(score(name+f'_fresh_{start+1}_to_{start+len(rows)}',rows,docs,goldfn,args.out))
    (args.out/'summary.json').write_text(json.dumps({'reports':reports},indent=2))
    print('PGER V8 BENCHMARK COMPLETE')

if __name__=='__main__':main()
