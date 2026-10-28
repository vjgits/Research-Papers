#!/usr/bin/env python3
"""PGER V9.7-9.9 sequential, feedback-gated experimental suite.

V9.7 tests openly licensed BGE-small dense source discovery rather than
repeating failed lexical entity/graph expansion. V9.8 learns a cheap-first
cost gate *only on development* using gold-independent online features;
V9.9 predicts RETRIEVAL support-chain completeness, NOT factual correctness.
The gate policy is auto-disabled when no development utility advantage is
observed. No paid APIs, oracle online features, semantic entailment or SOTA
claim. Public SAG2 question split (previously inspected by V7.1):
development 0:120, confirmation 120:240.
"""
import argparse,hashlib,json,pathlib,time
from collections import Counter
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss,roc_auc_score
from benchmark_v71_sag2_corpus import download,official_records,SAG2_AUTHOR,RELEASE
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger
from benchmark_v95_controlled import initial,two_actions,metric,paired,unique,cpu_ms
from expansion_v92 import rank_fuse,terms

DEV=(0,120)
CONF=(120,240)
MODEL="BAAI/bge-small-en-v1.5"  # published MIT license; open weights
MODEL_LICENSE="MIT (model card, verify on download)"
TOP_DENSE=80
TOP_BASE=80
STRENGTH=0.85
MODEL_BATCH=64
SEED=20261028
DATASETS=("2wikimultihopqa","musique")
METHODS=("v71_fast","v95_two_query","dense_direct","dense_fused")
GATE_THRESHOLD=.60
MIN_DEVELOPMENT_WINS=2

def dense_index(documents,questions,device="cpu"):
    from sentence_transformers import SentenceTransformer
    import torch
    torch.set_num_threads(2)
    t=time.process_time()
    model=SentenceTransformer(MODEL,device=device)
    model.max_seq_length=256
    loadms=cpu_ms(t)
    t=time.process_time()
    passages=[d["title"]+"\n"+d.get("text","")[:1000] for d in documents]
    D=model.encode(passages,batch_size=MODEL_BATCH,normalize_embeddings=True,
                   convert_to_numpy=True,show_progress_bar=False).astype(np.float32)
    corpusms=cpu_ms(t)
    t=time.process_time()
    Q=model.encode(["Represent this sentence for searching relevant passages: "+q
                    for q in questions],batch_size=MODEL_BATCH,
                   normalize_embeddings=True,convert_to_numpy=True,
                   show_progress_bar=False).astype(np.float32)
    query_encode_ms=cpu_ms(t)
    t=time.process_time()
    similarity=Q @ D.T
    dotms=cpu_ms(t)
    revision=getattr(model[0].auto_model.config,"_commit_hash",None)
    return similarity,{"model":MODEL,"license":MODEL_LICENSE,
         "model_revision":revision,"dimensions":int(D.shape[1]),
         "load_cpu_ms":round(loadms,2),
         "offline_corpus_encoding_cpu_ms":round(corpusms,2),
         "batch_query_encoding_cpu_ms":round(query_encode_ms,2),
         "batch_dot_cpu_ms":round(dotms,2),
         "index_bytes":int(D.nbytes),
         "per_query_batch_amortized_ms":round((query_encode_ms+dotms)/len(questions),3),
         "warning":"Batch-amortized query CPU is NOT interactive single-query p95"}

def top_dense(row,k=TOP_DENSE):
    ix=np.argpartition(-row,min(k,len(row)-1))[:k]
    return [int(i) for i in sorted(ix,key=lambda j:(-float(row[j]),int(j)))]

def fuse(fast,dense):
    scores={}
    for r,i in enumerate(fast[:100]):scores[i]=scores.get(i,0)+1/(25+r)
    for r,i in enumerate(dense[:100]):scores[i]=scores.get(i,0)+STRENGTH/(25+r)
    anchors=unique(fast[:1])
    out=anchors+sorted((i for i in scores if i not in anchors),
            key=lambda i:(-scores[i],i))
    return unique(out+fast+dense)

def online_features(q,docs,fast,bm,dense,graph):
    qt=set(terms(q)); qt=qt or {"_EMPTY_"}
    top=fast[:5]
    qt_covered=set()
    for i in top:
        qt_covered |= set(terms(docs[i]["title"]+" "+docs[i].get("text","")[:700]))
    qlen=len(terms(q))
    coverage=len(qt&qt_covered)/len(qt)
    overlap=len(set(fast[:10])&set(dense[:10]))/10.
    linked=sum(len(graph.adj[i]) for i in fast[:2]) if top else 0
    return [min(60,qlen)/60.,coverage,overlap,min(100,linked)/100.,
            min(3,qlen/12.),float(len(set(fast[:5])&set(bm[:5])))/5.]

def eval_dataset(name,root,out):
    hashes=download(name,root);source_obj,docs,questions=official_records(name,root)
    assert len(docs)==SAG2_AUTHOR[name]["corpus"] and len(questions)==1000
    source=list(source_obj)
    t=time.process_time();methods=SparseMethods(docs);bm_index=cpu_ms(t)
    t=time.process_time();graph=EvidenceLedger(methods);graph_index=cpu_ms(t)
    selected=questions[DEV[0]:CONF[1]]
    sim,dense_cost=dense_index(docs,[r["question"] for r in selected])
    records=[]
    for j,r in enumerate(selected):
        q=r["question"];bm,fast,base_ms=initial(q,methods,graph)
        expansions,actions,extra_ms=two_actions(q,methods,fast)
        t=time.process_time()
        sparse=unique(rank_fuse(fast,bm,expansions,mode="fuse",
                                strength=.4,protect=2,cutoff=150))
        vector=top_dense(sim[j])
        combined=fuse(fast,vector)
        fuse_ms=cpu_ms(t)
        ranked={"v71_fast":fast,"v95_two_query":sparse,
                "dense_direct":vector,"dense_fused":combined}
        # All source discovery/ranking and routing features precede gold access.
        feat=online_features(q,docs,fast,bm,vector,graph)
        pools={"v71_fast":unique(fast[:TOP_BASE]),
               "v95_two_query":unique(fast[:TOP_BASE]+
                                    [i for h in expansions for i in h]),
               "dense_direct":vector,
               "dense_fused":unique(fast[:TOP_BASE]+vector)}
        gold=set(r["gold"])
        assert gold and gold<=set(source)
        as_source=lambda ix:{source[i] for i in ix}
        records.append({
          "id":r["id"],"question":q,"required_sources":len(gold),
          "metrics":{m:metric(rank,source,gold) for m,rank in ranked.items()},
          "candidate_full":{m:int(gold<=as_source(pool))
                            for m,pool in pools.items()},
          "candidate_recall":{m:len(gold&as_source(pool))/len(gold)
                              for m,pool in pools.items()},
          "online_features":feat,
          "search_actions":actions,
          "top10_source_ids":{m:[docs[i]["_id"] for i in rank[:10]]
                              for m,rank in ranked.items()},
          "query_cpu_base_ms":base_ms,
          "query_cpu_sparse_additional_ms":extra_ms,
          "query_cpu_fusion_ms":fuse_ms})
        if (j+1)%40==0:print("PROGRESS",name,j+1,"/",len(selected),flush=True)
    for split,(start,end) in (("development",DEV),("confirmation",CONF)):
        subset=records[start:end]
        summary={"stage":"V9.7","dataset":name,"split":split,
                 "question_indices":[start,end],
                 "n":len(subset),"file_hashes":hashes,
                 "release":RELEASE,"sparse_index_cpu_ms":round(bm_index,2),
                 "graph_index_cpu_ms":round(graph_index,2),
                 "semantic_model_cost":dense_cost,
                 "methods":{}}
        for m in METHODS:
            xs=[r["metrics"][m] for r in subset]
            a={k:round(float(np.mean([x[k] for x in xs])),6)
               for k in ("ae5","ae10","r5","r10")}
            a["full_candidate"]=sum(r["candidate_full"][m] for r in subset)
            a["candidate_recall"]=round(float(np.mean(
                [r["candidate_recall"][m] for r in subset])),6)
            a["by_support_count"]={str(n):{
                "n":sum(r["required_sources"]==n for r in subset),
                "full_candidate":sum(r["required_sources"]==n and
                                      r["candidate_full"][m] for r in subset),
                "ae5":sum(r["required_sources"]==n and
                           r["metrics"][m]["ae5"] for r in subset)}
                for n in sorted(set(r["required_sources"] for r in subset))}
            for ctrl in ("v71_fast","v95_two_query"):
                if m!=ctrl:a["paired_vs_"+ctrl]=paired(
                    [r["metrics"][m]["ae5"] for r in subset],
                    [r["metrics"][ctrl]["ae5"] for r in subset])
            summary["methods"][m]=a
        out.mkdir(parents=True,exist_ok=True)
        prefix=name+"_"+split
        (out/(prefix+"_summary.json")).write_text(json.dumps(summary,indent=2))
        with (out/(prefix+"_cases.jsonl")).open("w") as f:
            for x in subset:f.write(json.dumps(x,ensure_ascii=False)+"\n")
        print("V97_RESULT",name,split,json.dumps(summary["methods"]),flush=True)
    return records,dense_cost

def select_policies(datasets,out):
    # V9.8 controller, per-query gold-independent online features.
    # Train on dev observations across datasets. No dataset ID feature.
    dev=[r for dataset in datasets.values() for r in dataset[:120]]
    conf=[r for dataset in datasets.values() for r in dataset[120:240]]
    target=np.array([r["metrics"]["dense_fused"]["ae5"]-
                     r["metrics"]["v71_fast"]["ae5"] for r in dev])
    w=int(sum(target>0));l=int(sum(target<0))
    X=np.asarray([r["online_features"] for r in dev])
    active=False;reason=""
    if w<MIN_DEVELOPMENT_WINS or w<=l:
        reason=f"Development dense-fused gains insufficient (wins={w}, losses={l}); no routing permitted"
        model=None
    else:
        # Only winner-versus-loser sign cases train; ties never create a
        # spurious model advantage. Fixed C and threshold, no tuning grid.
        chosen=target!=0
        y=(target[chosen]>0).astype(int)
        if len(set(y))<2:
            reason="Only one class among decision-changing cases"
            model=None
        else:
            model=LogisticRegression(C=1.,max_iter=500,random_state=SEED)
            model.fit(X[chosen],y)
            active=True
            reason=f"Frozen classifier trained on {int(chosen.sum())} differing development cases"
    report={"stage":"V9.8","active":active,"reason":reason,
            "development_wins_dense_fused":w,
            "development_losses_dense_fused":l,
            "positive_probability_threshold":GATE_THRESHOLD,
            "gold_in_online_features":False,
            "dataset_id_feature":False,
            "hypothesis":"Can selective semantic retrieval beat fast-only under actual extra compute?"}
    for split,subset in (("development",dev),("confirmation",conf)):
        actual=[];baseline=[];dense=[];cost_flags=[]
        for r in subset:
            prob=(float(model.predict_proba([r["online_features"]])[0,1])
                  if model is not None else 0.)
            triggered=active and prob>=GATE_THRESHOLD
            actual.append(r["metrics"]["dense_fused" if triggered else "v71_fast"]["ae5"])
            baseline.append(r["metrics"]["v71_fast"]["ae5"])
            dense.append(r["metrics"]["dense_fused"]["ae5"])
            cost_flags.append(int(triggered))
            r["v98_routed"]={"triggered":bool(triggered),
                             "predicted_improvement":round(prob,6),
                             "ae5":actual[-1]}
        report[split]={"n":len(subset),"mean_ae5":round(float(np.mean(actual)),6),
            "fast_ae5":round(float(np.mean(baseline)),6),
            "always_dense_fused_ae5":round(float(np.mean(dense)),6),
            "routed_count":sum(cost_flags),"routed_fraction":round(float(np.mean(cost_flags)),6),
            "paired_vs_fast":paired(actual,baseline)}
        print("V98_RESULT",split,json.dumps(report[split]),flush=True)
    (out/"v98_gate_summary.json").write_text(json.dumps(report,indent=2))
    return dev,conf,report

def reliability_proxy(dev,conf,out):
    # V9.9 is *not* answer truth calibration. Labels are annotated
    # supporting-passage completeness @5, available only offline to train.
    X=np.asarray([r["online_features"] for r in dev])
    Y=np.asarray([r["v98_routed"]["ae5"] for r in dev],dtype=int)
    if len(np.unique(Y))<2:
        obj={"stage":"V9.9","status":"SKIPPED",
             "reason":"One class in development cannot fit supervised reliability proxy"}
        (out/"v99_reliability_proxy.json").write_text(json.dumps(obj,indent=2))
        return obj
    model=LogisticRegression(C=1.0,max_iter=500,random_state=SEED)
    model.fit(X,Y)
    XX=np.asarray([r["online_features"] for r in conf])
    yy=np.asarray([r["v98_routed"]["ae5"] for r in conf],dtype=int)
    probs=model.predict_proba(XX)[:,1]
    constant=float(Y.mean())
    bins=np.linspace(0,1,6)
    ece=0
    for lo,hi in zip(bins[:-1],bins[1:]):
        mask=(probs>=lo)&(probs<=hi if hi==1 else probs<hi)
        if any(mask):
            ece+=np.mean(mask)*abs(float(np.mean(yy[mask]))-
                                  float(np.mean(probs[mask])))
    selections={}
    for frac in (.4,.6,.8,1.):
        k=max(1,int(np.ceil(len(probs)*frac)))
        chosen=np.argsort(-probs)[:k]
        selections[str(frac)]={"n_answered_proxy":int(k),
              "coverage":round(float(k/len(probs)),4),
              "completeness_precision":round(float(np.mean(yy[chosen])),6)}
    obj={"stage":"V9.9","status":"EVALUATED",
         "n_development":len(dev),"n_confirmation":len(conf),
         "target":"complete annotated gold documents in Top5 (NOT factual answer correctness)",
         "brier":round(float(brier_score_loss(yy,probs)),6),
         "constant_development_base_rate_brier":round(float(
             brier_score_loss(yy,np.full(len(yy),constant))),6),
         "ece_5_bins":round(float(ece),6),
         "roc_auc":round(float(roc_auc_score(yy,probs)),6) if len(set(yy))>1 else None,
         "selective_precision_vs_coverage":selections,
         "limitations":["No generated answers, relation entailment or validated abstention",
                        "This model estimates a retrieval-success proxy only",
                        "Public questions repeatedly inspected by earlier work"]}
    (out/"v99_reliability_proxy.json").write_text(json.dumps(obj,indent=2))
    print("V99_RESULT",json.dumps(obj),flush=True)
    return obj

def smoke():
    a=fuse([0,1,2],[3,1,4])
    assert a[0]==0 and len(a)==len(set(a))
    print("V9.7–9.9 smoke PASS")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("smoke","run"))
    p.add_argument("--data",type=pathlib.Path,default=pathlib.Path("data/sag2_official"))
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v97-v99"))
    a=p.parse_args()
    if a.command=="smoke":return smoke()
    experiment={}
    for name in DATASETS:
        experiment[name],cost=eval_dataset(name,a.data,a.out)
    dev,conf,gate=select_policies(experiment,a.out)
    reliability_proxy(dev,conf,a.out)
    print("V9.7-9.9 STAGED EVALUATION COMPLETE",flush=True)

if __name__=="__main__":
    main()
