#!/usr/bin/env python3
"""PGER V13A: learn *joint necessity of source pairs* on training questions only.

Evidence co-necessity is NOT logical entailment or a validated relationship.
This experiments with listwise assembly to address the prior 52/54 gold
candidate recall but 3/54 AE@5 on an independent question cohort.
Preserve PGER's original boosted passage relevance, provenance IDs,
retrieval budget, and trace of possible incomplete-proof links.

Public MultiHop-RAG news corpus (609 sources); training questions [0,400),
previously unused test [2400,2556), same 120 candidate budget, no extra
searches for any arm. Evaluation gold source URLs used only after all ranks.
"""
import argparse,collections,hashlib,json,pathlib,time
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from benchmark_v101_multihoprag import get,make_corpus,map_gold
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger
from benchmark_v95_controlled import initial,paired,cpu_ms,unique
from benchmark_v113 import doc_cache,prepare
from benchmark_v111 import reorder,score,SEED
from expansion_v92 import terms

TRAIN=(0,400)
TEST=(2400,2556)
K=5
POOL=120
PAIR_BASE_TOP=56
SCORE_SAMPLE=64
SEED_PAIR=.11
STRONG_PAIR=.23
NEG_PER_QUESTION=90
PAIR_FEATURES=12
METHODS=("bm25","v71_fast","boosted_independent",
         "simple_text_diversity","learned_pair_weak","learned_pair_strong")

def words(t):
    return set(terms(t))
def doc_signatures(docs):
    signatures=[]
    for d in docs:
        title=words(d["title"])
        body=words(d.get("text","")[:1500])
        source=words(str(d.get("source","")))
        signatures.append({"title":title,"body":body,"all":title|body,
                           "source":source,"url":d.get("url","")})
    return signatures

def pair_features(a,b,learned,sign,qset,fast_rank):
    A,B=sign[a],sign[b]
    ta,tb=A["title"],B["title"]
    aa,bb=A["all"],B["all"]
    inter=len(aa&bb)
    uni=max(1,len(aa|bb))
    qa=aa&qset
    qb=bb&qset
    ra=fast_rank.get(a,200)
    rb=fast_rank.get(b,200)
    return [
      min(learned.get(a,0),learned.get(b,0)),
      max(learned.get(a,0),learned.get(b,0)),
      learned.get(a,0)*learned.get(b,0),
      inter/uni,
      len(ta&bb)/max(1,len(ta)),
      len(tb&aa)/max(1,len(tb)),
      len(ta&tb)/max(1,len(ta|tb)),
      len(qa&qb)/max(1,len(qset)),
      len(qa^qb)/max(1,len(qset)),
      len((qa|qb))/max(1,len(qset)),
      1/(1+min(ra,rb)),
      float(bool(A["source"]&B["source"]))
    ]

def fit_passage(X,Y):
    model=HistGradientBoostingClassifier(
      max_iter=100,max_leaf_nodes=15,learning_rate=.08,
      l2_regularization=1.0,class_weight="balanced",random_state=SEED)
    model.fit(X,Y)
    return model

def training_pairs(train_records,model,sign,docs):
    X=[];Y=[];rng=np.random.default_rng(SEED)
    for rec in train_records:
        q=rec["q"];b=rec["b"];gold=rec["gold"]
        prob=model.predict_proba(b["X"])[:,1]
        pmap={int(d):float(p) for d,p in zip(b["pool"],prob)}
        candidate=unique(
          reorder(prob,b["fast"],b["pool"])[:PAIR_BASE_TOP] +
          [d for d in b["pool"] if d in gold])
        rank={d:i for i,d in enumerate(b["fast"])}
        qset=words(q)
        positives=[];negatives=[]
        for x,i in enumerate(candidate):
            for j in candidate[x+1:]:
                f=pair_features(i,j,pmap,sign,qset,rank)
                if i in gold and j in gold:positives.append(f)
                else:negatives.append(f)
        if positives:
            X.extend(positives)
            Y.extend([1]*len(positives))
        if negatives:
            idx=rng.choice(len(negatives),
                 size=min(NEG_PER_QUESTION,len(negatives)),
                 replace=False)
            X.extend(negatives[z] for z in idx)
            Y.extend([0]*len(idx))
    outx=np.asarray(X,dtype=np.float32)
    outy=np.asarray(Y,dtype=int)
    assert outx.shape[1]==PAIR_FEATURES and 0<sum(outy)<len(outy)
    t=time.process_time()
    clf=make_pipeline(StandardScaler(),
          LogisticRegression(C=1.0,class_weight="balanced",
            max_iter=1000,solver="liblinear",random_state=SEED))
    clf.fit(outx,outy)
    return clf,{"n_training_pairs":len(outy),
                "n_positive_pairs":int(sum(outy)),
                "n_negative_pairs":int(len(outy)-sum(outy)),
                "fit_cpu_ms":cpu_ms(t)}

def prep_pair_scores(q,b,base,prob,sign,clf):
    t=time.process_time()
    pmap={int(d):float(p) for d,p in zip(b["pool"],prob)}
    candidates=unique(base[:PAIR_BASE_TOP])
    fr={d:i for i,d in enumerate(b["fast"])}
    qset=words(q)
    pairs=[];features=[]
    for n,i in enumerate(candidates):
        for j in candidates[n+1:]:
            pairs.append((i,j))
            features.append(pair_features(i,j,pmap,sign,qset,fr))
    val=clf.predict_proba(np.asarray(features,dtype=np.float32))[:,1]
    probs={}
    for (i,j),v in zip(pairs,val):
        probs[(i,j)]=float(v)
    return probs,candidates,pmap,cpu_ms(t)

def joint_select(base,pmap,pair,candidates,weight,sign,lexical_only=False):
    t=time.process_time()
    original={d:i for i,d in enumerate(base)}
    chosen=[base[0]]
    remaining=[i for i in candidates if i not in chosen]
    trace=[]
    while len(chosen)<10 and remaining:
        def joint(d):
            if lexical_only:
                # Transparent non-learned text diversity control.
                sim=max((len(sign[d]["all"]&sign[s]["all"])/
                    max(1,len(sign[d]["all"]|sign[s]["all"])))
                    for s in chosen)
                return pmap.get(d,0)+weight*(1-sim)
            links=[pair.get((min(d,s),max(d,s)),0) for s in chosen]
            return (1-weight)*pmap.get(d,0) + weight*(
                   float(np.mean(links)) if links else 0.)
        nxt=max(remaining,key=lambda d:(joint(d),-original.get(d,1000),-d))
        links=[float(pair.get((min(nxt,s),max(nxt,s)),0)) for s in chosen]
        trace.append({"candidate_index":int(nxt),
              "pair_co_necessity_mean":round(float(np.mean(links)),5),
              "relation_entailment_verified":False})
        chosen.append(nxt);remaining.remove(nxt)
    chosen.extend(d for d in base if d not in set(chosen))
    return unique(chosen),trace,cpu_ms(t)

def run(rawdocs,questions,hashes,out):
    docs=make_corpus(rawdocs)
    sign=doc_signatures(docs)
    cache,cachems=doc_cache(docs)
    t=time.process_time();sm=SparseMethods(docs);bmms=cpu_ms(t)
    t=time.process_time();graph=EvidenceLedger(sm);graphms=cpu_ms(t)
    Xs=[];Ys=[];dev=[];skips=collections.Counter()
    train_sources=set()
    for r in questions[TRAIN[0]:TRAIN[1]]:
        q=str(r.get("query",r.get("question",""))).strip()
        if not q:skips["missing_q"]+=1;continue
        gold,flags,n=map_gold(r,docs)
        if n<2 or len(gold)!=n or "unresolved_evidence_identity" in flags:
            skips["unresolved_gold"]+=1;continue
        b=prepare(q,sm,graph,docs,cache)
        Xs.append(b["X"]);Ys.extend(int(d in gold) for d in b["pool"])
        dev.append({"q":q,"gold":gold,"b":b})
        train_sources|=gold
    X=np.vstack(Xs);Y=np.asarray(Ys,dtype=int)
    assert len(dev)>=250 and X.shape[1]==23
    t=time.process_time();model=fit_passage(X,Y);base_fit=cpu_ms(t)
    pair_model,pair_fit=training_pairs(dev,model,sign,docs)
    del dev
    cases=[];excluded=collections.Counter()
    for row in questions[TEST[0]:TEST[1]]:
        q=str(row.get("query",row.get("question",""))).strip()
        if not q:excluded["missing_q"]+=1;continue
        b=prepare(q,sm,graph,docs,cache)
        t=time.process_time()
        probs=model.predict_proba(b["X"])[:,1]
        base_order=reorder(probs,b["fast"],b["pool"])
        infer_ms=cpu_ms(t)
        pair_scores,candidates,pmap,pair_ms=prep_pair_scores(
            q,b,base_order,probs,sign,pair_model)
        div,divtrace,divms=joint_select(
            base_order,pmap,pair_scores,candidates,.11,sign,lexical_only=True)
        weak,weaktrace,weakms=joint_select(
            base_order,pmap,pair_scores,candidates,SEED_PAIR,sign)
        strong,strongtrace,strongms=joint_select(
            base_order,pmap,pair_scores,candidates,STRONG_PAIR,sign)
        ranks={"bm25":b["bm"],"v71_fast":b["fast"],
               "boosted_independent":base_order,
               "simple_text_diversity":div,
               "learned_pair_weak":weak,"learned_pair_strong":strong}
        # Offline inspection only after methods and traces complete.
        gold,flags,n=map_gold(row,docs)
        if n<2 or len(gold)!=n or "unresolved_evidence_identity" in flags:
            excluded["unresolved_gold"]+=1;continue
        full_seen=gold.isdisjoint(train_sources)
        cases.append({
          "question":q,"required_sources":len(gold),
          "gold_disjoint_from_training_gold_sources":bool(full_seen),
          "full_gold_in_120_pool":int(gold<=set(b["pool"])),
          "full_gold_in_top56_pool":int(gold<=set(candidates)),
          "metrics":{k:score(v,gold) for k,v in ranks.items()},
          "top10_source_ids":{k:[docs[i]["_id"] for i in v[:10]]
                              for k,v in ranks.items()},
          "trace":{"weak":weaktrace,"strong":strongtrace,
                   "diversity":divtrace},
          "postindex_cpu_ms":{"retrieval":b["time"]["base"],
                     "extra_search":b["time"]["extra"],
                     "features":b["time"]["features"],
                     "boosted_prediction":infer_ms,
                     "pair_predict_and_features":pair_ms,
                     "joint_weak":weakms,"joint_strong":strongms,
                     "diversity":divms}
        })
        if len(cases)%50==0:print("V13_PROGRESS",len(cases),flush=True)
    assert len(cases)>=80
    out.mkdir(parents=True,exist_ok=True)
    summary={"stage":"V13A_pair_co_necessity_not_entailment",
        "source_dataset_sha256":hashes,
        "corpus_articles":len(docs),
        "train_offsets":list(TRAIN),"test_offsets":list(TEST),
        "train_questions":len(Xs),"train_pairs":len(Y),
        "n_evaluated":len(cases),"excluded":dict(excluded),
        "n_source_disjoint_gold":sum(c["gold_disjoint_from_training_gold_sources"] for c in cases),
        "train_positive_sources_count":len(train_sources),
        "pair_model_training":pair_fit,
        "base_fit_cpu_ms":base_fit,
        "offline_cpu_ms":{"cache":cachems,"bm25":bmms,"graph":graphms},
        "methods":{},"cpu_mean_ms":{},"cpu_p95_ms":{},
        "limitations":[
          "Pair classifier targets co-necessity (both gold source IDs) not factual directional entailment",
          "All docs same public news corpus, source-disjoint gold subset is small and may still share article contexts",
          "PGER prior-stage question-cohort exposure only excludes this new question range",
          "No use of test gold source identities at inference",
          "Only evidence document identities not answer correctness or calibrated abstention",
          "True 4/5/6/8 logical-hop dependency graph not independently labeled",
          "Pair score and truth verification must not be confused",
          "Postindex CPU process time not end-to-end production latency"]}
    for m in METHODS:
        stats={key:round(float(np.mean([c["metrics"][m][key]
                   for c in cases])),6) for key in ("ae5","ae10","r5","r10")}
        stats["support_groups"]={str(n):{"n":sum(c["required_sources"]==n for c in cases),
                 "ae5":sum(c["required_sources"]==n and c["metrics"][m]["ae5"] for c in cases),
                 "ae10":sum(c["required_sources"]==n and c["metrics"][m]["ae10"] for c in cases),
                 "pool_full":sum(c["required_sources"]==n and c["full_gold_in_120_pool"] for c in cases),
                 "top56_full":sum(c["required_sources"]==n and c["full_gold_in_top56_pool"] for c in cases)}
              for n in sorted(set(c["required_sources"] for c in cases))}
        for baseline in ("v71_fast","boosted_independent","simple_text_diversity"):
            if m!=baseline:stats["vs_"+baseline]=paired(
                [c["metrics"][m]["ae5"] for c in cases],
                [c["metrics"][baseline]["ae5"] for c in cases])
        sd=[c for c in cases if c["gold_disjoint_from_training_gold_sources"]]
        if sd:stats["source_gold_disjoint"]={"n":len(sd),
               "ae5":sum(c["metrics"][m]["ae5"] for c in sd)}
        summary["methods"][m]=stats
    for component in ("retrieval","extra_search","features","boosted_prediction",
                      "pair_predict_and_features","joint_weak","joint_strong","diversity"):
        scores=[c["postindex_cpu_ms"][component] for c in cases]
        summary["cpu_mean_ms"][component]=round(float(np.mean(scores)),3)
        summary["cpu_p95_ms"][component]=round(float(np.percentile(scores,95)),3)
    (out/"summary.json").write_text(json.dumps(summary,indent=2))
    with (out/"cases.jsonl").open("w") as f:
        for c in cases:f.write(json.dumps(c,ensure_ascii=False)+"\n")
    print("V13A_RESULT",json.dumps(summary),flush=True)

def smoke():
    s=[{"title":set("ab"),"body":set("bc"),"all":set("abc"),"source":set("s")},
       {"title":set("bd"),"body":set("dc"),"all":set("bdc"),"source":set("s")}]
    f=pair_features(0,1,{0:.7,1:.8},s,{"a","b","c","d"},{0:0,1:1})
    assert len(f)==PAIR_FEATURES
    d,t,m=joint_select([0,1],{0:.7,1:.8},{(0,1):.8},[0,1],.11,s)
    assert d==[0,1] and m>=0
    print("V13A co-necessity listwise smoke PASS")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("smoke","run"))
    p.add_argument("--data",type=pathlib.Path,default=pathlib.Path("data/multihoprag_pinned"))
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v13a"))
    a=p.parse_args()
    if a.command=="smoke":return smoke()
    docs,questions,hashes=get(a.data)
    assert len(questions)>=TEST[1]
    run(docs,questions,hashes,a.out)
if __name__=="__main__":main()
