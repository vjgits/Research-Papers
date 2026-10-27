#!/usr/bin/env python3
"""V6.3 Independent Evidence Reviewers, development-only BEIR evaluation.

Research hypothesis (not an established discovery): a second retrieval view
and reviewers with intentionally different information access can find
evidence that the initial BM25 search missed without harmful rank churn.

NOT an autonomous LLM multi-agent system:
  blind reviewer = frozen MS MARCO cross-encoder: question + candidate alone
  context reviewer = explicit evidence-gap/source-overlap checks on original
                     BM25 documents, original question, and new candidate
  coordinator = fixed conservative rules, no access to relevance judgments
These modules are isolated from qrels. No paid APIs. Model download and CPU
cost are recorded. Never claim retrieval nDCG is final answer accuracy.

BEIR 'sealed' qrels are filtered while reading and never materialized.
Development-fit and development-validation subsets are disjoint and stable.
"""
import argparse, collections, hashlib, json, math, os, pathlib, sys, time
import numpy as np
import torch
from sklearn.metrics.pairwise import cosine_similarity
from benchmark_v6 import Retriever, download, partition, jsonl, measures
from benchmark_v62 import inner_part

torch.set_num_threads(min(2, max(1,os.cpu_count() or 2)))
EMBED_MODEL="sentence-transformers/all-MiniLM-L6-v2"
REVIEW_MODEL="cross-encoder/ms-marco-MiniLM-L-6-v2"
BENCHMARKS=("scifact","nfcorpus")
SEED="v6.3-reviewers-2026-10-27"
BM25_POOL=24
DENSE_POOL=24
CE_MAX_LEN=256
CE_BATCH=24
# Fixed before the run. No tuning on development-validation.
GAP_MASS_THRESHOLD=0.17
REVIEWER_SUPPORT_THRESHOLD=0.30
BLIND_ADVANTAGE_THRESHOLD=0.09
DENSE_SOURCE_NOVELTY_THRESHOLD=0.09
MAX_REVIEWED=48

def load_dev_only(folder,dataset):
    """Read BEIR documents and development qrels, discard sealed qrels immediately.
    No sealed qrels dictionary is built and no sealed scores are computed.
    """
    docs=list(jsonl(folder/"corpus.jsonl"))
    queries={}
    for q in jsonl(folder/"queries.jsonl"):
        if partition(dataset,q["_id"])=="dev":
            queries[q["_id"]]=q["text"]
    gold=collections.defaultdict(dict)
    with (folder/"qrels"/"test.tsv").open(encoding="utf8") as f:
        header=f.readline().strip().split("\t")
        if header[:3]!=["query-id","corpus-id","score"]:raise ValueError("BEIR format changed")
        for line in f:
            qid,docid,grade=line.rstrip().split("\t")[:3]
            if qid in queries and int(grade)>0:gold[qid][docid]=int(grade)
    return docs,queries,gold

def stable_rank(scores,ids,top=100):
    scores=np.asarray(scores)
    vals=np.flatnonzero(np.isfinite(scores))
    if not len(vals):return []
    n=min(top,len(vals))
    subset=vals[np.argpartition(scores[vals],-n)[-n:]]
    return sorted((int(i) for i in subset),key=lambda i:(-float(scores[i]),ids[i]))

def text_view(d):
    return (d.get("title","")+" "+d.get("text","")).strip()

def sigmoid(value):
    # Fixed normalization of cross-encoder logits. These are NOT calibrated probabilities.
    return 1/(1+math.exp(-max(-30.,min(30.,float(value)))))

def weighted_coverage(index,qwords,docrow):
    present=set(index.count.indices[index.count.indptr[docrow]:index.count.indptr[docrow+1]])
    denom=max(1e-8,sum(index.idfs.get(t,0.) for t in qwords))
    score=sum(index.idfs.get(t,0.) for t in qwords if index.words.vocabulary_.get(t,-1) in present)
    return score/denom

def context_review(index,question,baseids,chosen):
    """Checklist-only context reviewer. Receives original ranks+passages;
    knows nothing about cross-encoder logits or qrels.
    """
    terms=sorted(set(index.words.build_analyzer()(question))&set(index.words.vocabulary_))
    if not terms:return {"gap":0.,"coverage":0.,"fills":0.,"novelty":0.,"support":0.}
    seen=set()
    for i in baseids[:2]:
        seen.update(index.count.indices[index.count.indptr[i]:index.count.indptr[i+1]])
    row=set(index.count.indices[index.count.indptr[chosen]:index.count.indptr[chosen+1]])
    allmass=max(1e-8,sum(index.idfs[t] for t in terms))
    gapmass=sum(index.idfs[t] for t in terms if index.words.vocabulary_[t] not in seen)
    fillmass=sum(index.idfs[t] for t in terms if index.words.vocabulary_[t] not in seen and index.words.vocabulary_[t] in row)
    coverage=sum(index.idfs[t] for t in terms if index.words.vocabulary_[t] in row)/allmass
    novelty=len(row-seen)/max(1,len(row))
    # Independent checklist: meaningful gap fill and original-question coverage.
    support=(fillmass/max(gapmass,1e-8))*(0.50+0.50*coverage)
    return {"gap":gapmass/allmass,"coverage":coverage,
            "fills":fillmass/max(gapmass,1e-8),"novelty":novelty,
            "support":support}

class EvidenceSystem:
    def __init__(self,docs,embedder,crossencoder):
        self.docs=docs
        self.docs_by_id=[text_view(d) for d in docs]
        self.bm=Retriever(docs)
        self.embedder=embedder
        self.crossencoder=crossencoder
        t=time.perf_counter()
        self.dense=np.asarray(embedder.encode(self.docs_by_id,show_progress_bar=False,
            batch_size=48,normalize_embeddings=True,convert_to_numpy=True),dtype=np.float32)
        self.encode_seconds=time.perf_counter()-t
    def evaluate_one(self,question):
        timing={}
        t=time.perf_counter()
        bm_scores=self.bm.search(question,"bm25",100)
        bmids=[i for i,s in bm_scores]
        timing["bm25_ms"]=(time.perf_counter()-t)*1000
        t=time.perf_counter()
        qemb=np.asarray(self.embedder.encode([question],normalize_embeddings=True,
                   convert_to_numpy=True),dtype=np.float32).reshape(-1)
        denseids=stable_rank(self.dense@qemb,self.bm.ids,100)
        timing["dense_ms"]=(time.perf_counter()-t)*1000
        if not bmids or not denseids:raise ValueError("Empty retrieval result")
        bset=set(bmids[:100])
        pool=list(dict.fromkeys(bmids[:BM25_POOL]+denseids[:DENSE_POOL]))
        # A query-blind-from-searcher reviewer: question+candidate text, without
        # any rank, search terms, provenance or earlier agent explanations.
        t=time.perf_counter()
        pair=[(question,self.docs_by_id[i][:1150]) for i in pool]
        logits=self.crossencoder.predict(pair,batch_size=CE_BATCH,show_progress_bar=False,
                 convert_to_numpy=True)
        logits=np.asarray(logits).reshape(-1)
        blind={i:sigmoid(v) for i,v in zip(pool,logits)}
        blindrank=sorted(pool,key=lambda i:(-blind[i],self.bm.ids[i]))
        timing["blind_ms"]=(time.perf_counter()-t)*1000
        t=time.perf_counter()
        # context reviewer receives no blind scores. Its checklist is applied
        # independently to original and newly surfaced sources.
        context={i:context_review(self.bm,question,bmids,i) for i in pool}
        reviewrank=sorted(pool,key=lambda i:(-context[i]["support"],-context[i]["coverage"],self.bm.ids[i]))
        timing["context_ms"]=(time.perf_counter()-t)*1000
        # Hybrid includes ALL baseline top-100 for fair retrieval recall@100.
        bpos={i:j for j,i in enumerate(bmids)}
        dpos={i:j for j,i in enumerate(denseids)}
        allids=set(bmids)|set(denseids)
        hybrid=sorted(allids,key=lambda i:(-
             (1/(60+bpos[i]+1) if i in bpos else 0)-
             (1/(60+dpos[i]+1) if i in dpos else 0),self.bm.ids[i]))
        # Context-aware critic is intentionally conservative: it may approve
        # a new document over the initial BM25 top-10 only when it fills
        # otherwise unresolved terms, and the blind critic is favorable.
        bm10=bmids[:10]
        baseline_ce=blind.get(bmids[0],0)
        approved=[]
        for i in blindrank:
            if i in bm10:continue
            info=context[i]
            # An uncorrelated source can be independently relevant but must
            # preserve topic and a supportable gap to change the ranking.
            accepted=(info["gap"]>=GAP_MASS_THRESHOLD and
                info["support"]>=REVIEWER_SUPPORT_THRESHOLD and
                info["novelty"]>=DENSE_SOURCE_NOVELTY_THRESHOLD and
                blind[i]>=baseline_ce+BLIND_ADVANTAGE_THRESHOLD)
            if accepted:approved.append(i)
        # No destructive rank churn: put only the strongest independently
        # approved genuinely new source at position 5. All existing 1-4 protected.
        dual=list(bmids)
        if approved:
            candidate=approved[0]
            dual=bmids[:4]+[candidate]+[i for i in bmids[4:] if i!=candidate]
            dual=dual[:100]
        # Published baselines and ablations:
        def fill(ids,back):
            out=list(dict.fromkeys(ids+back))
            return out[:100]
        bmce=sorted(bmids[:MAX_REVIEWED],key=lambda i:(-blind.get(i,-10),self.bm.ids[i]))
        # If candidate is outside CE-scored BM25 pool we score on same 24 BM25.
        bmce=sorted(bmids[:BM25_POOL],key=lambda i:(-blind[i],self.bm.ids[i]))
        return {
            "bm25":bmids,
            "dense":denseids,
            "hybrid":hybrid[:100],
            "bm25_blind":fill(bmce,bmids),
            "union_blind":fill(blindrank,bmids+denseids),
            "union_context":fill(reviewrank,bmids+denseids),
            "dual_review":dual,
        },{
            "timing":timing,"pool":len(pool),
            "approved":len(approved),"novel_dense_top24":sum(i not in bset for i in denseids[:DENSE_POOL]),
            "novel_source_selected":bool(approved and approved[0] not in bset),
            "changed":dual[:10]!=bmids[:10],
            "first_bm25_reviewer":blind.get(bmids[0],None)
        }

def eval_dataset(name,folder,output,embedder,critic,limit=0):
    docs,queries,gold=load_dev_only(folder,name)
    selected=[qid for qid in sorted(gold) if qid in queries and inner_part(name,qid)=="validate"]
    if limit:selected=selected[:limit]
    t=time.perf_counter();system=EvidenceSystem(docs,embedder,critic)
    print(f"{name}: docs={len(docs)} validate={len(selected)} "
          f"embedding_index_s={system.encode_seconds:.1f} "
          f"index_total_s={time.perf_counter()-t:.1f}",flush=True)
    observed=collections.defaultdict(list)
    summaries=[]
    for index,qid in enumerate(selected):
        rankings,diag=system.evaluate_one(queries[qid])
        for method,ids in rankings.items():
            actual=[system.bm.ids[i] for i in ids]
            score=measures(actual,gold[qid])
            observed[method].append({"qid":qid,"method":method,**score,
                "time_bm25_ms":diag["timing"]["bm25_ms"],
                "time_dense_ms":diag["timing"]["dense_ms"],
                "time_blind_ms":diag["timing"]["blind_ms"],
                "time_context_ms":diag["timing"]["context_ms"],
                "approved":diag["approved"],
                "changed":diag["changed"],
                "new_source_selected":diag["novel_source_selected"],
                "novel_dense_top24":diag["novel_dense_top24"]})
        if (index+1)%20==0:print(f"{name}: evaluated {index+1}/{len(selected)}",flush=True)
    base={q["qid"]:q for q in observed["bm25"]}
    for method,rows in observed.items():
        gains=[q["ndcg10"]-base[q["qid"]]["ndcg10"] for q in rows]
        s={"dataset":name,"method":method,"split":"dev-validation","n":len(rows),
          "metrics":{key:float(np.mean([q[key] for q in rows])) for key in ["ndcg10","recall10","recall100","mrr10"]},
          "wins":sum(a>1e-10 for a in gains),"losses":sum(a< -1e-10 for a in gains),
          "ties":sum(abs(a)<=1e-10 for a in gains),
          "time_ms":{key:float(np.mean([q[key] for q in rows])) for key in
                 ["time_bm25_ms","time_dense_ms","time_blind_ms","time_context_ms"]},
          "approved":sum(q["approved"]>0 for q in rows),
          "rank_changes":sum(q["changed"] for q in rows),
          "found_new_dense_sources":sum(q["novel_dense_top24"] for q in rows),
          "index_seconds":system.encode_seconds,
          "model_versions":{"dense":EMBED_MODEL,"blind":REVIEW_MODEL}}
        summaries.append(s)
        with (output/f"{name}_{method}_per_query.jsonl").open("w") as f:
            for row in rows:f.write(json.dumps(row)+"\n")
        print(f'{name}/{method}: ndcg10={s["metrics"]["ndcg10"]:.4f} '
              f'recall10={s["metrics"]["recall10"]:.4f} '
              f'wins/loss={s["wins"]}/{s["losses"]}',flush=True)
    return summaries

def smoke():
    x=[{"_id":"a","title":"Light","text":"Sunlight affects plants through photosynthesis."},
       {"_id":"b","title":"Stars","text":"Stars emit electromagnetic radiation."},
       {"_id":"c","title":"Farming","text":"Soil affects plant growth."}]
    idx=Retriever(x)
    first=[i for i,_ in idx.search("sunlight affects plants","bm25")]
    diag=context_review(idx,"sunlight affects plants",first,first[0])
    assert set(diag)=={"gap","coverage","fills","novelty","support"}
    assert 0<=diag["support"]<=1.1
    assert sigmoid(-1000)<sigmoid(0)<sigmoid(1000)
    assert partition("scifact","a") in ("dev","sealed")
    assert inner_part("scifact","a") in ("fit","validate")
    print("V6.3 SMOKE PASS",flush=True)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("command",choices=["smoke","dev-validation"])
    ap.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v63"))
    ap.add_argument("--data",type=pathlib.Path,default=pathlib.Path("data"))
    ap.add_argument("--limit",type=int,default=0)
    args=ap.parse_args()
    if args.command=="smoke":smoke();sys.exit(0)
    from sentence_transformers import SentenceTransformer,CrossEncoder
    args.out.mkdir(parents=True,exist_ok=True)
    torch.manual_seed(2026)
    start=time.perf_counter()
    embedder=SentenceTransformer(EMBED_MODEL,device="cpu")
    critic=CrossEncoder(REVIEW_MODEL,max_length=CE_MAX_LEN,device="cpu")
    print("Models loaded in seconds:",round(time.perf_counter()-start,1),flush=True)
    data=[]
    for name in BENCHMARKS:
        data.extend(eval_dataset(name,download(name,args.data),args.out,embedder,critic,args.limit))
    (args.out/"summary.json").write_text(json.dumps({
        "version":"6.3","reviewer_type":"independent open-weight evidence scorers, not LLM agents",
        "preregistered_parameters":{"bm25_pool":BM25_POOL,"dense_pool":DENSE_POOL,
             "gap":GAP_MASS_THRESHOLD,"support":REVIEWER_SUPPORT_THRESHOLD,
             "blind_advantage":BLIND_ADVANTAGE_THRESHOLD,
             "novelty":DENSE_SOURCE_NOVELTY_THRESHOLD},
        "validation":data,"sealed_answers_used":False,
        "known_limits":["No answer generator","No true factual entailment verifier",
           "No proof of novelty","Latency is CPU model inference, not API billing"]
    },indent=2))
    print("COMPLETE: Saved",args.out/"summary.json",flush=True)
