#!/usr/bin/env python3
"""PGER V11.1 development-only learned candidate reranker, external MultiHopRAG.

This is a controlled prior-art ranking component experiment, not a novel
relationship verifier, end-to-end answer truth checker or SOTA claim.

HARD RULES:
- question source identities/gold only label development model examples.
- confirmation (offsets 800:1200) identities accessed solely AFTER all
  predictions are frozen for that question.
- same frozen 120-document candidate pool for all rerank controls.
- report strict 2/3/4 source chain @5/@10, paired CI and CPU/model cost.
- source metadata is a valid publicly retrievable document attribute.
- corpus/questions PUBLIC and previously inspected in V10.1/V11, not sealed.
"""
import argparse,collections,hashlib,json,pathlib,re,time
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from benchmark_v101_multihoprag import get,make_corpus,map_gold
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger
from benchmark_v95_controlled import initial,two_actions,paired,unique,cpu_ms
from benchmark_v11 import facet_queries,candidate_pool,fusion
from expansion_v92 import terms

SEED=20261028
TRAIN=(0,400)
CONF=(800,1200)
BUDGET=120
MAX_DOC_CHARS=1800
FACET_CALL_MAX=2
N_ESTIMATORS=120
MIN_LEAF=5
RANKERS=("bm25","v71_fast","facet_fusion",
         "learned_pointwise","learned_anchor","learned_facet_diverse")
RX_YEAR=re.compile(r"\b(?:19|20)\d{2}\b")

def tokenize(t):
    return set(terms(t))
def weight_overlap(a,b,idf):
    return sum(idf.get(t,0.) for t in a & b)/max(
        1e-8,sum(idf.get(t,0.) for t in a))
def data_features(q,docs,rank_bm,rank_fast,facets,facet_hits,pool,idf):
    """Gold-independent numeric per-query/candidate features and facet matrix."""
    qwords=tokenize(q);year=set(RX_YEAR.findall(q))
    featwords=[tokenize(s) for s in facets]
    qlow=q.casefold()
    rb={d:r for r,d in enumerate(rank_bm)}
    rf={d:r for r,d in enumerate(rank_fast)}
    fr=[{d:r for r,d in enumerate(h)} for h in facet_hits]
    X=[];F=[]
    for d in pool:
        item=docs[d]
        title=item["title"]
        body=item.get("text","")[:MAX_DOC_CHARS]
        source=str(item.get("source",""))
        tx=tokenize(title)
        bx=tokenize(body)
        sx=tokenize(source)
        yrs=set(RX_YEAR.findall(title+" "+body))
        facet_coverage=[weight_overlap(x,(tx|bx),idf) for x in featwords]
        facet_ranks=[ranks.get(d,100) for ranks in fr]
        source_norm=source.strip().casefold()
        exact_source=float(len(source_norm)>=4 and source_norm in qlow)
        first_source_word=float(bool(sx) and bool(sx & qwords))
        title_phrase=float(len(title)>=7 and title.casefold() in qlow)
        bmr=rb.get(d,100)
        far=rf.get(d,100)
        row=[
         min(1.,len(qwords)/28),min(1.,len(tx)/14),
         1/(1+bmr),1/(1+far),
         float(d in rank_fast[:5]),float(d in rank_bm[:5]),
         weight_overlap(qwords,tx,idf),
         weight_overlap(qwords,bx,idf),
         weight_overlap(qwords,tx|bx,idf),
         sum(1 for x in qwords if x in tx)/max(1,len(qwords)),
         sum(1 for x in qwords if x in bx)/max(1,len(qwords)),
         exact_source,first_source_word,title_phrase,
         len(year & yrs)/max(1,len(year)),
         max(facet_coverage) if facet_coverage else 0,
         sum(facet_coverage)/max(1,len(facet_coverage)),
         min(1.,sum(facet_coverage)/max(1,len(facet_coverage))),
         sum(1 for f in facet_coverage if f>=.30)/max(1,len(facet_coverage)),
         min((1/(1+r) for r in facet_ranks),default=0.),
         sum(1/(1+r) for r in facet_ranks)/max(1,len(facet_ranks)),
         float(len(facets)), min(1.,len(body)/MAX_DOC_CHARS)
        ]
        X.append(row);F.append(facet_coverage)
    return np.asarray(X,dtype=np.float32),np.asarray(F,dtype=np.float32)

def collect_item(q,sm,graph,docs,include_heldout_label=False):
    t=time.process_time()
    bm,fast,base_cpu=initial(q,sm,graph)
    bmraw=sm.index.search(q,"bm25",100)
    bm=unique([i for i,s in bmraw] or bm)
    facets=facet_queries(q)[:FACET_CALL_MAX]
    t2=time.process_time()
    hits=[[i for i,s in sm.index.search(f,"bm25",50)] for f in facets]
    extra_cpu=cpu_ms(t2)
    rank=fusion(fast,bm,hits)
    pool=candidate_pool(fast,bm,hits)
    # Keep exact SAME candidate universe for each learned reranking arm.
    t3=time.process_time()
    X,F=data_features(q,docs,bm,fast,facets,hits,pool,sm.index.idfs)
    feature_cpu=cpu_ms(t3)
    return {
      "bm":bm,"fast":fast,"fusion":rank,"pool":pool,
      "X":X,"facets":facets,"facet_matrix":F,
      "time_cpu":{"base":base_cpu,"extra":extra_cpu,"feature":feature_cpu}
    }

def reorder(pred,base,pool,diverse_facet=None,anchor=False):
    order={d:r for r,d in enumerate(base)}
    scores={i:float(p) for i,p in zip(pool,pred)}
    remaining=list(pool)
    result=[]
    if anchor and base and base[0] in remaining:
        result.append(base[0]);remaining.remove(base[0])
    if diverse_facet is None or diverse_facet.shape[1]<2:
        remaining.sort(key=lambda d:(-scores[d],order.get(d,999),d))
        return unique(result+remaining+base)
    idx={d:j for j,d in enumerate(pool)}
    covered=np.zeros(diverse_facet.shape[1],dtype=float)
    # Explicitly cheap balanced clause selection without gold.
    while len(result)<10 and remaining:
        def util(d):
            vals=diverse_facet[idx[d]]
            marginal=float(np.mean(np.maximum(0, vals-covered)))
            return .82*scores[d]+.18*marginal
        choice=max(remaining,key=lambda d:(util(d),-order.get(d,999),-d))
        covered=np.maximum(covered,diverse_facet[idx[choice]])
        result.append(choice);remaining.remove(choice)
    return unique(result+sorted(remaining,key=lambda d:(-scores[d],order.get(d,999),d))+base)

def score(rank,gold):
    return {"ae5":int(gold<=set(rank[:5])),
            "ae10":int(gold<=set(rank[:10])),
            "r5":len(gold&set(rank[:5]))/len(gold),
            "r10":len(gold&set(rank[:10]))/len(gold)}

def run(rawdocs,rawquestions,hashes,out):
    docs=make_corpus(rawdocs)
    t=time.process_time();sm=SparseMethods(docs);indexms=cpu_ms(t)
    t=time.process_time();graph=EvidenceLedger(sm);graphms=cpu_ms(t)
    # Training labels in the development cohort ONLY, strict fixed protocol.
    Xtrain=[];ytrain=[];dev_n=0;dev_skip=collections.Counter()
    for row in rawquestions[TRAIN[0]:TRAIN[1]]:
        q=str(row.get("query",row.get("question",""))).strip()
        if not q:dev_skip["empty_question"]+=1;continue
        gold,flag,n=map_gold(row,docs)
        if n<2 or len(gold)!=n or "unresolved_evidence_identity" in flag:
            dev_skip["unresolved_gold_identity"]+=1;continue
        item=collect_item(q,sm,graph,docs)
        Xtrain.append(item["X"])
        ytrain.extend(int(i in gold) for i in item["pool"])
        dev_n+=1
        if dev_n%100==0:print("V111_TRAIN_DATA",dev_n,flush=True)
    assert dev_n>=200 and sum(ytrain)>=100
    Xtrain=np.vstack(Xtrain);ytrain=np.asarray(ytrain,np.int32)
    t=time.process_time()
    model=RandomForestClassifier(
       n_estimators=N_ESTIMATORS,max_depth=10,min_samples_leaf=MIN_LEAF,
       class_weight="balanced_subsample",n_jobs=2,random_state=SEED)
    model.fit(Xtrain,ytrain)
    fitms=cpu_ms(t)
    cases=[];confirm_skip=collections.Counter()
    for row in rawquestions[CONF[0]:CONF[1]]:
        q=str(row.get("query",row.get("question",""))).strip()
        if not q:confirm_skip["empty_question"]+=1;continue
        item=collect_item(q,sm,graph,docs)
        t=time.process_time()
        pred=model.predict_proba(item["X"])[:,1]
        probs_cpu=cpu_ms(t)
        t=time.process_time()
        learned=reorder(pred,item["fusion"],item["pool"])
        anchored=reorder(pred,item["fusion"],item["pool"],anchor=True)
        diversified=reorder(pred,item["fusion"],item["pool"],item["facet_matrix"])
        rank_cpu=cpu_ms(t)
        ranks={"bm25":item["bm"],"v71_fast":item["fast"],
               "facet_fusion":item["fusion"],
               "learned_pointwise":learned,
               "learned_anchor":anchored,
               "learned_facet_diverse":diversified}
        # Held-out source labels inspected ONLY after predictions/rankings made.
        gold,flag,n=map_gold(row,docs)
        if n<2 or len(gold)!=n or "unresolved_evidence_identity" in flag:
            confirm_skip["unresolved_gold_identity"]+=1;continue
        cases.append({
           "id":str(row.get("id",row.get("_id",""))),
           "question":q,"required_sources":len(gold),
           "n_candidate_docs":len(item["pool"]),
           "full_candidate":int(gold<=set(item["pool"])),
           "candidate_recall":len(gold&set(item["pool"]))/len(gold),
           "metric":{m:score(rank,gold) for m,rank in ranks.items()},
           "top10":{m:[docs[d]["_id"] for d in rank[:10]]
                    for m,rank in ranks.items()},
           "cpu_ms":{"base":item["time_cpu"]["base"],
                      "extra_search":item["time_cpu"]["extra"],
                      "feature":item["time_cpu"]["feature"],
                      "prediction":probs_cpu,"rerank":rank_cpu}
        })
        if len(cases)%50==0:print("V111_CONFIRM",len(cases),flush=True)
    assert len(cases)>=220
    result={"stage":"V11.1","dataset":"MultiHop-RAG article IDs",
       "corpus_docs":len(docs),"source_hashes":hashes,
       "train_offsets":list(TRAIN),"confirmation_offsets":list(CONF),
       "n_train_questions":dev_n,"n_train_pairs":len(ytrain),
       "positive_train_pairs":int(sum(ytrain)),
       "train_skipped":dict(dev_skip),
       "confirmation_scored":len(cases),
       "confirmation_skipped":dict(confirm_skip),
       "index_cpu_ms":{"bm25":indexms,"graph":graphms},
       "model":{"algorithm":"RandomForestClassifier",
                "n_estimators":N_ESTIMATORS,"max_depth":10,
                "min_leaf":MIN_LEAF,"class_weight":"balanced_subsample",
                "fit_cpu_ms":fitms,"seed":SEED,
                "model_inference_has_no_gold":True,
                "feature_count":int(Xtrain.shape[1])},
       "methods":{},
       "limitations":["Supervised classifier trained with labeled gold source IDs on PUBLIC development",
         "Public confirmation questions were already inspected in V10.1 and V11",
         "Potential article/source overlap between training and confirmation",
         "Sentence sources, titles and publishers are not formal entailment",
         "Document candidate pool can be 120/609 (~20 percent corpus)",
         "No answer generation, factual validity or 5/6/8 logical-hop verification",
         "Process CPU cost excludes indexing/deployment and full p95 wall",
         "No claim of novelty or SOTA"]
    }
    for m in RANKERS:
        stats={key:round(float(np.mean([p["metric"][m][key] for p in cases])),6)
               for key in ("ae5","ae10","r5","r10")}
        stats["by_support_count"]={str(n):{
          "n":sum(p["required_sources"]==n for p in cases),
          "ae5":sum(p["required_sources"]==n and p["metric"][m]["ae5"] for p in cases),
          "ae10":sum(p["required_sources"]==n and p["metric"][m]["ae10"] for p in cases),
          "full_candidate":sum(p["required_sources"]==n and p["full_candidate"] for p in cases)}
           for n in sorted(set(p["required_sources"] for p in cases))}
        for base in ("bm25","v71_fast","facet_fusion","learned_pointwise"):
            if base==m:continue
            stats["paired_vs_"+base]=paired(
                 [p["metric"][m]["ae5"] for p in cases],
                 [p["metric"][base]["ae5"] for p in cases])
        result["methods"][m]=stats
    for key in ("base","extra_search","feature","prediction","rerank"):
        result.setdefault("mean_cpu_ms",{})[key]=round(float(np.mean(
            [r["cpu_ms"][key] for r in cases])),3)
        result.setdefault("p95_cpu_ms",{})[key]=round(float(np.percentile(
            [r["cpu_ms"][key] for r in cases],95)),3)
    out.mkdir(parents=True,exist_ok=True)
    (out/"summary.json").write_text(json.dumps(result,indent=2))
    with (out/"cases.jsonl").open("w") as f:
        for p in cases:f.write(json.dumps(p,ensure_ascii=False)+"\n")
    print("V111_RESULT",json.dumps(result),flush=True)

def smoke():
    docs=[{"_id":"a","title":"Tokyo Guide","text":"Tokyo is the capital of Japan.",
           "source":"Travel Magazine"}]
    data=data_features("Which guide discusses Tokyo Japan?",docs,[0],[0],
          ["Tokyo Japan"],[[0]],[0],{"tokyo":2.,"japan":2.,"guide":1.})
    assert data[0].shape==(1,23)
    pred=np.array([.5]);assert reorder(pred,[0],[0])==[0]
    print("V11.1 supervised feature and ranker smoke PASS")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("smoke","run"))
    p.add_argument("--data",type=pathlib.Path,
                   default=pathlib.Path("data/multihoprag_pinned"))
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v111"))
    a=p.parse_args()
    if a.command=="smoke":return smoke()
    rawdocs,questions,hashes=get(a.data)
    run(rawdocs,questions,hashes,a.out)
if __name__=="__main__":main()
