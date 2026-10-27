#!/usr/bin/env python3
"""V7 honest first-stage head-to-head: retrieval-only on pooled 2WikiMultiHopQA.
BM25, TF-IDF, open-weight dense, hybrid RRF, title-link walk, and ORIGINAL
proof-gap hypothesis (a selective link-follow-up). IRCoT/HippoRAG2 ARE NOT
IMPLEMENTED here and no comparisons with their leaderboard scores are valid.

Dataset is the public 2WikiMultiHopQA validation pool. Questions and
supporting-title gold labels are disjoint from old HotpotQA experiments.
All methods search the exact same documents and are evaluated at same k.
No LLM generation, no paid APIs. Model/index costs reported separately.
"""
import argparse, collections, hashlib, json, pathlib, re, time, urllib.request
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer,TfidfVectorizer
from benchmark_v6 import Retriever
DATA_URL="https://huggingface.co/datasets/framolfese/2WikiMultihopQA/resolve/main/data/validation-00000-of-00001.parquet"
SEED="v7-2wikimultihop-2026-10-27"
NUM_QUESTIONS=240
DENSE_MODEL="sentence-transformers/all-MiniLM-L6-v2"

def get_records(dir):
    import pyarrow.parquet as pq
    dir.mkdir(parents=True,exist_ok=True)
    f=dir/"2wiki_validation.parquet"
    if not f.exists():
        print("Downloading original 2Wiki validation parquet from HF...",flush=True)
        urllib.request.urlretrieve(DATA_URL,f)
    table=pq.read_table(f,columns=["id","question","type","supporting_facts","context"])
    rows=table.to_pylist()
    rows.sort(key=lambda x:hashlib.sha256((SEED+"|"+str(x["id"])).encode()).digest())
    selected=[]
    for r in rows:
        ctxt=r.get("context") or {}
        titles=ctxt.get("title") or []
        passages=ctxt.get("sentences") or []
        sf=r.get("supporting_facts") or {}
        gold=set(t.strip().casefold() for t in (sf.get("title") or []) if t)
        if not titles or len(titles)!=len(passages) or len(gold)<2:continue
        available={str(t).strip().casefold() for t in titles}
        if not gold<=available:continue
        selected.append(r)
        if len(selected)>=NUM_QUESTIONS:break
    if len(selected)<NUM_QUESTIONS:raise ValueError("Insufficient complete 2Wiki records")
    return selected

def make_corpus(rows):
    # One title maps to one document, chosen without looking at supporting labels.
    # If same title has multiple paragraphs, retain the longest. This limits
    # duplicate docs that could distort ranking and evaluation.
    docs={}
    for r in rows:
        for title,sents in zip(r["context"]["title"],r["context"]["sentences"]):
            if not title:continue
            t=str(title).strip()
            body=" ".join(str(s) for s in (sents or [])).strip()
            key=t.casefold()
            if key not in docs or len(body)>len(docs[key]["text"]):
                docs[key]={"_id":key,"title":t,"text":body}
    return [docs[k] for k in sorted(docs)]

def ranked(score,docids,limit=None):
    out=np.asarray(score,dtype=np.float64).ravel()
    indices=list(range(len(out)))
    indices.sort(key=lambda i:(-float(out[i]),docids[i]))
    return indices[:limit] if limit else indices

def rrf(a,b,allids,k=60):
    r1={i:p for p,i in enumerate(a)}
    r2={i:p for p,i in enumerate(b)}
    union=set(r1)|set(r2)
    return sorted(union,key=lambda i:(-((1/(k+1+r1[i])) if i in r1 else 0)
                                      -((1/(k+1+r2[i])) if i in r2 else 0),allids[i]))

class Methods:
    def __init__(self,docs,embedder):
        self.docs=docs
        self.index=Retriever(docs)
        self.ids=self.index.ids
        self.title_lookup={d["_id"]:i for i,d in enumerate(docs)}
        self.titles=[d["title"].casefold() for d in docs]
        self.body=[d["text"].casefold() for d in docs]
        self.embedder=embedder
        start=time.perf_counter()
        self.emb=np.asarray(embedder.encode([d["title"]+" "+d["text"] for d in docs],
           batch_size=64,normalize_embeddings=True,convert_to_numpy=True,
           show_progress_bar=False),dtype=np.float32)
        self.embed_s=time.perf_counter()-start
        self.neighbors_cache={}
        print(f"Corpus {len(docs)} docs; dense embedding index {self.embed_s:.2f}s",flush=True)
    def linked(self,idx):
        if idx in self.neighbors_cache:return self.neighbors_cache[idx]
        text=self.body[idx]
        neighbors=[]
        # This is plain title-reference following; not HippoRAG2.
        for j,title in enumerate(self.titles):
            if j==idx or len(title)<5:continue
            if title in text:neighbors.append(j)
        neighbors.sort(key=lambda j:self.ids[j])
        self.neighbors_cache[idx]=neighbors
        return neighbors
    def proofgap(self,question,bmids,bmscore):
        """A bounded, selective information-need hypothesis, developed for V7.
        Only acts on observed source mentions; never accesses gold labels.
        First two original results are protected (unless no candidate).
        """
        if len(bmids)<5:return bmids,{"searches":0,"changed":False}
        # Avoid investigating very confident lexical matches.
        qterms=set(self.index.words.build_analyzer()(question))
        topterms=set(self.index.words.build_analyzer()(self.docs[bmids[0]]["title"]+" "+self.docs[bmids[0]]["text"]))
        gap=len(qterms-topterms)/max(1,len(qterms))
        if gap<0.20:return bmids,{"searches":0,"changed":False}
        bset=set(bmids[:5])
        seed=bmids[:3]
        options=collections.Counter()
        for rank,i in enumerate(seed):
            for j in self.linked(i):
                if j in bset:continue
                # A source-level trail to previously unexamined evidence.
                options[j]+=1/(rank+1)
        if not options:return bmids,{"searches":1,"changed":False}
        best=None
        top=float(bmscore[bmids[0]])
        for j,link in options.items():
            title_terms=set(self.index.words.build_analyzer()(self.docs[j]["title"]))
            new_title_terms=title_terms-qterms
            score=link+0.33*float(bmscore[j])/max(1e-8,top)+0.12*min(2,len(new_title_terms))
            if best is None or (score,self.ids[j])>(best[0],self.ids[best[1]]):
                best=(score,j)
        if not best or best[0]<0.60:return bmids,{"searches":1,"changed":False}
        cand=best[1]
        proposal=bmids[:2]+[cand]+[i for i in bmids[2:] if i!=cand]
        return proposal,{"searches":1,"changed":proposal!=bmids}
    def run(self,q):
        t0=time.perf_counter()
        query=self.index.query_words.transform([q])
        bmscore=np.asarray((self.index.bm@query.T).toarray()).ravel()
        bmids=ranked(bmscore,self.ids)
        ms_bm=(time.perf_counter()-t0)*1000
        t1=time.perf_counter()
        tfscore=np.asarray((self.index.tf@self.index.tfidf.transform([q]).T).toarray()).ravel()
        tfids=ranked(tfscore,self.ids)
        ms_tf=(time.perf_counter()-t1)*1000
        t2=time.perf_counter()
        emb=np.asarray(self.embedder.encode([q],normalize_embeddings=True,convert_to_numpy=True),dtype=np.float32).reshape(-1)
        den_ids=ranked(self.emb@emb,self.ids)
        ms_dense=(time.perf_counter()-t2)*1000
        t3=time.perf_counter()
        hybrid=rrf(bmids,den_ids,self.ids)
        ms_hybrid=(time.perf_counter()-t3)*1000
        t4=time.perf_counter()
        proof,info=self.proofgap(q,bmids,bmscore)
        ms_proof=(time.perf_counter()-t4)*1000
        # Non-LLM title-link traversal baseline, no separate reviewer.
        t5=time.perf_counter()
        counts=collections.Counter()
        for rank,i in enumerate(bmids[:3]):
            for j in self.linked(i):counts[j]+=1/(rank+1)
        graph=sorted(range(len(self.ids)),key=lambda i:(-(1/(61+bmids.index(i))+0.012*counts[i]),self.ids[i]))
        ms_graph=(time.perf_counter()-t5)*1000
        return {"bm25":bmids,"tfidf":tfids,"dense":den_ids,"hybrid":hybrid,
                "title_link_baseline":graph,"proofgap_v7":proof},{
             "ms_bm":ms_bm,"ms_tf":ms_tf,"ms_dense":ms_dense,
             "ms_hybrid":ms_hybrid,"ms_graph":ms_graph,"ms_proof":ms_proof,
             "proof_searches":info["searches"],"proof_changed":info["changed"]}

def chain_scores(ranks,gold,doc_ids):
    got=[doc_ids[i] for i in ranks]
    return {f"chain_at_{k}":int(gold<=set(got[:k])) for k in (2,3,5,10)},{
        f"evidence_recall_at_{k}":len(gold&set(got[:k]))/len(gold) for k in (2,3,5,10)}

def run(args):
    tstart=time.perf_counter()
    rows=get_records(args.data)
    docs=make_corpus(rows)
    from sentence_transformers import SentenceTransformer
    import torch
    torch.set_num_threads(2)
    model=SentenceTransformer(DENSE_MODEL,device="cpu")
    engine=Methods(docs,model)
    # Development/validation partition is fixed before any results.
    questions=[{"id":str(r["id"]),"question":r["question"],"type":r.get("type","unknown"),
       "gold":sorted({str(t).strip().casefold() for t in r["supporting_facts"]["title"]}),
       "difficulty":"3+ sources" if len(set(str(t).strip().casefold() for t in r["supporting_facts"]["title"]))>=3 else "2 sources"} for r in rows]
    args.out.mkdir(parents=True,exist_ok=True)
    records=[]
    for qn,row in enumerate(questions):
        rank,diag=engine.run(row["question"])
        gold=set(row["gold"])
        if not gold<=set(engine.ids):raise ValueError("Gold not in shared corpus")
        for method,ids in rank.items():
            complete,partial=chain_scores(ids,gold,engine.ids)
            records.append({"id":row["id"],"type":row["type"],"difficulty":row["difficulty"],
                 "method":method,"gold_count":len(gold),**complete,**partial,
                 "time_ms":diag, "question_index":qn})
        if (qn+1)%40==0:print(f"Completed {qn+1}/{len(questions)} questions",flush=True)
    output={}
    for method in sorted(set(r["method"] for r in records)):
        r=[x for x in records if x["method"]==method]
        metrics={k:float(np.mean([x[k] for x in r])) for k in
           ["chain_at_2","chain_at_3","chain_at_5","chain_at_10","evidence_recall_at_2","evidence_recall_at_5","evidence_recall_at_10"]}
        output[method]={"n":len(r),"metrics":metrics,
             "by_difficulty":{label:{"n":len([x for x in r if x["difficulty"]==label]),
                "chain_at_5":float(np.mean([x["chain_at_5"] for x in r if x["difficulty"]==label]))}
                for label in sorted(set(x["difficulty"] for x in r))}}
        print(method, "chain@5",f'{metrics["chain_at_5"]:.4f}',
              "evidence_recall@5",f'{metrics["evidence_recall_at_5"]:.4f}',flush=True)
    per_question={}
    for x in records:
        per_question.setdefault(x["id"],{})[x["method"]]=x["chain_at_5"]
    base={x["id"]:x for x in records if x["method"]=="bm25"}
    for method in output:
        if method=="bm25":continue
        gain=sum(per_question[q][method]>per_question[q]["bm25"] for q in per_question)
        lose=sum(per_question[q][method]<per_question[q]["bm25"] for q in per_question)
        output[method]["paired_wins_vs_bm25"]=gain;output[method]["paired_losses_vs_bm25"]=lose
    firstmethod=[x for x in records if x["method"]=="bm25"]
    ms={name:float(np.mean([r["time_ms"][name] for r in firstmethod])) for name in
        ["ms_bm","ms_tf","ms_dense","ms_hybrid","ms_graph","ms_proof"]}
    proof_queries=sum(r["time_ms"]["proof_searches"] for r in firstmethod)
    changed=sum(r["time_ms"]["proof_changed"] for r in firstmethod)
    report={"setup":{"dataset":"framolfese/2WikiMultihopQA validation (repackaged official)",
       "data_source":DATA_URL,"selection_seed":SEED,"questions":len(rows),
       "documents":len(docs),"pooling":"all question-provided passages, title deduplicated; NOT full Wikipedia",
       "no_ircot_or_hipporag2_replication":True,"gold_labels_not_used_in_ranking":True,
       "no_final_answer_generation":True,"dense_model":DENSE_MODEL,
       "sealed_test_not_used":True,
       "num_gold_support_sources":dict(collections.Counter(q["difficulty"] for q in questions))},
       "methods":output,"latency_ms_per_question":ms,
       "extra_index_embedding_seconds":engine.embed_s,
       "proofgap_link_searches":proof_queries,"proofgap_rank_changes":changed,
       "elapsed_total_s":time.perf_counter()-tstart}
    (args.out/"summary.json").write_text(json.dumps(report,indent=2))
    with (args.out/"per_question.jsonl").open("w") as f:
        for x in records:f.write(json.dumps(x)+"\n")
    print("COMPLETE",flush=True)

def smoke():
    assert chain_scores([1,0,2],{"a","b"},["a","b","c"])[0]["chain_at_2"]==1
    assert chain_scores([2,0,1],{"a","b"},["a","b","c"])[0]["chain_at_2"]==0
    assert len(rrf([0,1,2],[2,0,1],["a","b","c"]))==3
    print("V7 SMOKE PASS")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=["smoke","run"])
    p.add_argument("--data",type=pathlib.Path,default=pathlib.Path("data"))
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v7"))
    a=p.parse_args()
    if a.command=="smoke":smoke()
    else:run(a)
