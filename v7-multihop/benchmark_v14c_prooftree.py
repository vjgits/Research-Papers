#!/usr/bin/env python3
"""V14C truly new external *proof-tree* held-out source retrieval.

EntailmentBank (Dalvi et al EMNLP 2021; CC-BY-4.0 mirror) has human-
annotated proof trees, exact source facts, inference depths/steps. Test:
official 340 gold proof questions NEVER used for training/model/weight choice.
Gold proof used ONLY offline for fact identity and metric, no edge prediction.

Train previously frozen V11.3 23-feature cached HistGradientBoosting ranker
on first 400 official EntailmentBank task1 training questions. No tuning.
Compare BM25, V7.1 fast, unsupervised 2-query facet, learned boosted.

Primary claim: complete *exact* required WorldTree fact text in Top5/10/20.
Missing/rewritten gold facts count as unavailable; duplicates merged by
identical text, provenance UUID alternative is diagnostic only. Exact fact
retrieval is NOT source-relation entailment or reconstructed proof validity.
"""
import argparse,collections,hashlib,json,pathlib,re,time
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from audit_v14_entailmentbank import get,canonical,PROOF_SENT
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger
from benchmark_v95_controlled import paired,cpu_ms,unique
from benchmark_v113 import doc_cache,prepare
from benchmark_v111 import reorder,SEED
from audit_v14b_provenance import provenance

TRAIN_SIZE=400
K_VALUES=(5,10,20)
METHODS=("bm25","v71_fast","two_facet_fusion","pger_cached_boosted")
CORPUS_REV="8c6c148f7a21c21ff037a42d9a22446c9d42debc"

def source_corpus(rows):
    """Canonical text dedup is legitimate: literal duplicate statements are
    identical information, not additional independent sources."""
    docs=[];txtmap={}
    uuids={}
    for original in rows:
        original_text=str(original["text"]).strip()
        key=canonical(original_text)
        if not key or key in txtmap:continue
        idx=len(docs);txtmap[key]=idx
        label=" ".join(original_text.split()[:8])[:100]
        docs.append({"_id":str(original["uuid"]),
                     "title":label,
                     "text":original_text,
                     "source":str(original.get("source",""))})
    for r in rows:
        u=str(r.get("uuid"))
        c=canonical(r.get("text"))
        if c in txtmap:uuids[u]=txtmap[c]
    return docs,txtmap,uuids

def reference(q,txtmap,uuids,docs):
    """Offline proof-leaf extraction, NEVER passed into retrieval pipeline."""
    triples=(q.get("meta") or {}).get("triples") or {}
    prov=(q.get("meta") or {}).get("worldtree_provenance") or {}
    leaves=sorted(set(PROOF_SENT.findall(q.get("proof") or "")),
                  key=lambda s:int(s[4:]))
    gold_exact=set();strict_missing=[];uuid_rewritten=[]
    bad=[]
    for leaf in leaves:
        t=canonical(triples.get(leaf,""))
        if not t:
            bad.append(leaf);continue
        if t in txtmap:gold_exact.add(txtmap[t]);continue
        strict_missing.append(leaf)
        possible=[uuids[x] for x in provenance(prov,leaf) if x in uuids]
        if possible:uuid_rewritten.append((leaf,possible[0]))
    return {"leafs":leaves,"required_n":len(leaves),
            "gold_mapped":gold_exact,
            "strict_unavailable":strict_missing,
            "uuid_modified_count":len(uuid_rewritten),
            "unresolved_leafs":bad,
            "depth":int(q.get("depth_of_proof") or 0),
            "steps":int(q.get("length_of_proof") or 0)}

def evaluate_metric(rank,gold):
    mapped=gold["gold_mapped"]
    complete=(not gold["strict_unavailable"] and
              not gold["unresolved_leafs"])
    den=max(1,gold["required_n"])
    out={"available_all_exact":int(complete),
         "available_gold_count":len(mapped),
         "required_facts":gold["required_n"]}
    for k in K_VALUES:
        available_hits=len(mapped & set(rank[:k]))
        out["fact_recall_at"+str(k)]=available_hits/den
        out["complete_at"+str(k)]=int(complete and mapped<=set(rank[:k]))
    return out

def run(data,out):
    original_corpus,hash_corpus=get(data,"worldtree_corpus.jsonl")
    docs,txtmap,uuids=source_corpus(original_corpus)
    source_sha={"worldtree_corpus":hash_corpus}
    questions={}
    for split in ("train","validation","test"):
        rows,sha=get(data,"task1/"+split+".jsonl")
        questions[split]=rows;source_sha[split]=sha

    # NOTE: Model sees NO gold proof at inference: reference only offline.
    cache,cache_ms=doc_cache(docs)
    t=time.process_time();sm=SparseMethods(docs);build_sparse=cpu_ms(t)
    t=time.process_time();graph=EvidenceLedger(sm);build_graph=cpu_ms(t)

    training_x=[];training_y=[]
    train_stats=collections.Counter()
    for r in questions["train"][:TRAIN_SIZE]:
        q=str(r.get("question","")).strip()
        if not q:train_stats["empty_question"]+=1;continue
        gold=reference(r,txtmap,uuids,docs)
        if not gold["gold_mapped"]:train_stats["no_available_gold"]+=1;continue
        b=prepare(q,sm,graph,docs,cache,parity=False)
        training_x.append(b["X"])
        training_y.extend(int(i in gold["gold_mapped"]) for i in b["pool"])
        train_stats["trained_questions"]+=1
        if train_stats["trained_questions"]%100==0:
            print("V14C_TRAIN",train_stats["trained_questions"],flush=True)
    X=np.vstack(training_x);Y=np.asarray(training_y,dtype=np.int32)
    assert X.shape[1]==23 and sum(Y)>100
    model=HistGradientBoostingClassifier(
       max_iter=100,max_leaf_nodes=15,learning_rate=.08,
       l2_regularization=1.,class_weight="balanced",random_state=SEED)
    t=time.process_time();model.fit(X,Y);fit_ms=cpu_ms(t)

    reports={}
    for split in ("validation","test"):
        cases=[];processing=collections.Counter()
        for row in questions[split]:
            q=str(row.get("question","")).strip()
            if not q:processing["empty_question"]+=1;continue
            # Gold never inspected before retrieving/ranking.
            b=prepare(q,sm,graph,docs,cache,parity=False)
            from benchmark_v11 import facet_queries,fusion
            facets=facet_queries(q)[:2]
            hits=[[i for i,_ in sm.index.search(f,"bm25",50)] for f in facets]
            fused=fusion(b["fast"],b["bm"],hits)
            t=time.process_time();probs=model.predict_proba(b["X"])[:,1]
            learned=reorder(probs,b["fast"],b["pool"])
            model_ms=cpu_ms(t)
            rankings={"bm25":b["bm"],"v71_fast":b["fast"],
                      "two_facet_fusion":fused,"pger_cached_boosted":learned}
            gold=reference(row,txtmap,uuids,docs)
            processing["n_questions"]+=1
            processing["strict_fully_available"]+=int(
                not gold["strict_unavailable"] and not gold["unresolved_leafs"])
            processing["n_with_4plus_leaf_facts"]+=int(gold["required_n"]>=4)
            processing["n_with_4plus_depth"]+=int(gold["depth"]>=4)
            case={"id":str(row.get("id","")),"question":q,
                "proof_leaf_count":gold["required_n"],
                "proof_depth":gold["depth"],"proof_step_count":gold["steps"],
                "exact_gold_available":len(gold["gold_mapped"]),
                "exact_unavailable_count":len(gold["strict_unavailable"]),
                "provenance_rewritten_count":gold["uuid_modified_count"],
                "candidate_pool_all_gold":int(
                    not gold["strict_unavailable"] and
                    gold["gold_mapped"]<=set(b["pool"])),
                "metrics":{m:evaluate_metric(v,gold) for m,v in rankings.items()},
                "top20_ids":{m:[docs[i]["_id"] for i in v[:20]]
                            for m,v in rankings.items()},
                "cpu_ms":{"initial":b["time"]["base"],
                           "feature":b["time"]["features"],
                           "facets":b["time"]["extra"],
                           "learned_prediction_rerank":model_ms}}
            cases.append(case)
            if len(cases)%60==0:print("V14C_PROGRESS",split,len(cases),flush=True)
        assert len(cases)==len(questions[split]),"Unexpected missing test rows"
        stats={"dataset":"EntailmentBank task1 official "+split,
               "n":len(cases),
               "source_sha":source_sha,
               "corpus_original_fact_rows":len(original_corpus),
               "corpus_unique_exact_fact_texts":len(docs),
               "trained_on_first_n_train_questions":TRAIN_SIZE,
               "trained_pairs":len(Y),"positive_train_pairs":int(sum(Y)),
               "train_stats":dict(train_stats),
               "build_cpu_ms":{"token_cache":cache_ms,
                      "sparse_index":build_sparse,"title_graph":build_graph,
                      "boosted_fit":fit_ms},
               "source_availability":dict(processing),"methods":{},
               "warnings":[
                 "Test proof annotations are used only offline to compute gold leaves; no model uses gold at inference",
                 "Gold answer/hypothesis is NOT included in retrieval query: query is question text only",
                 "WorldTree corpus texts are literal released facts; duplicate identical facts are one information unit",
                 "Modified or absent facts are strict missing sources; UUID matches do NOT earn full-fact credit",
                 "Complete proof LEAVES retrieved does NOT mean generated proof edges were entailed",
                 "Proof depth/steps and number of premise facts are different",
                 "For >K distinct required facts complete@K is mathematically impossible",
                 "Public official test has never been a user-private sealed corpus; no SOTA/novelty claim",
                 "V7.1 and boosted originally engineered on news, tuning on test prohibited",
                 "CPU sums are process times after indexing, not production wall-clock"]}
        for method in METHODS:
            vals=[p["metrics"][method] for p in cases]
            m={}
            for k in K_VALUES:
                m["complete_at"+str(k)]=round(float(np.mean(
                    [v["complete_at"+str(k)] for v in vals])),6)
                m["fact_recall_at"+str(k)]=round(float(np.mean(
                    [v["fact_recall_at"+str(k)] for v in vals])),6)
            m["breakdown_by_leaf_count"]={}
            groups={
             "one_two":lambda p:p["proof_leaf_count"]<=2,
             "three":lambda p:p["proof_leaf_count"]==3,
             "four":lambda p:p["proof_leaf_count"]==4,
             "five":lambda p:p["proof_leaf_count"]==5,
             "six_plus":lambda p:p["proof_leaf_count"]>=6,
             "four_plus":lambda p:p["proof_leaf_count"]>=4,
             "deep_four_plus":lambda p:p["proof_depth"]>=4,
             "fully_present":lambda p:p["exact_unavailable_count"]==0
            }
            for label,fn in groups.items():
                items=[r for r in cases if fn(r)]
                if items:
                    m["breakdown_by_leaf_count"][label]={
                        "n":len(items),
                        "strict_available":sum(r["exact_unavailable_count"]==0 for r in items),
                        "full_pool":sum(r["candidate_pool_all_gold"] for r in items),
                        "complete5":sum(r["metrics"][method]["complete_at5"] for r in items),
                        "complete10":sum(r["metrics"][method]["complete_at10"] for r in items),
                        "complete20":sum(r["metrics"][method]["complete_at20"] for r in items)}
            if method!="v71_fast":
                for k in K_VALUES:
                    m["paired_vs_fast_at"+str(k)]=paired(
                       [v["complete_at"+str(k)] for v in vals],
                       [r["metrics"]["v71_fast"]["complete_at"+str(k)] for r in cases])
            stats["methods"][method]=m
        stats["cpu_mean_ms"]={k:round(float(np.mean([c["cpu_ms"][k] for c in cases])),3)
                              for k in ("initial","feature","facets","learned_prediction_rerank")}
        stats["cpu_p95_ms"]={k:round(float(np.percentile([c["cpu_ms"][k] for c in cases],95)),3)
                              for k in ("initial","feature","facets","learned_prediction_rerank")}
        out.mkdir(parents=True,exist_ok=True)
        (out/(split+"_summary.json")).write_text(json.dumps(stats,indent=2))
        with (out/(split+"_cases.jsonl")).open("w") as f:
            for case in cases:f.write(json.dumps(case,ensure_ascii=False)+"\n")
        reports[split]=stats
        print("V14C_RESULT",split,json.dumps({
            "n":stats["n"],
            "availability":stats["source_availability"],
            "methods":{k:{"complete5":v["complete_at5"],
                "complete10":v["complete_at10"],
                "complete20":v["complete_at20"],
                "four_plus":v["breakdown_by_leaf_count"].get("four_plus"),
                "deep_four_plus":v["breakdown_by_leaf_count"].get("deep_four_plus"),
                "paired_fast5":v.get("paired_vs_fast_at5")}
                for k,v in stats["methods"].items()},
            "cpu":stats["cpu_mean_ms"]}),flush=True)
    print("V14C_HELDOUT_COMPLETE",flush=True)

def smoke():
    docs,txt,u=source_corpus([
        {"uuid":"abc","text":"A star emits light","source":"worldtree"},
        {"uuid":"def","text":"A star emits light","source":"worldtree"},
        {"uuid":"xyz","text":"Light is energy","source":"et_addon"}])
    assert len(docs)==2 and len(u)==3
    row={"proof":"sent1 & sent2 -> hypothesis;",
         "meta":{"triples":{"sent1":"A star emits light",
                            "sent2":"An unmatched statement"}}}
    x=reference(row,txt,u,docs)
    assert x["required_n"]==2 and len(x["gold_mapped"])==1
    assert len(x["strict_unavailable"])==1
    print("V14C exact fact equivalence and missing proof-leaf smoke PASS")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("smoke","run"))
    p.add_argument("--data",type=pathlib.Path,default=pathlib.Path("data/entailmentbank_v14"))
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v14c"))
    a=p.parse_args()
    if a.command=="smoke":return smoke()
    run(a.data,a.out)
if __name__=="__main__":main()
