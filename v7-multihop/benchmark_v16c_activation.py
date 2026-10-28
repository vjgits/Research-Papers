#!/usr/bin/env python3
"""PGER V16C: source-archive activation from fixed 4-round fact retrieval.

Hypothesis: V16B's durable source archive contains significantly more
complete chains than Top120 active context (102/513 vs 70/513). A cheap
development-trained source-necessity activation gate may recover some of
that lost set without extra searches. PGER proof status ALWAYS unverified
without external source-edge reviewer.

TRAIN EntailmentBank published task1 train questions 400..799 (already
inspected in V16A; explicitly exploratory development). SCORE distinct
questions 800..1312 (inspected in V16B; not a sealed/new benchmark).
No test labels used by model, ranking or query selection. Dataset is public.
Compare unchanged H4 RRF, H1 cheap gate, two fixed learned activation
variants and archive oracle upper bound. Record source/provenance and CPU.
"""
import argparse,collections,hashlib,json,pathlib,time
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from benchmark_v16_frontier import FactLinkIndex,run_arm,POOL_LIMIT,digest
from benchmark_v14c_prooftree import source_corpus,reference
from audit_v14_entailmentbank import get
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger
from benchmark_v95_controlled import paired,cpu_ms,unique
from expansion_v92 import terms
from benchmark_v111 import SEED
from pger_v13_proof_gate import Claim,decide,Status

DEV=(400,800)
CONF=(800,1313)
FEATURES=17
METHODS=("initial","cheap_h1","unmodified_h4",
         "learned_archive","learned_archive_anchor")
K=(5,10,20)

def qvec(q):return set(terms(q))
def dfidf(word,idf):return max(0.0,float(idf.get(word,0)))
def numeric_features(q,docs,root,h4,idf):
    qterms=qvec(q)
    root_rank={i:j for j,i in enumerate(root["rank"])}
    late_rank={i:j for j,i in enumerate(h4["rank"])}
    first_hit={};hit_positions=collections.defaultdict(list)
    for turn,hits in enumerate(h4["hitlists"]):
        for pos,i in enumerate(hits):
            if i not in first_hit:first_hit[i]=turn
            hit_positions[i].append(pos)
    seen_query_seeds={x["source_id"] for x in h4["actions"]}
    baseline_docs=root["rank"][:5]
    baseline_terms=set()
    for i in baseline_docs:
        baseline_terms.update(terms(docs[i]["text"]))
    qnorm=sum(dfidf(w,idf) for w in qterms)
    qnorm=max(1e-9,qnorm)
    rows=[];indices=list(h4["archive"])
    for i in indices:
        d=docs[i];words=set(terms(d["text"]))
        r0=root_rank.get(i,9999);r4=late_rank.get(i,9999)
        matches=hit_positions.get(i,[])
        common=words&qterms
        overlap=sum(dfidf(w,idf) for w in common)/qnorm
        newer=words-qterms
        rarity=sum(dfidf(w,idf) for w in newer)/max(1,len(newer))
        max_rarity=max([dfidf(w,idf) for w in newer],default=0)
        full_len=max(1,len(words))
        rows.append([
          1/(1+r0) if r0<1000 else 0.,
          1/(1+r4) if r4<1000 else 0.,
          float(r0<10),float(r0<45),
          overlap,
          len(common)/max(1,len(qterms)),
          len(common)/full_len,
          min(1.,len(words)/40),
          min(1.,len(newer)/40),
          rarity/10,
          max_rarity/10,
          len(matches)/8,
          1/(1+min(matches)) if matches else 0.,
          1/(1+first_hit[i]) if i in first_hit else 0.,
          float(d["_id"] in seen_query_seeds),
          len(words&baseline_terms)/full_len,
          len(words&baseline_terms)/max(1,len(baseline_terms))
        ])
    X=np.asarray(rows,dtype=np.float32)
    assert X.shape==(len(indices),FEATURES)
    return indices,X

def fitted_model(X,Y):
    model=HistGradientBoostingClassifier(
      max_iter=100,max_leaf_nodes=15,learning_rate=.08,
      l2_regularization=1.,class_weight="balanced",random_state=SEED)
    model.fit(X,Y)
    return model

def activation(archive,pred,base,protect=0):
    original={d:i for i,d in enumerate(base)}
    priors={i:float(v) for i,v in zip(archive,pred)}
    selected=unique(base[:protect])
    order=sorted(archive,key=lambda i:(-priors[i],original.get(i,10000),i))
    return unique(selected+order+base)

def metric(order,pool,archive,gold):
    needed=gold["gold_mapped"]
    feasible=not gold["strict_unavailable"] and not gold["unresolved_leafs"]
    size=max(1,gold["required_n"])
    result={
      "pool_complete":int(feasible and needed<=set(pool)),
      "archive_complete":int(feasible and needed<=set(archive)),
      "archive_recall":len(needed&set(archive))/size}
    for k in K:
        result["complete"+str(k)]=int(feasible and needed<=set(order[:k]))
        result["recall"+str(k)]=len(needed&set(order[:k]))/size
    return result

def get_bundles(q,docs,sm,graph,link):
    # Each arm reuses original one frozen 4-round sequence, no new query.
    all_stages=run_arm(q,docs,sm,graph,link,"static_first_pass",rounds=4)
    assert all_stages.keys()=={0,1,2,4}
    return all_stages[0],all_stages[1],all_stages[4]

def experiment(folder,out):
    originals,csha=get(folder,"worldtree_corpus.jsonl")
    docs,txtmap,uuids=source_corpus(originals)
    rows,train_sha=get(folder,"task1/train.jsonl")
    assert len(rows)>=CONF[1]
    sm=SparseMethods(docs)
    graph=EvidenceLedger(sm)
    link=FactLinkIndex(docs)
    dev_X=[];dev_y=[];train=0
    for r in rows[DEV[0]:DEV[1]]:
        q=str(r["question"]).strip()
        root,h1,h4=get_bundles(q,docs,sm,graph,link)
        ids,X=numeric_features(q,docs,root,h4,sm.index.idfs)
        gold=reference(r,txtmap,uuids,docs)["gold_mapped"]
        if gold:
            dev_X.append(X);dev_y.extend(int(i in gold) for i in ids)
            train+=1
        if train%100==0:print("V16C_TRAIN",train,flush=True)
    X=np.vstack(dev_X);Y=np.asarray(dev_y,dtype=int)
    assert X.shape[1]==FEATURES and sum(Y)>=100 and train>=300
    t=time.process_time();clf=fitted_model(X,Y);fit_ms=cpu_ms(t)
    cases=[]
    for r in rows[CONF[0]:CONF[1]]:
        q=str(r["question"]).strip()
        t=time.process_time()
        root,h1,h4=get_bundles(q,docs,sm,graph,link)
        full_query_cpu=cpu_ms(t)
        t=time.process_time()
        ids,X=numeric_features(q,docs,root,h4,sm.index.idfs)
        feature_cpu=cpu_ms(t)
        t=time.process_time()
        pred=clf.predict_proba(X)[:,1]
        a=activation(ids,pred,h4["rank"])
        anchored=activation(ids,pred,h4["rank"],protect=5)
        infer_cpu=cpu_ms(t)
        methods={
            "initial":(root["rank"],root["pool"],root["archive"]),
            "cheap_h1":(h1["rank"],h1["pool"],h1["archive"]),
            "unmodified_h4":(h4["rank"],h4["pool"],h4["archive"]),
            "learned_archive":(a,a[:POOL_LIMIT],h4["archive"]),
            "learned_archive_anchor":(anchored,anchored[:POOL_LIMIT],h4["archive"])
        }
        # Gold labels first accessed AFTER all 5 methods have completed.
        gold=reference(r,txtmap,uuids,docs)
        status=decide([Claim("unverified","question","requires","verified_source")],
                      {},[],0)
        assert status.status==Status.ABSTAIN
        cases.append({
          "id":str(r["id"]),"question":q,
          "required_leaf_count":gold["required_n"],"depth":gold["depth"],
          "unavailable_leaf_count":len(gold["strict_unavailable"]),
          "full_archive_source_count":len(h4["archive"]),
          "metrics":{k:metric(rank,pool,archive,gold)
                     for k,(rank,pool,archive) in methods.items()},
          "top20_source_ids":{k:[docs[i]["_id"] for i in rank[:20]]
                     for k,(rank,_,_) in methods.items()},
          "cpu_ms":{"four_round_source_retrieval":full_query_cpu,
                    "activation_features":feature_cpu,
                    "activation_model_and_rank":infer_cpu,
                    "h1_query_cpu":h1["cost_ms"],
                    "h4_query_cpu":h4["cost_ms"]},
          "safety_status":status.status.value
        })
        if len(cases)%50==0:print("V16C_CONFIRM",len(cases),flush=True)
    assert len(cases)==CONF[1]-CONF[0]
    data={"stage":"V16C stored candidate source-set activation",
      "dataset":"EntailmentBank task1 public 11,472 unique science facts",
      "train_question_range":list(DEV),"confirm_question_range":list(CONF),
      "test_question_cohort_previously_inspected_v16b":True,
      "n_train":train,"n_train_pairs":len(Y),"n_positive_train":int(Y.sum()),
      "n_confirm":len(cases),"source_sha":{"corpus":csha,"train":train_sha},
      "fit_cpu_ms":fit_ms,"n_features":FEATURES,
      "method_results":{},"cost_cpu_ms":{},
      "limitations":[
        "Training/development and confirmation are question-disjoint but share source corpus and public annotations",
        "V16B already inspected aggregate confirmation metrics: outcome not sealed",
        "Labels used only in development model training; confirmation gold used only offline after prediction",
        "Archive candidate oracle is NOT final Top120 and NOT verified proof",
        "No true entailment, answer correctness, SOTA or comparable official SAG2/HippoRAG2/S2G execution",
        "All queries use question and source statements only; no gold answer/hypothesis leakage",
        "Model is standard prior art gradient boosted IR, no novel algorithm assertion",
        "Whole source embedding cost is zero; sparse source index build and activation model cost separately measured"]}
    for m in METHODS:
        d={}
        for field in ("pool_complete","archive_complete","complete5","complete10",
                      "complete20","recall5","recall10","recall20"):
            d[field]=round(float(np.mean([c["metrics"][m][field] for c in cases])),6)
        d["four_plus"]={"n":sum(c["required_leaf_count"]>=4 for c in cases),
           "pool_full":sum(c["required_leaf_count"]>=4 and c["metrics"][m]["pool_complete"] for c in cases),
           "complete20":sum(c["required_leaf_count"]>=4 and c["metrics"][m]["complete20"] for c in cases)}
        if m!="unmodified_h4":
            d["vs_h4_pool"]=paired(
              [c["metrics"][m]["pool_complete"] for c in cases],
              [c["metrics"]["unmodified_h4"]["pool_complete"] for c in cases])
        if m.startswith("learned"):
            d["vs_h4_complete20"]=paired(
              [c["metrics"][m]["complete20"] for c in cases],
              [c["metrics"]["unmodified_h4"]["complete20"] for c in cases])
        data["method_results"][m]=d
    for comp in ("four_round_source_retrieval","activation_features",
                 "activation_model_and_rank","h1_query_cpu","h4_query_cpu"):
        vals=[c["cpu_ms"][comp] for c in cases]
        data["cost_cpu_ms"][comp]={"mean":round(float(np.mean(vals)),3),
                         "p95":round(float(np.percentile(vals,95)),3)}
    out.mkdir(parents=True,exist_ok=True)
    (out/"summary.json").write_text(json.dumps(data,indent=2))
    with (out/"cases.jsonl").open("w") as f:
        for c in cases:f.write(json.dumps(c,ensure_ascii=False)+"\n")
    print("V16C_RESULT",json.dumps(data),flush=True)

def smoke():
    docs=[{"_id":"a","title":"A","text":"A frog is an amphibian"},
          {"_id":"b","title":"B","text":"Frogs breathe oxygen"}]
    root={"rank":[0,1]}
    h4={"rank":[1,0],"archive":[0,1],
        "hitlists":[[1,0]],"actions":[{"source_id":"a"}]}
    idx,X=numeric_features("How does a frog breathe?",docs,root,h4,
                           {"frog":1.,"breathe":1.,"oxygen":2.})
    assert X.shape==(2,FEATURES)
    assert set(activation(idx,[.3,.7],[0,1]))=={0,1}
    assert len(activation(idx,[.3,.7],[0,1],protect=1))==2
    print("V16C same-source archive activation and strict cheap ranking smoke PASS")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("smoke","run"))
    p.add_argument("--data",type=pathlib.Path,
                   default=pathlib.Path("data/entailmentbank_v14"))
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v16c"))
    a=p.parse_args()
    if a.command=="smoke":return smoke()
    experiment(a.data,a.out)
if __name__=="__main__":main()
