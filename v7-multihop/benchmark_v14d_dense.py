#!/usr/bin/env python3
"""PGER V14D: sparse-vs-open-dense discovery on human proof-tree science data.

EXPLORATORY: official EntailmentBank TEST previously inspected in V14C.
Do not claim sealed generalization. One pretrained MIT BGE-small 1.5,
pinned by resolved Hugging Face git revision, NO paid services.

Question-only query, same exact WorldTree released fact corpus and all 340
official heldout questions, no answers or gold proof in model input. Compare
sparse-only 120 pool to dense-only top80 and fixed 60+60 hybrid 120 pool.
Train separate frozen V11.3-spec rankers on first 400 official TRAIN cases,
with source gold used only in training labels. Gold TEST used post-ranking.

Gold exact text, duplicates and unavailable sources follow V14C strict
mapping. Inference is semantic relevance, NOT entailment/proof validation.
"""
import argparse,collections,json,pathlib,time,hashlib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from benchmark_v14c_prooftree import (get,source_corpus,reference,
                                      evaluate_metric,K_VALUES)
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger
from benchmark_v95_controlled import paired,cpu_ms,unique
from benchmark_v113 import doc_cache,prepare,cached_data_features
from benchmark_v111 import reorder,SEED

MODEL="BAAI/bge-small-en-v1.5"
TRAIN_SIZE=400
DENSE_K=80
POOL_LIMIT=120
SPARSE_RESERVE=60
DENSE_RESERVE=60
METHODS=("bm25","v71_fast","pger_sparse","dense_direct",
         "hybrid_rrf","pger_hybrid")

def get_dense(docs,questions):
    from sentence_transformers import SentenceTransformer
    from huggingface_hub import model_info
    import torch
    torch.set_num_threads(2)
    revision=model_info(MODEL).sha
    t=time.process_time()
    model=SentenceTransformer(MODEL,revision=revision,device="cpu")
    model.max_seq_length=256
    model_load=cpu_ms(t)
    t=time.process_time()
    docmat=model.encode([d["text"] for d in docs],batch_size=96,
        normalize_embeddings=True,convert_to_numpy=True,
        show_progress_bar=False).astype(np.float32)
    build_cpu=cpu_ms(t)
    t=time.process_time()
    qmat=model.encode(["Represent this sentence for searching relevant passages: "+q
                       for q in questions],batch_size=64,
        normalize_embeddings=True,convert_to_numpy=True,
        show_progress_bar=False).astype(np.float32)
    encode_cpu=cpu_ms(t)
    t=time.process_time()
    sim=qmat@docmat.T
    score_cpu=cpu_ms(t)
    return sim,{"name":MODEL,"license":"MIT","revision":revision,
        "load_cpu_ms":round(model_load,2),
        "offline_doc_encode_cpu_ms":round(build_cpu,2),
        "query_encode_cpu_ms_total":round(encode_cpu,2),
        "query_similarity_cpu_ms_total":round(score_cpu,2),
        "batch_amortized_query_cpu_ms":round(
           (encode_cpu+score_cpu)/len(questions),3),
        "vector_index_bytes":int(docmat.nbytes),"dims":int(docmat.shape[1])}

def dense_indices(row,k=DENSE_K):
    ix=np.argpartition(-row,min(k,len(row)-1))[:k]
    return [int(i) for i in sorted(ix,key=lambda j:(-float(row[j]),int(j)))]

def hybrid_pool(sparse,dense):
    seed=unique(sparse[:SPARSE_RESERVE]+dense[:DENSE_RESERVE])
    return unique(seed+sparse+dense)[:POOL_LIMIT]
def hybrid_rrf(sparse,dense):
    scores={}
    for r,i in enumerate(sparse[:120]):
        scores[i]=scores.get(i,0.)+1/(25+r)
    for r,i in enumerate(dense[:DENSE_K]):
        scores[i]=scores.get(i,0.)+1/(25+r)
    ids=hybrid_pool(sparse,dense)
    ranked=sorted(ids,key=lambda i:(-scores.get(i,0.),i))
    return unique(ranked+sparse+dense)

def model_spec():
    return HistGradientBoostingClassifier(
      max_iter=100,max_leaf_nodes=15,learning_rate=.08,
      l2_regularization=1.,class_weight="balanced",random_state=SEED)

def evaluate(data,out):
    worldtree,corpushash=get(data,"worldtree_corpus.jsonl")
    docs,textmap,uuids=source_corpus(worldtree)
    records={}
    source_hash={"worldtree":corpushash}
    for split in ("train","validation","test"):
        rows,sha=get(data,f"task1/{split}.jsonl")
        records[split]=rows;source_hash[split]=sha
    # Identical precommitted train and official test partitions.
    train=records["train"][:TRAIN_SIZE]
    ordered=[*train,*records["validation"],*records["test"]]
    questions=[str(r.get("question","")).strip() for r in ordered]
    assert all(questions)

    cache,cache_cpu=doc_cache(docs)
    t=time.process_time();sm=SparseMethods(docs);bm_cpu=cpu_ms(t)
    t=time.process_time();graph=EvidenceLedger(sm);graph_cpu=cpu_ms(t)
    similarities,dense_cost=get_dense(docs,questions)
    cache_results={}
    Xt_s=[];Xt_h=[];Y_s=[];Y_h=[]
    for i,raw in enumerate(train):
        q=questions[i]
        pack=prepare(q,sm,graph,docs,cache)
        dense=dense_indices(similarities[i])
        hybrid=hybrid_pool(pack["pool"],dense)
        facets=__import__("benchmark_v11").facet_queries(q)[:2]
        hits=[[j for j,_ in sm.index.search(f,"bm25",50)] for f in facets]
        t=time.process_time()
        X_h,_=cached_data_features(q,docs,pack["bm"],pack["fast"],
                                   facets,hits,hybrid,sm.index.idfs,cache)
        xh_cpu=cpu_ms(t)
        gold=reference(raw,textmap,uuids,docs)["gold_mapped"]
        if gold:
            Xt_s.append(pack["X"]);Xt_h.append(X_h)
            Y_s.extend(int(j in gold) for j in pack["pool"])
            Y_h.extend(int(j in gold) for j in hybrid)
        if (i+1)%100==0:print("V14D_TRAIN",i+1,flush=True)
    Xt_s=np.vstack(Xt_s);Xt_h=np.vstack(Xt_h)
    assert len(Y_s)==len(Xt_s) and len(Y_h)==len(Xt_h)
    t=time.process_time();smodel=model_spec().fit(Xt_s,np.asarray(Y_s));train_s=cpu_ms(t)
    t=time.process_time();hmodel=model_spec().fit(Xt_h,np.asarray(Y_h));train_h=cpu_ms(t)

    reports={}
    idx=TRAIN_SIZE
    for split in ("validation","test"):
        examples=[];data_rows=records[split]
        for raw in data_rows:
            q=questions[idx]
            t=time.process_time()
            pack=prepare(q,sm,graph,docs,cache)
            dense=dense_indices(similarities[idx])
            hybrid=hybrid_pool(pack["pool"],dense)
            init_ms=cpu_ms(t)
            facets=__import__("benchmark_v11").facet_queries(q)[:2]
            hits=[[j for j,_ in sm.index.search(f,"bm25",50)] for f in facets]
            t=time.process_time()
            X_h,_=cached_data_features(q,docs,pack["bm"],pack["fast"],
                             facets,hits,hybrid,sm.index.idfs,cache)
            feat_h_ms=cpu_ms(t)
            t=time.process_time()
            sparse_pred=smodel.predict_proba(pack["X"])[:,1]
            hybrid_pred=hmodel.predict_proba(X_h)[:,1]
            sparse_rank=reorder(sparse_pred,pack["fast"],pack["pool"])
            hybrid_rank=reorder(hybrid_pred,pack["fast"],hybrid)
            pred_ms=cpu_ms(t)
            rankings={"bm25":pack["bm"],"v71_fast":pack["fast"],
               "pger_sparse":sparse_rank,"dense_direct":dense,
               "hybrid_rrf":hybrid_rrf(pack["pool"],dense),
               "pger_hybrid":hybrid_rank}
            # Gold annotations accessed only after all scores/ranks computed.
            gold=reference(raw,textmap,uuids,docs)
            strict=int(not gold["strict_unavailable"] and
                       not gold["unresolved_leafs"])
            pools={"sparse120":pack["pool"],"dense80":dense,"hybrid120":hybrid}
            examples.append({
                "id":str(raw["id"]),
                "proof_depth":gold["depth"],
                "proof_steps":gold["steps"],
                "required_facts":gold["required_n"],
                "gold_exact_available":strict,
                "missing_exact_fact_count":len(gold["strict_unavailable"]),
                "candidate_full":{name:int(strict and gold["gold_mapped"]<=set(pool))
                              for name,pool in pools.items()},
                "candidate_recall":{name:len(gold["gold_mapped"]&set(pool))/
                              max(1,gold["required_n"]) for name,pool in pools.items()},
                "metrics":{m:evaluate_metric(rank,gold) for m,rank in rankings.items()},
                "top20_source_ids":{m:[docs[j]["_id"] for j in rank[:20]]
                              for m,rank in rankings.items()},
                "cpu_ms":{"sparse_retrieval_plus_dense_ranking":init_ms,
                          "hybrid_features":feat_h_ms,
                          "dual_models_and_rerank":pred_ms}})
            idx+=1
            if len(examples)%60==0:print("V14D_PROGRESS",split,len(examples),flush=True)
        result={"stage":"V14D","dataset":"EntailmentBank science proof trees",
                "test_previously_inspected_by_V14C":True,"split":split,
                "n":len(examples),"source_sha":source_hash,
                "unique_exact_worldtree_facts":len(docs),
                "train_first_n":TRAIN_SIZE,"train_available_sparse_pairs":len(Y_s),
                "train_available_hybrid_pairs":len(Y_h),
                "train_cpu_ms":{"sparse_boosted":train_s,"hybrid_boosted":train_h},
                "offline_cpu_ms":{"cache":cache_cpu,"bm25":bm_cpu,"graph":graph_cpu},
                "dense_cost":dense_cost,
                "methods":{},
                "candidate_pool":{"sparse120":{},"dense80":{},"hybrid120":{}},
                "warnings":[
                    "This is exploratory test reuse after V14C, not sealed validation",
                    "Dense retrieval is semantic relevance NOT proof entailment",
                    "All queries contain question text only, never answers or gold hypothesis",
                    "Exact gold statement missing means strict complete retrieval impossible",
                    "Gold proof inference edges not generated or verified",
                    "Offline embedding CPU/index memory is material, not free retrieval",
                    "Identical 120-candidate cap between sparse-only and hybrid for trained rerank",
                    "Four-plus source facts and four-plus proof-depth are distinct",
                    "End-to-end wall and CPU comparisons with SOTA systems not established"]}
        for pname in ("sparse120","dense80","hybrid120"):
            result["candidate_pool"][pname]={
               "full_all_questions":sum(x["candidate_full"][pname] for x in examples),
               "full_four_plus":sum(x["candidate_full"][pname] and
                         x["required_facts"]>=4 for x in examples),
               "mean_fact_recall":round(float(np.mean(
                    [x["candidate_recall"][pname] for x in examples])),6)}
        for method in METHODS:
            xs=[x["metrics"][method] for x in examples]
            m={k:round(float(np.mean([v[k] for v in xs])),6)
               for k in ("complete_at5","complete_at10","complete_at20",
                         "fact_recall_at5","fact_recall_at10","fact_recall_at20")}
            m["four_plus"]={k:sum(x["required_facts"]>=4 and
                     x["metrics"][method]["complete_at"+str(k)] for x in examples)
                     for k in K_VALUES}
            m["deep_four_plus"]={k:sum(x["proof_depth"]>=4 and
                     x["metrics"][method]["complete_at"+str(k)] for x in examples)
                     for k in K_VALUES}
            for other in ("v71_fast","pger_sparse","hybrid_rrf"):
                if method!=other:
                    m["vs_"+other+"_at10"]=paired(
                    [x["metrics"][method]["complete_at10"] for x in examples],
                    [x["metrics"][other]["complete_at10"] for x in examples])
            result["methods"][method]=m
        result["cpu_mean_ms"]={c:round(float(np.mean([x["cpu_ms"][c] for x in examples])),3)
                for c in ("sparse_retrieval_plus_dense_ranking","hybrid_features",
                          "dual_models_and_rerank")}
        out.mkdir(parents=True,exist_ok=True)
        (out/(split+"_summary.json")).write_text(json.dumps(result,indent=2))
        with (out/(split+"_cases.jsonl")).open("w") as f:
            for e in examples:f.write(json.dumps(e,ensure_ascii=False)+"\n")
        print("V14D_RESULT",split,json.dumps({
                "n":result["n"],"candidates":result["candidate_pool"],
                "methods":result["methods"],"cpu":result["cpu_mean_ms"],
                "dense":result["dense_cost"]}),flush=True)
    print("V14D_COMPLETE",flush=True)
def smoke():
    d=hybrid_pool([1,2,3],[3,4,5])
    assert len(d)==5 and len(set(d))==5
    ranks=hybrid_rrf([1,2,3],[2,4,5])
    assert set([1,2,3,4,5])<=set(ranks)
    print("V14D frozen hybrid pool and RRF smoke PASS")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("smoke","run"))
    p.add_argument("--data",type=pathlib.Path,default=pathlib.Path("data/entailmentbank_v14"))
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v14d"))
    a=p.parse_args()
    if a.command=="smoke":return smoke()
    evaluate(a.data,a.out)
if __name__=="__main__":main()
