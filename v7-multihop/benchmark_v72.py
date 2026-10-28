#!/usr/bin/env python3
"""PGER V7.2: locked fresh QUESTION cohort, retrieval-only, CPU and no API.

Independent of prior 240+240 2Wiki / 160 MuSiQue query IDs, but still public
validation samples and pooled passages. NOT a sealed blind benchmark.

Compares BM25, V7.1 BM25 + indexed title-graph (fast), a matched no-memory
surface-relation controller, and the same controller retaining provenance-
checked relation/dependency state. Candidate generation is common to both
V7.2 controller arms. Gold is accessed only after retrieval for diagnostics.
"""
import argparse, collections, hashlib, json, pathlib, statistics, time
import numpy as np
from benchmark_v71 import EvidenceLedger, phrases, gold_2wiki, gold_musique
from benchmark_v7 import DATA_URL, SEED as WIKI_SEED, make_corpus, chain_scores
from benchmark_musique import URL as MUSIQUE_URL, SEED as MUSIQUE_SEED, pool_documents
from benchmark_v6 import Retriever
from pger_v72_core import ClaimIndex, make_shared_candidates, rank_with_claims, should_expand

OLD_WIKI_STOP=480
OLD_MUSIQUE_STOP=160
SAMPLE_WIKI=240
SAMPLE_MUSIQUE=160
BOOTSTRAPS=5000

class SparseMethods:
    def __init__(self,docs):
        self.docs=docs
        s=time.perf_counter()
        self.index=Retriever(docs)
        self.bm_index_seconds=time.perf_counter()-s
        self.ids=self.index.ids

def load_fresh_wiki(folder):
    import pyarrow.parquet as pq, urllib.request
    folder.mkdir(parents=True,exist_ok=True)
    p=folder/'2wiki_validation.parquet'
    if not p.exists():urllib.request.urlretrieve(DATA_URL,p)
    rows=pq.read_table(p,columns=['id','question','type','supporting_facts','context']).to_pylist()
    rows.sort(key=lambda r:hashlib.sha256((WIKI_SEED+'|'+str(r['id'])).encode()).digest())
    valid=[]
    for r in rows:
        ctx=r.get('context') or {}; titles=ctx.get('title') or []
        paras=ctx.get('sentences') or [];sf=r.get('supporting_facts') or {}
        gold={str(t).strip().casefold() for t in sf.get('title') or [] if t}
        if titles and len(titles)==len(paras) and len(gold)>=2 and gold<={str(t).strip().casefold() for t in titles}:
            valid.append(r)
            if len(valid)>=OLD_WIKI_STOP+SAMPLE_WIKI:break
    assert len(valid)>=OLD_WIKI_STOP+SAMPLE_WIKI, 'Insufficient unused 2Wiki valid validation questions'
    assert not ({str(r['id']) for r in valid[:OLD_WIKI_STOP]} & {str(r['id']) for r in valid[OLD_WIKI_STOP:]}), 'Leaked 2Wiki question'
    return valid[OLD_WIKI_STOP:OLD_WIKI_STOP+SAMPLE_WIKI]

def load_fresh_musique(folder):
    import pyarrow.parquet as pq,urllib.request
    folder.mkdir(parents=True,exist_ok=True)
    p=folder/'musique_validation.parquet'
    if not p.exists():urllib.request.urlretrieve(MUSIQUE_URL,p)
    rows=pq.read_table(p,columns=['id','question','paragraphs','answerable']).to_pylist()
    rows.sort(key=lambda r:hashlib.sha256((MUSIQUE_SEED+'|'+str(r['id'])).encode()).digest())
    valid=[]
    for r in rows:
        if not r.get('answerable'):continue
        pars=r.get('paragraphs') or []
        g=[q for q in pars if q.get('is_supporting')]
        if 2<=len(g)<=4 and all(q.get('title') and q.get('paragraph_text') for q in pars):
            valid.append(r)
            if len(valid)>=OLD_MUSIQUE_STOP+SAMPLE_MUSIQUE:break
    assert len(valid)>=OLD_MUSIQUE_STOP+SAMPLE_MUSIQUE, 'Insufficient unused MuSiQue valid validation questions'
    assert not ({str(r['id']) for r in valid[:OLD_MUSIQUE_STOP]} & {str(r['id']) for r in valid[OLD_MUSIQUE_STOP:]}),'Leaked MuSiQue question'
    return valid[OLD_MUSIQUE_STOP:OLD_MUSIQUE_STOP+SAMPLE_MUSIQUE]

def confidence(diffs,seed=20261027):
    if not diffs:return {'delta_pp':None,'ci95_pp':None}
    vals=np.asarray(diffs,dtype=float);rng=np.random.default_rng(seed)
    # bootstrap the paired per-question differences, NOT independent arms
    boot=np.empty(BOOTSTRAPS)
    for b in range(BOOTSTRAPS):
        boot[b]=np.mean(vals[rng.integers(0,len(vals),len(vals))])
    return {'delta_pp':round(100*float(np.mean(vals)),3),
            'ci95_pp':[round(100*float(x),3) for x in np.quantile(boot,[0.025,0.975])],
            'paired_wins':int(sum(vals>0)),'paired_losses':int(sum(vals<0))}

def audit_one(gold,indices,graph,claims,considered,base,docs):
    """Gold-only *post-hoc* diagnostic. Not available to rankers."""
    missing=gold-{docs[i]['_id'] for i in indices[:5]}
    in_considered={docs[i]['_id'] for i in considered}
    inbound_graph={docs[j]['_id'] for i in base[:5] for j in graph.adj[i]}
    inbound_rel={docs[c.target]['_id'] for i in base[:5] for c in claims.links.get(i,[])}
    records=[]
    for docid in sorted(missing):
        if docid in in_considered:
            reason='considered_but_not_top5'
        elif docid in inbound_rel:
            reason='relation_edge_candidate_not_considered'
        elif docid in inbound_graph:
            reason='title_edge_candidate_not_considered'
        else:reason='outside_shared_candidate_pool_and_seed_links'
        records.append({'doc_id':docid,'reason':reason,
            'source_title':next((str(d['title']) for d in docs if d['_id']==docid),None)})
    return records

def evaluate(name,rows,docs,goldfn,out):
    print(name,'indexing',len(docs),'documents',flush=True)
    s=SparseMethods(docs)
    graph=EvidenceLedger(s)
    claims=ClaimIndex(docs)
    assert all(claims.valid(c) for c in claims.claims),'Source provenance invariant failed'
    print(name,'graph and claim indexes ready',flush=True)
    per=[]
    for k,row in enumerate(rows):
        q=row['question']; qid=str(row['id'])
        t=time.perf_counter()
        bmraw=s.index.search(q,'bm25',100)
        bm=[i for i,_ in bmraw]
        bm_ms=1000*(time.perf_counter()-t)
        if not bm:
            # Explicit deterministic zero-match fallback, as a full BM25 ranking does.
            bm=list(range(min(100,len(docs))))
        # EXACT V7.1 fast graph baseline source (no dense index or model)
        t=time.perf_counter()
        fast,faststats=graph.search(q,bm,mode='one-hop',bmraw=bmraw)
        graph_ms=1000*(time.perf_counter()-t)
        t=time.perf_counter()
        def bm_search(query,limit):return [i for i,_ in s.index.search(query,'bm25',limit)]
        considered,search_log=make_shared_candidates(q,docs,fast,bm,claims,bm_search)
        retrieval_ms=1000*(time.perf_counter()-t)
        if should_expand(q,docs,bm):
            t=time.perf_counter()
            reset,resetmeta=rank_with_claims(q,docs,fast,bm,claims,considered,retain=False)
            reset_ms=1000*(time.perf_counter()-t)
            t=time.perf_counter()
            ledger,ledgermeta=rank_with_claims(q,docs,fast,bm,claims,considered,retain=True)
            ledger_ms=1000*(time.perf_counter()-t)
        else:
            reset=list(fast);ledger=list(fast)
            resetmeta=ledgermeta={'paths':0,'deepest':0,'sourced_links':0}
            reset_ms=ledger_ms=0.
        gold=goldfn(row)
        assert len(gold)>=2 and gold<=set(s.ids)
        rankings={'bm25':bm,'bm25_graph_v71':fast,'v72_no_memory':reset,'v72_relation_ledger':ledger}
        for method,rank in rankings.items():
            complete,partial=chain_scores(rank,gold,s.ids)
            a=audit_one(gold,rank,graph,claims,considered,fast,docs)
            per.append({'id':qid,'question':q,'method':method,'gold_count':len(gold),
              **complete,**partial,'gold_ids':sorted(gold),
              'ranked_top10':[s.ids[i] for i in rank[:10]],
              'considered_n':len(considered),'missing_at5':a,
              'gate_expanded':should_expand(q,docs,bm),
              'followup_queries':search_log,
              'latency_ms':{'bm25':bm_ms,'indexed_graph':graph_ms,
                 'shared_followup':retrieval_ms,'arm_scoring':
                  {'v72_no_memory':reset_ms,'v72_relation_ledger':ledger_ms}.get(method,0.)},
              'walk':{'v72_no_memory':resetmeta,'v72_relation_ledger':ledgermeta}.get(method,{})})
        if (k+1)%40==0:print(name,k+1,'/',len(rows),flush=True)
    assert len(per)==4*len(rows),'Some fresh queries had no BM25 match; adjust protocol before making comparison'
    by=collections.defaultdict(dict)
    for r in per:by[r['id']][r['method']]=r
    methods={}
    for method in ('bm25','bm25_graph_v71','v72_no_memory','v72_relation_ledger'):
        a=[q[method] for q in by.values()]
        mean=lambda field:round(float(np.mean([x[field] for x in a])),6)
        groups={}
        for h in sorted({x['gold_count'] for x in a}):
            subgroup=[x for x in a if x['gold_count']==h]
            groups[str(h)]={'n':len(subgroup),'chain_at5':sum(x['chain_at_5'] for x in subgroup),
              'chain_at10':sum(x['chain_at_10'] for x in subgroup),
              'evidence_recall_at5':round(float(np.mean([x['evidence_recall_at_5'] for x in subgroup])),6)}
        methodmetrics={'n':len(a),'chain_at5':mean('chain_at_5'),'chain_at10':mean('chain_at_10'),
           'evidence_recall_at5':mean('evidence_recall_at_5'),'by_support_count':groups,
           'query_cost_ms_mean':{
             'bm25':round(float(np.mean([x['latency_ms']['bm25'] for x in a])),4),
             'graph_extra':round(float(np.mean([x['latency_ms']['indexed_graph'] for x in a])),4),
             'common_followup_extra':(round(float(np.mean([x['latency_ms']['shared_followup'] for x in a])),4) if method.startswith('v72_') else 0.),
             'arm_scoring_extra':round(float(np.mean([x['latency_ms']['arm_scoring'] for x in a])),4)},
           'mean_extra_bm25_queries':(round(float(np.mean([len(x['followup_queries']) for x in a])),5) if method.startswith('v72_') else 0.)}
        for comparator in ('bm25_graph_v71','v72_no_memory'):
            if method==comparator:continue
            for topk in (5,10):
                diffs=[by[qid][method][f'chain_at_{topk}']-items[comparator][f'chain_at_{topk}'] for qid,items in by.items()]
                methodmetrics[f'paired_vs_{comparator}_at{topk}']=confidence(diffs)
        methods[method]=methodmetrics
        print(name,method,'chain@5',methodmetrics['chain_at5'],'chain@10',methodmetrics['chain_at10'],flush=True)
    failure_counts=collections.Counter(x['reason'] for r in per if r['method']=='v72_relation_ledger' for x in r['missing_at5'])
    result={'dataset':name,'protocol':{
      'public_dev_reuse':True,'question_ids_disjoint_from_v7_v71':True,
      'pooled_document_universe':True,'question_count':len(rows),
      'no_gold_in_retriever':True,'answer_generation':False,
      'official_ircot_or_hipporag':False,'no_paid_api':True,
      'candidate_generation_identical_across_reset_and_ledger':True,
      'budget':{'secondary_bm25_calls_max':2,'beam':8,'fanout':8,'graph_depth':3,'topk':[5,10]},
      'fresh_qid_sha256':hashlib.sha256('\n'.join(sorted(by)).encode()).hexdigest()},
      'index':{'documents':len(docs),'bm25_seconds':s.bm_index_seconds,
         'title_graph':graph.stats,'relation_index_seconds':claims.seconds,
         'relation_links':len(claims.claims),'asserted_cue_links':sum(c.asserted for c in claims.claims),
         'potential_conflicts':len(claims.contradictions())},
      'methods':methods,'failure_reason_counts_ledger_at5':dict(failure_counts),
      'warnings':['Surface-pattern relation cue extraction is not full semantic understanding.',
        'Candidate recall and ranking classification is relative to V7.2 shared candidate pool.',
        'Latency is shared-process CPU post-index, not production/answer-generation latency.',
        'Bootstrap intervals describe sample variation, not generalization beyond public validation.']}
    out.mkdir(parents=True,exist_ok=True)
    with (out/(name+'_per_question.jsonl')).open('w') as f:
        for x in per:f.write(json.dumps(x,ensure_ascii=False)+'\n')
    (out/(name+'_summary.json')).write_text(json.dumps(result,indent=2))
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=('smoke','run'))
    p.add_argument('--datasets',nargs='+',choices=['2wiki','musique'],default=['2wiki','musique'])
    p.add_argument('--data',type=pathlib.Path,default=pathlib.Path('data'))
    p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('results-v72'))
    args=p.parse_args()
    if args.command=='smoke':
        from pger_v72_core import ClaimIndex
        d=[{'_id':'a','title':'Alpha Person','text':'Alpha Person was born in Beta Valley.'},
           {'_id':'b','title':'Beta Valley','text':'Beta Valley is located in Delta Country.'},
           {'_id':'c','title':'Delta Country','text':'Delta Country is large.'}]
        x=ClaimIndex(d);assert all(x.valid(c) for c in x.claims)
        assert 1 in [c.target for c in x.links[0]]
        print('V7.2 smoke pass');return
    reports=[]
    if '2wiki' in args.datasets:
        rows=load_fresh_wiki(args.data)
        reports.append(evaluate('2wiki_fresh_481_to_720',rows,make_corpus(rows),gold_2wiki,args.out))
    if 'musique' in args.datasets:
        rows=load_fresh_musique(args.data)
        reports.append(evaluate('musique_fresh_161_to_320',rows,pool_documents(rows),gold_musique,args.out))
    (args.out/'summary.json').write_text(json.dumps({'reports':reports},indent=2))
    print('V7.2 FRESH EVAL COMPLETE',flush=True)
if __name__=='__main__':main()