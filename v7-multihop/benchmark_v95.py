#!/usr/bin/env python3
"""V9.5 predeclared graph-set gate. Public new IDs 160:240; no gold at inference."""
import argparse, collections, json, pathlib, time
import numpy as np
from sentence_transformers import CrossEncoder
from benchmark_v71_sag2_corpus import download, official_records, SAG2_AUTHOR, RELEASE
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger
from benchmark_v94 import score, ranked, fresh_candidates, MODEL, K

SEED=20261028
METHODS=("v71_fast","ce_fast64_prot2","ce_expand64_prot2","v95_graph_set_gate","v95_gate_fasttail")
def graph_set_diagnostic(graph, fast):
    """Undirected induced title-mention connectivity; negative set is retained."""
    top=list(dict.fromkeys(fast[:5])); selected=set(top)
    edges=set()
    for i in top:
        for j in graph.adj[i]:
            if j in selected and i!=j: edges.add((min(i,j),max(i,j)))
    adj={i:set() for i in top}
    for i,j in edges:adj[i].add(j);adj[j].add(i)
    unseen=set(top);largest=0
    while unseen:
        start=next(iter(unseen));stack=[start];unseen.remove(start);n=0
        while stack:
            node=stack.pop();n+=1
            for neighbor in adj[node]&unseen:
                unseen.remove(neighbor);stack.append(neighbor)
        largest=max(largest,n)
    positive={i for i in top if adj[i]}
    negative=selected-positive
    assert positive.isdisjoint(negative) and positive|negative==selected
    return {"strong":len(edges)>=2 and largest>=3,
            "edges":len(edges),"largest_component":largest,
            "positive":sorted(positive),"negative":sorted(negative)}
def bootstrap(a,b):
    diff=np.asarray(a,dtype=float)-np.asarray(b,dtype=float)
    rng=np.random.default_rng(SEED)
    draws=np.mean(diff[rng.integers(0,len(diff),(3000,len(diff)))],axis=1)
    return {"delta_pp":round(float(diff.mean()*100),2),
      "ci95_pp":[round(float(x*100),2) for x in np.quantile(draws,[.025,.975])],
      "wins":int(sum(diff>0)),"losses":int(sum(diff<0))}
def bench(name,root,out,start,n,ce):
    hashes=download(name,root);unique,docs,rows=official_records(name,root)
    assert len(rows)==1000 and len(docs)==SAG2_AUTHOR[name]["corpus"]
    sources=list(unique);s=time.perf_counter();bm=SparseMethods(docs)
    bm_index_s=time.perf_counter()-s;s=time.perf_counter();graph=EvidenceLedger(bm)
    graph_index_s=time.perf_counter()-s
    cases=[];times=collections.defaultdict(list)
    for position,row in enumerate(rows[start:start+n]):
        q=row["question"];gold=set(row["gold"])
        t=time.perf_counter();bmraw=bm.index.search(q,"bm25",100)
        b=[i for i,_ in bmraw] or list(range(min(100,len(docs))))
        fast,_=graph.search(q,b,mode="one-hop",bmraw=bmraw)
        fast_ms=(time.perf_counter()-t)*1000
        diag=graph_set_diagnostic(graph,fast)
        first=list(dict.fromkeys(fast+b))[:K]
        fs,first_ms=score(ce,q,docs,first)
        seed=ranked(first,fs,fast)[:3]
        tail=[i for i in list(dict.fromkeys(fast+b)) if i not in first][:K]
        ts,tail_ms=score(ce,q,docs,tail)
        t=time.perf_counter();new,trace=fresh_candidates(q,docs,fast,b,bm,seed,set(first),K)
        expand_ms=(time.perf_counter()-t)*1000
        ns,new_ms=score(ce,q,docs,new)
        fast_ce=ranked(first+tail,fs|ts,fast,protect=2)
        expanded_ce=ranked(first+new,fs|ns,fast,protect=2)
        ranks={"v71_fast":fast,"ce_fast64_prot2":fast_ce,
          "ce_expand64_prot2":expanded_ce,
          "v95_graph_set_gate":fast if diag["strong"] else expanded_ce,
          "v95_gate_fasttail":fast if diag["strong"] else fast_ce}
        metrics={}
        for method,rank in ranks.items():
            docs_at=[sources[i] for i in rank[:10]]
            metrics[method]={"ae5":int(gold<=set(docs_at[:5])),
              "ae10":int(gold<=set(docs_at[:10])),
              "r5":len(gold&set(docs_at[:5]))/len(gold),
              "r10":len(gold&set(docs_at[:10]))/len(gold)}
        cases.append({"id":row["id"],"n_gold":len(gold),"metrics":metrics,
          "gate":diag,"candidate_full":{
            "fast64":int(gold<={sources[i] for i in first+tail}),
            "expand64":int(gold<={sources[i] for i in first+new})},
          "candidate_count":{"fast64":len(first+tail),"expand64":len(first+new)},
          "expansion_queries":len(trace),
          "top5":{k:[docs[i]["title"] for i in v[:5]] for k,v in ranks.items()}})
        for key,val in [("fast_ms",fast_ms),("first_ce_ms",first_ms),
                        ("tail_ce_ms",tail_ms),("new_ce_ms",new_ms),("expand_ms",expand_ms)]:
            times[key].append(val)
        if (position+1)%20==0:print(name,start+position+1,"/",start+n,flush=True)
    results={}
    for method in METHODS:
        data=[p["metrics"][method] for p in cases]
        result={key:round(float(np.mean([x[key] for x in data])),6)
                for key in ("ae5","ae10","r5","r10")}
        result["by_required_sources"]={
            str(k):{"n":sum(p["n_gold"]==k for p in cases),
              "ae5":sum(p["n_gold"]==k and p["metrics"][method]["ae5"] for p in cases),
              "ae10":sum(p["n_gold"]==k and p["metrics"][method]["ae10"] for p in cases)}
            for k in sorted(set(p["n_gold"] for p in cases))}
        result["vs_v71"]=bootstrap([x["ae5"] for x in data],
            [p["metrics"]["v71_fast"]["ae5"] for p in cases])
        result["vs_equal_budget_expanded"]=bootstrap([x["ae5"] for x in data],
            [p["metrics"]["ce_expand64_prot2"]["ae5"] for p in cases])
        result["vs_equal_budget_fasttail"]=bootstrap([x["ae5"] for x in data],
            [p["metrics"]["ce_fast64_prot2"]["ae5"] for p in cases])
        results[method]=result
    cpu={k:{"mean_ms":round(float(np.mean(v)),2),
            "p95_ms":round(float(np.percentile(v,95)),2)} for k,v in times.items()}
    strong=sum(p["gate"]["strong"] for p in cases)
    cpu["gate_fast_fraction"]=round(strong/len(cases),4)
    cpu["estimated_guarded_inference_ms_mean"]=round(float(np.mean(
        [0 if p["gate"]["strong"] else times["first_ce_ms"][i]+times["new_ce_ms"][i]
         for i,p in enumerate(cases)])),2)
    cpu["estimated_expanded_inference_ms_mean"]=round(float(np.mean(
        [a+b for a,b in zip(times["first_ce_ms"],times["new_ce_ms"])])),2)
    summary={"dataset":name,"range":[start,start+n],"n":len(cases),
      "corpus_documents":len(docs),"source_revision":RELEASE,
      "source_hashes":hashes,"model":MODEL,"index_seconds":{
        "bm25":round(bm_index_s,2),"graph":round(graph_index_s,2)},
      "results":results,"cpu":cpu,"candidate_full":{
        "fast64":sum(p["candidate_full"]["fast64"] for p in cases),
        "expand64":sum(p["candidate_full"]["expand64"] for p in cases)},
      "gate_strong":strong,
      "limitations":["Public question IDs 160:240, not sealed independent test",
        "No SAG2 JEV rerun; no generated answers or semantic entailment",
        "Graph connectivity is not proof of correctness",
        "All CE scores physically computed; guarded inference cost is projected",
        "No model or threshold tuning after inspection"]}
    out.mkdir(parents=True,exist_ok=True)
    (out/f"{name}_{start}_{start+n}_summary.json").write_text(json.dumps(summary,indent=2))
    with (out/f"{name}_{start}_{start+n}_cases.jsonl").open("w") as f:
        for p in cases:f.write(json.dumps(p,ensure_ascii=False)+"\n")
    print("RESULT",name,json.dumps(summary),flush=True)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("smoke","run"))
    p.add_argument("--start",type=int,default=160)
    p.add_argument("--limit",type=int,default=80)
    p.add_argument("--data",type=pathlib.Path,default=pathlib.Path("data/sag2_official"))
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v95"))
    a=p.parse_args()
    if a.command=="smoke":
        class G:adj=[(1,),(0,2),(1,),(4,),(3,)]
        d=graph_set_diagnostic(G(),[0,1,2,3,4])
        assert d["strong"] and d["largest_component"]==3
        class H:adj=[(),(),(),(),()]
        d=graph_set_diagnostic(H(),[0,1,2,3,4])
        assert not d["strong"] and len(d["negative"])==5
        print("V9.5 graph-set gate smoke PASS");return
    assert a.start==160 and a.limit==80,"Frozen V9.5 cohort only"
    import torch
    torch.set_num_threads(2)
    ce=CrossEncoder(MODEL,max_length=224,device="cpu")
    for name in ("musique","2wikimultihopqa"):
        bench(name,a.data,a.out,a.start,a.limit,ce)
    print("V9.5 FROZEN RUN COMPLETE",flush=True)
if __name__=="__main__":main()
