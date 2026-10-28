#!/usr/bin/env python3
"""Run unchanged V7.1 BM25 + Aho-Corasick 1-hop graph on EXACT SAG2 corpus/questions.
SAG2 comparison is authors' archived scores only: no JEV API or paid inference.
"""
import argparse,hashlib,json,pathlib,time,urllib.request
import numpy as np
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger

REV="5ec05b38deecc3318bb432c69865959c56058990"
BASE="https://huggingface.co/datasets/osunlp/HippoRAG_2/resolve/"+REV+"/"
REF={"2wikimultihopqa":(6119,.9735,.97425,.929,.931),
     "musique":(11656,.80675,.8661666667,.59,.695),
     "hotpotqa":(9811,.9845,.99,.97,.981)}
SEED=20261028

def get(name,root):
    root.mkdir(parents=True,exist_ok=True);hashes={}
    for suffix in (".json","_corpus.json"):
        p=root/(name+suffix)
        if not p.exists():
            req=urllib.request.Request(BASE+name+suffix,headers={"User-Agent":"PGER-V71-SAG2/1.0"})
            with urllib.request.urlopen(req,timeout=360) as f:data=f.read()
            assert len(data)>1000 and isinstance(json.loads(data),list)
            tmp=pathlib.Path(str(p)+".tmp");tmp.write_bytes(data);tmp.replace(p)
        hashes[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
    return hashes

def load(name,root):
    corpus=json.loads((root/(name+"_corpus.json")).read_text())
    samples=json.loads((root/(name+".json")).read_text())
    # Identical to official SAG2 DatasetLoader.get_docs canonical source strings.
    uniq={}
    for row in corpus:
        title=str(row["title"]).strip();body=str(row["text"])
        src=title+"\n"+body
        if src not in uniq:uniq[src]={"_id":"d"+str(len(uniq)).zfill(6),"title":title,"text":body}
    records=[]
    for x in samples:
        if name=="musique":
            gold=[p["title"]+"\n"+(p.get("paragraph_text") or p.get("text") or "")
                  for p in x["paragraphs"] if p["is_supporting"]]
        else:
            titles={sf[0] for sf in x["supporting_facts"]}
            sep="" if name=="hotpotqa" else " "
            gold=[title+"\n"+sep.join(sentences) for title,sentences in x["context"] if title in titles]
        records.append({"id":str(x.get("_id",x.get("id"))),"q":x["question"].strip(),
                        "gold":list(dict.fromkeys(gold))})
    return uniq,records

def boot(a,b):
    d=np.asarray(a)-np.asarray(b);rng=np.random.default_rng(SEED)
    draws=[float(d[rng.integers(0,len(d),size=len(d))].mean()) for _ in range(4000)]
    return {"delta_pp":round(float(d.mean()*100),3),
      "ci95_pp":[round(float(v*100),3) for v in np.quantile(draws,[.025,.975])],
      "wins":int(sum(d>0)),"losses":int(sum(d<0))}

def evaluate(name,root,out,limit=0):
    files=get(name,root);uniq,questions=load(name,root)
    source=list(uniq);docs=list(uniq.values());expected=REF[name]
    if len(docs)!=expected[0] or len(questions)!=1000:
        raise AssertionError(f"Corpus/questions mismatch: {name}: {len(docs)} docs, {len(questions)} questions; expected {expected[0]}/1000")
    srcset=set(source);missing=sum(g not in srcset for x in questions for g in x["gold"])
    t=time.perf_counter();methods=SparseMethods(docs);index_s=time.perf_counter()-t
    t=time.perf_counter();graph=EvidenceLedger(methods);graph_s=time.perf_counter()-t
    results={"bm25":[],"v71_fast":[]};rows=[];bm_times=[];graph_times=[]
    for k,rec in enumerate(questions[:limit] if limit else questions):
        q=rec["q"];gold=set(rec["gold"])
        t=time.perf_counter();hits=methods.index.search(q,"bm25",100)
        bm=[i for i,s in hits] or list(range(min(100,len(docs))))
        bm_ms=1000*(time.perf_counter()-t)
        t=time.perf_counter();fast,_=graph.search(q,bm,mode="one-hop",bmraw=hits)
        graph_ms=1000*(time.perf_counter()-t)
        bm_times.append(bm_ms);graph_times.append(graph_ms)
        scores={}
        for method,ranking in (("bm25",bm),("v71_fast",fast)):
            retrieved=[source[j] for j in ranking[:10]]
            m={f"Recall@{n}":len(gold&set(retrieved[:n]))/max(1,len(gold)) for n in (5,10)}
            m.update({f"AllEvidence@{n}":int(gold<=set(retrieved[:n])) for n in (5,10)})
            scores[method]=m;results[method].append(m)
        rows.append({"id":rec["id"],"question":q,"gold_n":len(gold),
          "gold_missing_from_corpus":sum(g not in srcset for g in gold),
          "bm25":scores["bm25"],"v71_fast":scores["v71_fast"],
          "latency_ms":{"bm25":bm_ms,"onehop_extra":graph_ms},
          "retrieved_fast_top10":[docs[j]["_id"] for j in fast[:10]]})
        if (k+1)%100==0:print(name,k+1,flush=True)
    fields=["Recall@5","Recall@10","AllEvidence@5","AllEvidence@10"]
    summary={m:{f:round(float(np.mean([x[f] for x in vals])),6) for f in fields} for m,vals in results.items()}
    author=dict(zip(fields,expected[1:]))
    summary_obj={"dataset":name,"question_count":len(rows),"full_corpus_docs":len(docs),
      "source_revision":REV,"source_hashes":files,"gold_not_in_corpus":missing,
      "methods":summary,"sag2_published_not_rerun":author,
      "paired_v71_minus_bm25":{f:boot([x[f] for x in results["v71_fast"]],
                                         [x[f] for x in results["bm25"]]) for f in fields},
      "indexing_seconds":{"original_sparse_bm25_plus_tfidf":round(index_s,3),"title_graph":round(graph_s,3)},
      "query_ms":{"bm25_mean":round(float(np.mean(bm_times)),3),
                  "bm25_p95":round(float(np.percentile(bm_times,95)),3),
                  "graph_extra_mean":round(float(np.mean(graph_times)),3),
                  "graph_extra_p95":round(float(np.percentile(graph_times,95)),3)},
      "limitations":["This run does NOT independently run paid SAG2 JEV model; its result is from authors' archived 1000-question records",
        "Identical source corpus and question IDs, matching passage metric; algorithms and serving hardware differ",
        "Data are fixed public development subsets, not sealed final generalization",
        "CPU query timing after indexing, not a comparable provider-side SAG2 latency or production cost"]}
    out.mkdir(parents=True,exist_ok=True)
    (out/(name+"_summary.json")).write_text(json.dumps(summary_obj,indent=2))
    with (out/(name+"_per_question.jsonl")).open("w") as f:
        for row in rows:f.write(json.dumps(row,ensure_ascii=False)+"\n")
    print(name,"FINISHED",json.dumps(summary),flush=True)
    return summary_obj

def smoke():
    docs=[{"_id":"a","title":"Alpha Person","text":"Alpha Person was born in Beta Town."},
      {"_id":"b","title":"Beta Town","text":"Beta Town is located in Gamma Country."}]
    sm=SparseMethods(docs);g=EvidenceLedger(sm);hits=sm.index.search("Alpha Person birthplace","bm25")
    rank,_=g.search("Alpha Person birthplace",[i for i,s in hits],mode="one-hop",bmraw=hits)
    assert rank and len(set(rank))==len(rank)
    print("SAG2 official-corpus adapter smoke PASS")

def main():
    p=argparse.ArgumentParser();p.add_argument("command",choices=["smoke","run"])
    p.add_argument("--datasets",nargs="+",choices=list(REF),default=list(REF))
    p.add_argument("--data",type=pathlib.Path,default=pathlib.Path("data/sag2_official"))
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v71-sag2"))
    p.add_argument("--limit",type=int,default=0)
    a=p.parse_args()
    if a.command=="smoke":return smoke()
    out=[evaluate(n,a.data,a.out,a.limit) for n in a.datasets]
    (a.out/"summary.json").write_text(json.dumps({"datasets":out},indent=2))
    print("V7.1 ON FULL SAG2 QUESTION/CORPUS EVALUATION COMPLETE",flush=True)
if __name__=="__main__":main()
