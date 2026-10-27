#!/usr/bin/env python3
"""V6.1: evidence-gap value gating and non-destructive ranking.
All parameters here are fixed prior to running this iteration's development experiment.
The sealed evaluation split is never read or scored. No LLM APIs.
"""
import argparse, collections, json, math, pathlib, re, time
import numpy as np
from benchmark_v6 import Retriever, download, load, measures, partition, SEED, proofgap

# Precommitted, heuristic settings (not fitted on the evaluation labels).
SEARCH_THRESHOLD=0.18
PROMOTION_THRESHOLD=0.18
MIN_MISSING_TERMS=2
PROTECTED_PREFIX=2

def query_terms(index, question):
    analyzer=index.words.build_analyzer()
    words=[w for w in analyzer(question) if w in index.words.vocabulary_]
    return sorted(set(words))

def document_terms(index, row):
    a,b=index.count.indptr[row:row+2]
    return set(index.count.indices[a:b])

def evidence_gap(index, question, first):
    words=query_terms(index,question)
    if not words or not first: return 0.0, [], [], 1.0
    seen=document_terms(index,first[0][0])
    total=sum(index.idfs.get(t,0) for t in words)
    missing=[t for t in words if index.words.vocabulary_[t] not in seen]
    present=[t for t in words if index.words.vocabulary_[t] in seen]
    mass=sum(index.idfs.get(t,0) for t in missing)/max(total,1e-8)
    s1=first[0][1]
    s2=first[1][1] if len(first)>1 else 0.
    margin=max(0.,min(1.,(s1-s2)/max(abs(s1),1e-8)))
    # A missing concept matters most when the original ranking is ambiguous.
    return mass,missing,present,margin

def guarded(index,question,cap=100):
    """Explicitly score expected value before querying; retain original order if no clear benefit.

    This is a *heuristic* expected-utility proxy, not a calibrated probability
    or a proof that any source is true.  Never sees reference relevance labels.
    """
    base=index.search(question,"bm25",cap)
    ids=[i for i,_ in base]
    info={"calls":1,"searched":False,"accepted":False,"gap":0.0,
          "proxy_value":0.0,"candidate_delta":0.0,"protected":True}
    if len(base)<4:return ids,info
    gap,missing,present,margin=evidence_gap(index,question,base)
    expected_value=gap*(1-margin)
    info["gap"]=gap;info["proxy_value"]=expected_value
    if len(missing)<MIN_MISSING_TERMS or expected_value<SEARCH_THRESHOLD:
        return ids,info

    # A single targeted query tests whether the missing concept can be filled.
    anchor=max(present,key=lambda t:index.idfs.get(t,0),default="")
    followup=" ".join(([anchor] if anchor else [])+missing[:12])
    extra=index.search(followup,"bm25",cap)
    info["calls"]=2;info["searched"]=True
    if not extra:return ids,info

    # Relevance gate: a new document must address missing query concepts,
    # retain meaningful original-query relevance, and be beyond the protected prefix.
    base_rank={i:j for j,i in enumerate(ids)}
    base_score={i:s for i,s in base}
    top=max(base[0][1],1e-8)
    candidates=[]
    full_mass=sum(index.idfs.get(t,0) for t in query_terms(index,question))
    gap_mass=max(sum(index.idfs.get(t,0) for t in missing),1e-8)
    for pos,(idx,score) in enumerate(extra[:20]):
        j=base_rank.get(idx,10000)
        if j<=PROTECTED_PREFIX:continue
        tset=document_terms(index,idx)
        overlap=sum(index.idfs.get(t,0) for t in missing if index.words.vocabulary_[t] in tset)
        coverage=overlap/gap_mass
        original=base_score.get(idx,0.0)/top
        if coverage<0.45 or original<0.25:continue
        # Move beyond small query-rewording gains only when a distinct
        # relevant document provides strong coverage of the missing terms.
        utility=(overlap/max(full_mass,1e-8))*(0.65+0.35*original)-0.08*(1-original)
        if utility>=PROMOTION_THRESHOLD:candidates.append((utility,idx,j))

    if not candidates:return ids,info
    candidates.sort(key=lambda x:(-x[0],x[2],index.ids[x[1]]))
    gain,chosen,from_pos=candidates[0]
    info["candidate_delta"]=gain
    # The first two BM25 documents cannot be displaced.
    if from_pos>=len(ids): return ids,info
    modified=ids[:PROTECTED_PREFIX]+[chosen]+[i for i in ids[PROTECTED_PREFIX:] if i!=chosen]
    info["accepted"]=modified!=ids
    info["protected"]=modified[:PROTECTED_PREFIX]==ids[:PROTECTED_PREFIX]
    return modified[:cap],info

def eval_dev(name,folder,result_dir,limit=0):
    docs,queries,gold=load(folder)
    engine=Retriever(docs)
    dev=[qid for qid in sorted(gold) if qid in queries and partition(name,qid)=="dev"]
    if limit:dev=dev[:limit]
    result_dir.mkdir(parents=True,exist_ok=True)
    rows_by_method={}
    summaries=[]
    for method in ["bm25","proofgap_v6","proofgap_v61"]:
        rows=[]
        for qid in dev:
            start=time.perf_counter()
            if method=="bm25":
                ids=[i for i,_ in engine.search(queries[qid],"bm25")]
                diag={"calls":1,"searched":False,"accepted":False}
            elif method=="proofgap_v6":
                ids,calls=proofgap(engine,queries[qid])
                diag={"calls":calls,"searched":calls==2,"accepted":calls==2}
            else:ids,diag=guarded(engine,queries[qid])
            latency=(time.perf_counter()-start)*1000
            # The sealed test never enters this code path.
            values=measures([engine.ids[i] for i in ids],gold[qid])
            rows.append({"qid":qid, "method":method,**values,
                         "search_calls":diag["calls"],"latency_ms":latency,
                         "searched":diag["searched"],"accepted":diag["accepted"]})
        rows_by_method[method]=rows
        fields=["ndcg10","recall10","recall100","mrr10","search_calls","latency_ms"]
        summary={"dataset":name,"split":"dev","method":method,"questions":len(rows),
                 "documents":len(docs),"split_seed":SEED,
                 "mean":{k:float(np.mean([x[k] for x in rows])) if rows else None for k in fields},
                 "second_searches":sum(x["searched"] for x in rows),
                 "rank_updates":sum(x["accepted"] for x in rows)}
        summaries.append(summary)
        with (result_dir/(name+"_"+method+"_per_query.jsonl")).open("w") as f:
            for r in rows:f.write(json.dumps(r)+"\n")
        (result_dir/(name+"_"+method+"_summary.json")).write_text(json.dumps(summary,indent=2))
        print(f'{name}/{method}: nDCG@10={summary["mean"]["ndcg10"]:.5f} '
              f'R@10={summary["mean"]["recall10"]:.5f} '
              f'calls={summary["mean"]["search_calls"]:.3f} '
              f'updates={summary["rank_updates"]}',flush=True)
    byid={m:{r["qid"]:r for r in rows} for m,rows in rows_by_method.items()}
    ref=byid["bm25"]
    diagnostics={}
    for method in ["proofgap_v6","proofgap_v61"]:
        vals=[(byid[method][q]["ndcg10"]-ref[q]["ndcg10"]) for q in dev]
        diagnostics[method]={
            "wins":sum(v>1e-10 for v in vals),
            "losses":sum(v< -1e-10 for v in vals),
            "ties":sum(abs(v)<=1e-10 for v in vals),
            "mean_delta":float(np.mean(vals)) if vals else None
        }
    (result_dir/(name+"_v61_paired.json")).write_text(json.dumps(diagnostics,indent=2))
    return summaries,diagnostics

def smoke_v61():
    docs=[{"_id":"a","title":"Alpha beta","text":"The alpha beta experiment measured temperatures."},
          {"_id":"b","title":"Gamma","text":"Gamma measurements used temperature monitoring."},
          {"_id":"c","title":"Delta","text":"Delta tracks an independent laboratory result."},
          {"_id":"d","title":"Other","text":"Unrelated astronomical observations of stars."}]
    model=Retriever(docs)
    ids,diag=guarded(model,"alpha beta experiment temperature")
    assert ids[:2]==[i for i,_ in model.search("alpha beta experiment temperature","bm25")][:2]
    assert diag["calls"] in (1,2)
    for query in ["gamma temperature monitoring","delta laboratory independent"]:
        ids,_=guarded(model,query)
        assert len(ids)==len(set(ids))
    print("V6.1 SMOKE PASS")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("command",choices=["smoke","dev"])
    parser.add_argument("--datasets",nargs="+",choices=["scifact","nfcorpus"],default=["scifact","nfcorpus"])
    parser.add_argument("--data",type=pathlib.Path,default=pathlib.Path("data"))
    parser.add_argument("--results",type=pathlib.Path,default=pathlib.Path("results-v61"))
    parser.add_argument("--limit",type=int,default=0)
    args=parser.parse_args()
    if args.command=="smoke":smoke_v61()
    else:
        for name in args.datasets:eval_dev(name,download(name,args.data),args.results,args.limit)
