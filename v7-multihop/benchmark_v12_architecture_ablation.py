#!/usr/bin/env python3
"""PGER V12: three architectural *proxies* on exactly one fixed candidate pool.

Comparisons are inspired by, but NOT executions of:
  SAG2: score-conditioned local DPP source diversity (full system uses JEV)
  HippoRAG 2: seeded evidence graph spreading (full uses OpenIE+PPR)
  S2G-RAG: unmet-question-facet selection (full uses a trained sufficiency judge)
PGER retains its cached 23-feature learned necessity score and original
source-ID/provenance; no source relationship is claimed verified.

Train frozen boosted scorer on MultiHopRAG public question indices 0:400.
One NEW-TO-PGER confirmation question slice 2000:2400. 609 corpus articles
are reused, so this is not source-disjoint validation or a true independent
official leaderboard. All variant inputs / query counts are identical.
Source labels are ONLY consulted after all scores and rankings are frozen.
"""
from __future__ import annotations

import argparse,collections,hashlib,json,pathlib,time
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from benchmark_v101_multihoprag import get,make_corpus,map_gold
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger
from benchmark_v95_controlled import paired,cpu_ms
from benchmark_v113 import doc_cache,prepare
from benchmark_v111 import reorder,score
from expansion_v92 import terms

SEED=20261028
TRAIN=(0,400)
TEST=(2000,2400)
POOL_K=120
FINAL_K=5
DPP_SCAN=10
PPR_TOP_NEIGHBORS=8
PPR_STEPS=10
PPR_DAMPING=.78
PPR_MIX=.22
GAP_BONUS=.16
METHODS=("bm25","v71_fast","pger_boosted",
         "sag2_dpp_proxy","hipporag2_local_ppr_proxy","s2g_gap_proxy")
LICENSE_NOTE="All 3 are independently authored cheap architecture-inspired proxies; they ARE NOT official baseline implementations."

def build_doc_vectors(docs):
    """One entirely offline lexical representation, shared by DPP and PPR."""
    texts=[(d["title"]+" "+d["title"]+" "+
            d.get("text","")[:1800]) for d in docs]
    t=time.process_time()
    v=TfidfVectorizer(ngram_range=(1,2),min_df=1,max_features=18000,
                      sublinear_tf=True,dtype=np.float32,
                      norm="l2").fit_transform(texts)
    return v,cpu_ms(t)

def baseline_order(probs,pool,fast):
    # Exactly the frozen V11.3/11.4 boosted ranking.
    return reorder(probs,fast,pool)

def quality_scores(probs,pool):
    # A 0..1 probability is not source entailment.
    return {int(doc):max(0.0001,min(.9999,float(p)))
            for doc,p in zip(pool,probs)}

def sag2_dpp_proxy(base,quality,vectors):
    """DPP rank within an unchanged TOP TEN candidate set.
    SAG2 source code's greedy DPP uses JEV quality scores and TF-IDF kernel;
    we substitute existing PGER learned relevance, NOT JEV.
    """
    t=time.process_time()
    head=list(base[:DPP_SCAN])
    if len(head)<2:return base,[],cpu_ms(t)
    sim=(vectors[head]@vectors[head].T).toarray()
    sim=np.clip(sim,0.0,1.0)
    q=np.array([quality.get(i,.001) for i in head],dtype=float)
    K=(q[:,None]*q[None,:])*sim
    np.fill_diagonal(K,q*q)
    remaining=list(range(len(head)))
    selected=[]
    coeffs=np.zeros((len(head),len(head)),dtype=float)
    residual=np.diag(K).copy()
    while remaining:
        winner=max(remaining,key=lambda i:(residual[i],-i))
        if residual[winner] <= 1e-10:
            selected.extend(remaining);break
        selected.append(winner)
        remaining.remove(winner)
        den=max(1e-10,float(np.sqrt(residual[winner])))
        pos=len(selected)-1
        for k in remaining:
            projected= (K[winner,k]-float(coeffs[winner,:pos]@coeffs[k,:pos]))/den
            coeffs[k,pos]=projected
            residual[k]=max(0.0,residual[k]-projected*projected)
    ranked=[head[i] for i in selected]+base[DPP_SCAN:]
    audit=[{"doc_id":int(head[i]),"dpp_position":j,
            "relevance_proxy":round(float(q[i]),4)}
           for j,i in enumerate(selected[:FINAL_K])]
    assert len(set(ranked))==len(ranked)
    return ranked,audit,cpu_ms(t)

def hipporag_local_ppr_proxy(base,quality,pool,vectors):
    """Bounded query-scoped *document* graph and seeded PPR proxy.

    The official HippoRAG2 constructs fact/entity edges offline with OpenIE
    and uses PPR. This lightweight proxy has ONLY lexical TF-IDF links;
    it does not reproduce or claim the official system.
    """
    t=time.process_time()
    if len(pool)<2:return base,[],cpu_ms(t)
    nodes=list(pool[:POOL_K])
    sub=(vectors[nodes]@vectors[nodes].T).toarray()
    np.fill_diagonal(sub,0.)
    graph=np.zeros_like(sub,dtype=np.float64)
    for i in range(len(nodes)):
        js=np.argsort(-sub[i])[:PPR_TOP_NEIGHBORS]
        for j in js:
            if sub[i,j]>=.12:
                graph[i,j]=float(sub[i,j])
    # Undirected adjacency, bounded no large global graph indexing.
    graph=np.maximum(graph,graph.T)
    degree=graph.sum(axis=1)
    for i in range(len(nodes)):
        if degree[i]<=0:graph[i,i]=1.
    graph/=np.maximum(1e-9,graph.sum(axis=1))[:,None]
    qs=np.array([quality.get(d,0.0001) for d in nodes],dtype=float)
    seeds=np.zeros(len(nodes),dtype=float)
    # Personalize restart to learned score's strongest 8 source passages.
    topseed=np.argsort(-qs)[:8]
    seeds[topseed]=qs[topseed]
    seeds/=max(1e-12,seeds.sum())
    p=seeds.copy()
    for step in range(PPR_STEPS):
        p=(1-PPR_DAMPING)*seeds+PPR_DAMPING*(graph.T@p)
    pq=qs / max(1e-9,qs.max())
    ppr=p / max(1e-9,p.max())
    combined=(1-PPR_MIX)*pq+PPR_MIX*ppr
    pos={d:i for i,d in enumerate(base)}
    sorted_nodes=sorted(nodes,
          key=lambda d:(-combined[nodes.index(d)],pos.get(d,1000),d))
    result=sorted_nodes+[d for d in base if d not in set(sorted_nodes)]
    trace=[{"doc_id":int(d),"seed_q":round(float(seeds[nodes.index(d)]),5),
            "ppr":round(float(p[nodes.index(d)]),5),
            "lexical_edges_only":True,"relation_verified":False}
           for d in result[:FINAL_K]]
    return result,trace,cpu_ms(t)

def s2g_gap_proxy(question,docs,base,quality):
    """Question-term coverage *proxy*, NOT S2G's learned sufficient/gap judge.

    No extra model call / query. At each selection, compute uncovered lexical
    question terms and marginal source support. Keep original necessary-evidence
    probability and only add a bounded gap bonus.
    """
    t=time.process_time()
    important={w for w in terms(question) if len(w)>=3}
    if not important:return base,[],cpu_ms(t)
    source_terms={}
    for docid in base[:POOL_K]:
        d=docs[docid]
        text=d["title"]+" "+d.get("text","")[:1000]
        source_terms[docid]=set(terms(text)) & important
    selected=[];remaining=list(base[:POOL_K]);covered=set()
    evidence=[]
    original={d:i for i,d in enumerate(base)}
    while len(selected)<10 and remaining:
        def preference(d):
            uncovered=source_terms[d]-covered
            novelty=len(uncovered)/max(1,len(important))
            # Conservative gap compensation: cannot overpower large
            # learned-score differences or fake an unsupported link.
            return quality.get(d,0.)+GAP_BONUS*novelty
        next_doc=max(remaining,key=lambda d:(preference(d),-original[d],-d))
        debt=sorted(source_terms[next_doc]-covered)
        evidence.append({"doc_id":int(next_doc),
          "uncovered_question_terms":debt,
          "source_relation_verified":False})
        selected.append(next_doc)
        remaining.remove(next_doc)
        covered |= source_terms[next_doc]
    result=selected+[d for d in base if d not in set(selected)]
    return result,evidence[:FINAL_K],cpu_ms(t)

def prepare_corpus(original):
    docs=make_corpus(original)
    assert len(docs)>100
    docdata,cost=doc_cache(docs)
    t=time.process_time()
    retrieval=SparseMethods(docs)
    build_bm=cpu_ms(t)
    t=time.process_time()
    graph=EvidenceLedger(retrieval)
    build_graph=cpu_ms(t)
    vec,vec_cpu=build_doc_vectors(docs)
    return docs,docdata,retrieval,graph,vec,{
         "tokens_cpu_ms":round(cost,3),
         "bm25_cpu_ms":round(build_bm,3),
         "title_graph_cpu_ms":round(build_graph,3),
         "tfidf_cpu_ms":round(vec_cpu,3),
         "tfidf_bytes_sparse":int(vec.data.nbytes+vec.indices.nbytes+
                                  vec.indptr.nbytes)}

def run(rawdocs,questions,hashes,out):
    docs,doc_cache_data,sm,graph,vec,offline=prepare_corpus(rawdocs)
    # Original frozen V11.3 training data/policy, no evidence from V12 test.
    Xs=[];ys=[];train=0;skips=collections.Counter()
    for r in questions[TRAIN[0]:TRAIN[1]]:
        q=str(r.get("query",r.get("question",""))).strip()
        if not q:skips["empty"]+=1;continue
        gold,flags,n=map_gold(r,docs)
        if n<2 or len(gold)!=n or "unresolved_evidence_identity" in flags:
            skips["unmapped"]+=1;continue
        pack=prepare(q,sm,graph,docs,doc_cache_data)
        Xs.append(pack["X"])
        ys.extend(int(i in gold) for i in pack["pool"])
        train+=1
    X=np.vstack(Xs);Y=np.asarray(ys,dtype=np.int32)
    assert train>=250 and X.shape[1]==23 and Y.sum()>500
    model=HistGradientBoostingClassifier(
        max_iter=100,max_leaf_nodes=15,learning_rate=.08,
        l2_regularization=1.,class_weight="balanced",random_state=SEED)
    t=time.process_time();model.fit(X,Y);fitms=cpu_ms(t)
    scored=[];unmapped=collections.Counter()
    for raw in questions[TEST[0]:TEST[1]]:
        q=str(raw.get("query",raw.get("question",""))).strip()
        if not q:unmapped["empty"]+=1;continue
        pack=prepare(q,sm,graph,docs,doc_cache_data)
        t=time.process_time();p=model.predict_proba(pack["X"])[:,1]
        model_cpu=cpu_ms(t)
        t=time.process_time()
        base=baseline_order(p,pack["pool"],pack["fast"])
        base_cpu=cpu_ms(t)
        quality=quality_scores(p,pack["pool"])
        sag,sag_trace,sag_cpu=sag2_dpp_proxy(base,quality,vec)
        hip,hip_trace,hip_cpu=hipporag_local_ppr_proxy(base,quality,pack["pool"],vec)
        s2g,s2g_trace,s2g_cpu=s2g_gap_proxy(q,docs,base,quality)
        rankings={"bm25":pack["bm"],"v71_fast":pack["fast"],
                  "pger_boosted":base,
                  "sag2_dpp_proxy":sag,
                  "hipporag2_local_ppr_proxy":hip,
                  "s2g_gap_proxy":s2g}
        # Inspect gold annotations only AFTER all rankings and trace creation.
        gold,flags,n=map_gold(raw,docs)
        if n<2 or len(gold)!=n or "unresolved_evidence_identity" in flags:
            unmapped["unmapped"]+=1;continue
        scored.append({
           "id":str(raw.get("id",raw.get("_id",""))),"question":q,
           "support_count":len(gold),
           "full_gold_in_pool":int(gold<=set(pack["pool"])),
           "pool_size":len(pack["pool"]),
           "top10":{name:[docs[d]["_id"] for d in order[:10]]
                    for name,order in rankings.items()},
           "metrics":{name:score(order,gold)
                      for name,order in rankings.items()},
           "trace":{"sag2_proxy":sag_trace,"hipporag2_proxy":hip_trace,
                    "s2g_proxy":s2g_trace},
           "cpu_ms":{"base_retrieval":pack["time"]["base"],
                     "extra_search":pack["time"]["extra"],
                     "cached_features":pack["time"]["features"],
                     "boosted_prediction":model_cpu,
                     "boosted_ranking":base_cpu,
                     "sag2_dpp_proxy":sag_cpu,
                     "hipporag2_local_ppr_proxy":hip_cpu,
                     "s2g_gap_proxy":s2g_cpu}
        })
        if len(scored)%50==0:
            print("V12_PROGRESS",len(scored),flush=True)
    assert len(scored)>=200,"Unexpected source-ID mapping or corpus size"
    summary={
      "stage":"V12_top3_architecture_proxies",
      "dataset":"MultiHop-RAG / 609 pooled ODC-BY news articles",
      "source_sha256":hashes,"train_offsets":list(TRAIN),
      "confirmation_offsets":list(TEST),
      "public_question_cohort_new_to_PGER":True,
      "source_articles_shared_across_train_test":True,
      "original_confirmation_n":TEST[1]-TEST[0],
      "n_confirmation":len(scored),
      "n_training":train,"train_positive_pairs":int(Y.sum()),
      "train_source_identity_issues":dict(skips),
      "confirmation_unmapped":dict(unmapped),
      "model_fit_cpu_ms":round(fitms,2),
      "offline_index_cost":offline,
      "methods":{}, "component_cpu_ms":{}, "component_cpu_p95_ms":{},
      "warning":LICENSE_NOTE,
      "limitations":[
          "SAG2 uses JEV necessity and its own retrieval; this DPP-only proxy DOES NOT run SAG2",
          "HippoRAG 2 uses OpenIE fact/entity graph+PPR; this lightweight document-graph proxy DOES NOT run HippoRAG2",
          "S2G uses a trained sufficiency gap judge and extraction; lexical-gap proxy DOES NOT run S2G-RAG",
          "Full official baseline head-to-head NOT performed; avoid borrowing published scores",
          "All 3 share same learned scores, initial searches, 120-candidate pool",
          "Source text match/cooccurrence is not verified fact entailment",
          "Original question labels previously inspected in this corpus but these query IDs are new to PGER",
          "Questions differ but training/test source articles overlap",
          "No generated answers, logical 5/6/8-hop, source entailment or factual abstention",
          "CPU are process timings on one hosted runner, not wall-clock production metrics",
          "Public gold URL/unique-title ambiguous question exclusions can bias results"]
    }
    for method in METHODS:
        stats={k:round(float(np.mean([x["metrics"][method][k]
              for x in scored])),6) for k in ("ae5","ae10","r5","r10")}
        stats["by_support_count"]={str(n):{
          "n":sum(x["support_count"]==n for x in scored),
          "ae5":sum(x["support_count"]==n and
                    x["metrics"][method]["ae5"] for x in scored),
          "ae10":sum(x["support_count"]==n and
                     x["metrics"][method]["ae10"] for x in scored),
          "full_candidate":sum(x["support_count"]==n and
                               x["full_gold_in_pool"] for x in scored)}
             for n in sorted(set(x["support_count"] for x in scored))}
        for baseline in ("v71_fast","pger_boosted"):
            if method==baseline:continue
            stats["paired_vs_"+baseline]=paired(
                [x["metrics"][method]["ae5"] for x in scored],
                [x["metrics"][baseline]["ae5"] for x in scored])
        summary["methods"][method]=stats
    for cost in ("base_retrieval","extra_search","cached_features",
                 "boosted_prediction","boosted_ranking",
                 "sag2_dpp_proxy","hipporag2_local_ppr_proxy","s2g_gap_proxy"):
        ms=[x["cpu_ms"][cost] for x in scored]
        summary["component_cpu_ms"][cost]=round(float(np.mean(ms)),4)
        summary["component_cpu_p95_ms"][cost]=round(float(np.percentile(ms,95)),4)
    out.mkdir(parents=True,exist_ok=True)
    (out/"summary.json").write_text(json.dumps(summary,indent=2))
    with (out/"cases.jsonl").open("w") as f:
        for x in scored:f.write(json.dumps(x,ensure_ascii=False)+"\n")
    print("V12_RESULT",json.dumps(summary),flush=True)

def smoke():
    from scipy.sparse import csr_matrix
    v=csr_matrix(np.array([[1,0],[.9,.1],[0,1.]],dtype=np.float32))
    base=[0,1,2]
    qualities={0:.8,1:.7,2:.6}
    d,trace,_=sag2_dpp_proxy(base,qualities,v)
    h,trace2,_=hipporag_local_ppr_proxy(base,qualities,base,v)
    q,trace3,_=s2g_gap_proxy("What did Alice do in Paris?",
             [{"title":"Alice","text":"Alice lived in Paris"},
              {"title":"Paris","text":"paris"},
              {"title":"Other","text":"none"}],base,qualities)
    assert set(d)==set(h)==set(q)==set(base)
    assert all(not x.get("relation_verified",True) for x in trace2)
    print("V12 three architecture proxy smoke PASS")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("smoke","run"))
    p.add_argument("--data",type=pathlib.Path,
                   default=pathlib.Path("data/multihoprag_pinned"))
    p.add_argument("--out",type=pathlib.Path,
                   default=pathlib.Path("results-v12"))
    a=p.parse_args()
    if a.command=="smoke":return smoke()
    docs,questions,hashes=get(a.data)
    assert len(questions)>=TEST[1],"MultiHopRAG record count too small"
    run(docs,questions,hashes,a.out)
if __name__=="__main__":main()
