#!/usr/bin/env python3
"""PGER V11.3: frozen cached-feature speed and three supervised rankers.

Source: MultiHopRAG 609-news-article ODC-BY corpus. Training questions
0..399, strict new-to-PGER confirmation questions 1200..1599; candidate
pool remains V11.1 fixed 120-document union. Labels only train rankings.
This is standard supervised IR prior art, not semantic entailment, generated
answers, new retrieval novelty, or independent sealed SOTA.
"""
import argparse,collections,hashlib,json,pathlib,re,time
import numpy as np
from sklearn.ensemble import RandomForestClassifier,HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from benchmark_v101_multihoprag import get,make_corpus,map_gold
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger
from benchmark_v95_controlled import initial,paired,unique,cpu_ms
from benchmark_v11 import facet_queries,candidate_pool,fusion
from benchmark_v111 import (data_features,tokenize,weight_overlap,reorder,
                            score,MAX_DOC_CHARS,RX_YEAR,SEED)
TRAIN=(0,400)
CONF=(1200,1600)
METHODS=("bm25","v71_fast","rf_cached","linear_cached","boosted_cached")
FRAC_PARITY=15

def doc_cache(docs):
    t=time.process_time()
    cache=[]
    for d in docs:
        title=d["title"];body=d.get("text","")[:MAX_DOC_CHARS]
        source=str(d.get("source",""))
        cache.append({
           "title":title,"source":source,
           "tx":tokenize(title),"bx":tokenize(body),
           "sx":tokenize(source),"years":set(RX_YEAR.findall(title+" "+body)),
           "body_length":len(body)})
    return cache,cpu_ms(t)

def cached_data_features(q,docs,bm,fast,facets,hits,pool,idf,cache):
    qwords=tokenize(q)
    year=set(RX_YEAR.findall(q))
    fw=[tokenize(s) for s in facets]
    low=q.casefold()
    rb={d:r for r,d in enumerate(bm)}
    rf={d:r for r,d in enumerate(fast)}
    fr=[{d:r for r,d in enumerate(h)} for h in hits]
    X=[];F=[]
    for d in pool:
        c=cache[d]
        tx=c["tx"];bx=c["bx"];sx=c["sx"]
        ft=[weight_overlap(x,tx|bx,idf) for x in fw]
        ranks=[r.get(d,100) for r in fr]
        src=c["source"].strip().casefold()
        title=c["title"]
        bmr=rb.get(d,100);far=rf.get(d,100)
        X.append([
          min(1.,len(qwords)/28),min(1.,len(tx)/14),
          1/(1+bmr),1/(1+far),
          float(d in fast[:5]),float(d in bm[:5]),
          weight_overlap(qwords,tx,idf),
          weight_overlap(qwords,bx,idf),
          weight_overlap(qwords,tx|bx,idf),
          len(qwords&tx)/max(1,len(qwords)),
          len(qwords&bx)/max(1,len(qwords)),
          float(len(src)>=4 and src in low),
          float(bool(sx) and bool(sx&qwords)),
          float(len(title)>=7 and title.casefold() in low),
          len(year&c["years"])/max(1,len(year)),
          max(ft) if ft else 0.,
          sum(ft)/max(1,len(ft)),
          min(1.,sum(ft)/max(1,len(ft))),
          sum(1 for f in ft if f>=.30)/max(1,len(ft)),
          min((1/(1+r) for r in ranks),default=0.),
          sum(1/(1+r) for r in ranks)/max(1,len(ranks)),
          float(len(facets)),min(1.,c["body_length"]/MAX_DOC_CHARS)
        ])
        F.append(ft)
    return np.asarray(X,dtype=np.float32),F

def prepare(q,sm,graph,docs,cache,parity=False):
    bm,fast,base_ms=initial(q,sm,graph)
    raw=sm.index.search(q,"bm25",100)
    bm=unique([i for i,_ in raw] or bm)
    facets=facet_queries(q)[:2]
    t=time.process_time()
    hits=[[i for i,_ in sm.index.search(f,"bm25",50)] for f in facets]
    extra_ms=cpu_ms(t)
    f=fusion(fast,bm,hits)
    pool=candidate_pool(fast,bm,hits)
    t=time.process_time()
    X,_=cached_data_features(q,docs,bm,fast,facets,hits,pool,sm.index.idfs,cache)
    features_ms=cpu_ms(t)
    delta=0
    if parity:
        t=time.process_time()
        Xorig,_=data_features(q,docs,bm,fast,facets,hits,pool,sm.index.idfs)
        old_ms=cpu_ms(t)
        assert Xorig.shape==X.shape and np.allclose(
            Xorig,X,rtol=1e-7,atol=1e-7),"Feature cache changed numeric values"
        delta=old_ms
    return {"bm":bm,"fast":fast,"pool":pool,"X":X,
            "time":{"base":base_ms,"extra":extra_ms,
                    "features":features_ms,"uncached_parity":delta}}

def fit_models(X,Y):
    specs={
     "rf_cached":RandomForestClassifier(n_estimators=120,max_depth=10,
                  min_samples_leaf=5,class_weight="balanced_subsample",
                  n_jobs=2,random_state=SEED),
     "linear_cached":make_pipeline(StandardScaler(),
                  LogisticRegression(C=1.0,class_weight="balanced",
                  max_iter=500,solver="liblinear",random_state=SEED)),
     "boosted_cached":HistGradientBoostingClassifier(
                  max_iter=100,max_leaf_nodes=15,learning_rate=.08,
                  l2_regularization=1.,class_weight="balanced",random_state=SEED)}
    fitting={}
    for key,model in specs.items():
        t=time.process_time();model.fit(X,Y)
        fitting[key]=round(cpu_ms(t),2)
    return specs,fitting

def go(rawdocs,questions,hashes,out):
    docs=make_corpus(rawdocs)
    cache,cache_build=doc_cache(docs)
    t=time.process_time();sm=SparseMethods(docs);index_ms=cpu_ms(t)
    t=time.process_time();graph=EvidenceLedger(sm);graph_ms=cpu_ms(t)
    Xs=[];Ys=[];train_n=0;train_skipped=collections.Counter()
    for r in questions[TRAIN[0]:TRAIN[1]]:
        q=str(r.get("query",r.get("question",""))).strip()
        if not q:train_skipped["empty_question"]+=1;continue
        gold,flags,n=map_gold(r,docs)
        if n<2 or len(gold)!=n or "unresolved_evidence_identity" in flags:
            train_skipped["unresolved_gold"]+=1;continue
        bundle=prepare(q,sm,graph,docs,cache,parity=train_n<FRAC_PARITY)
        Xs.append(bundle["X"]);Ys.extend(int(d in gold) for d in bundle["pool"])
        train_n+=1
        if train_n%100==0:print("V113_TRAIN",train_n,flush=True)
    X=np.vstack(Xs);Y=np.asarray(Ys,np.int32)
    assert X.shape[1]==23 and Y.sum()>100
    models,fit_cost=fit_models(X,Y)
    cases=[];skip=collections.Counter()
    for r in questions[CONF[0]:CONF[1]]:
        q=str(r.get("query",r.get("question",""))).strip()
        if not q:skip["empty_question"]+=1;continue
        b=prepare(q,sm,graph,docs,cache,parity=len(cases)<FRAC_PARITY)
        ranks={"bm25":b["bm"],"v71_fast":b["fast"]}
        times={}
        for name,model in models.items():
            t=time.process_time()
            probs=model.predict_proba(b["X"])[:,1]
            inference=cpu_ms(t)
            t=time.process_time();ranks[name]=reorder(probs,b["fast"],b["pool"])
            rank_ms=cpu_ms(t)
            times[name]={"predict_cpu_ms":inference,"rank_cpu_ms":rank_ms}
        # Offline confirmation annotation use only AFTER all online ranking.
        gold,flags,n=map_gold(r,docs)
        if n<2 or len(gold)!=n or "unresolved_evidence_identity" in flags:
            skip["unresolved_gold"]+=1;continue
        cases.append({"id":str(r.get("id",r.get("_id",""))),"question":q,
           "required_sources":len(gold),
           "full_candidate":int(gold<=set(b["pool"])),
           "metrics":{m:score(v,gold) for m,v in ranks.items()},
           "top10":{m:[docs[i]["_id"] for i in v[:10]] for m,v in ranks.items()},
           "time_common_cpu_ms":b["time"],"time_model_cpu_ms":times})
        if len(cases)%50==0:print("V113_CONFIRM",len(cases),flush=True)
    assert len(cases)>200
    obj={"stage":"V11.3","split_train":list(TRAIN),"split_confirm":list(CONF),
         "dataset":"MultiHopRAG 609 news article corpus",
         "sha256":hashes,"corpus_documents":len(docs),
         "n_train_questions":train_n,"n_train_pairs":len(Y),
         "train_positive":int(Y.sum()),"n_confirmation":len(cases),
         "train_skips":dict(train_skipped),"confirmation_skips":dict(skip),
         "cpu_offline_build_ms":{"token_cache":cache_build,"bm25":index_ms,
                                 "graph":graph_ms},
         "model_fit_cpu_ms":fit_cost,"methods":{},"mean_cost_cpu_ms":{},
         "p95_cost_cpu_ms":{},
         "limitations":[
           "Confirmation new to this PGER project but is public and same news corpus",
           "Question/answer labels in training only; source/article reuse across cohorts possible",
           "Only document coverage; NO source relationship entailment or generated answer evaluation",
           "Four source articles do not certify four logical reasoning hops",
           "Training source supervision and supervised rankers are established IR methods",
           "CPU process cost, not true production wall, cold query p95 or commercial comparison",
           "Offline candidate pool may expose 120/609 documents; not zero-ingestion system"]}
    for m in METHODS:
        summary={metric:round(float(np.mean([p["metrics"][m][metric]
                                            for p in cases])),6)
                 for metric in ("ae5","ae10","r5","r10")}
        summary["by_support_count"]={str(n):{
           "n":sum(p["required_sources"]==n for p in cases),
           "ae5":sum(p["required_sources"]==n and p["metrics"][m]["ae5"]
                      for p in cases),
           "ae10":sum(p["required_sources"]==n and p["metrics"][m]["ae10"]
                      for p in cases),
           "full_candidate":sum(p["required_sources"]==n and p["full_candidate"]
                                for p in cases)}
             for n in sorted(set(p["required_sources"] for p in cases))}
        for control in ("bm25","v71_fast","rf_cached","linear_cached"):
            if control==m:continue
            summary["paired_vs_"+control]=paired(
                [p["metrics"][m]["ae5"] for p in cases],
                [p["metrics"][control]["ae5"] for p in cases])
        obj["methods"][m]=summary
    for method in models:
        for component in ("predict_cpu_ms","rank_cpu_ms"):
            arr=[p["time_model_cpu_ms"][method][component] for p in cases]
            obj["mean_cost_cpu_ms"][method+"_"+component]=round(float(np.mean(arr)),3)
            obj["p95_cost_cpu_ms"][method+"_"+component]=round(float(np.percentile(arr,95)),3)
    for component in ("base","extra","features","uncached_parity"):
        arr=[p["time_common_cpu_ms"][component] for p in cases]
        obj["mean_cost_cpu_ms"][component]=round(float(np.mean(arr)),3)
        obj["p95_cost_cpu_ms"][component]=round(float(np.percentile(arr,95)),3)
    out.mkdir(parents=True,exist_ok=True)
    (out/"summary.json").write_text(json.dumps(obj,indent=2))
    with (out/"cases.jsonl").open("w") as f:
        for p in cases:f.write(json.dumps(p,ensure_ascii=False)+"\n")
    print("V113_RESULT",json.dumps(obj),flush=True)

def smoke():
    d=[{"_id":"a","title":"Japan Guide",
        "text":"Tokyo is the capital of Japan.",
        "source":"Travel Magazine"}]
    cache,_=doc_cache(d)
    q="Which guide discusses Tokyo Japan?"
    from benchmark_v111 import data_features
    v,_=cached_data_features(q,d,[0],[0],["Tokyo Japan"],[[0]],[0],
                             {"tokyo":2.,"japan":2.,"guide":1.},cache)
    w,_=data_features(q,d,[0],[0],["Tokyo Japan"],[[0]],[0],
                      {"tokyo":2.,"japan":2.,"guide":1.})
    assert np.array_equal(v,w) and v.shape==(1,23)
    print("V11.3 cached feature bit-equivalence smoke PASS")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("smoke","run"))
    p.add_argument("--data",type=pathlib.Path,
                   default=pathlib.Path("data/multihoprag_pinned"))
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v113"))
    a=p.parse_args()
    if a.command=="smoke":return smoke()
    docs,questions,hashes=get(a.data)
    go(docs,questions,hashes,a.out)
if __name__=="__main__":main()
