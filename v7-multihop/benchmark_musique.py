#!/usr/bin/env python3
"""V7 cross-dataset replication on MuSiQue (multi-hop evidence paragraph retrieval).

NO algorithm change: reuse the exact six Methods from benchmark_v7.py.
Unlike 2Wiki's title-level gold, this gold consists of individually supporting
paragraphs, identified by a deterministic hash of title + exact paragraph text.
No LLM answer generation, reviewer agents, or paid APIs.
"""
import argparse, collections, hashlib, json, pathlib, time, urllib.request
import numpy as np
from benchmark_v7 import Methods, chain_scores, DENSE_MODEL
URL="https://huggingface.co/datasets/awinml/musique/resolve/main/data/validation-00000-of-00001.parquet"
SEED="v7-musique-2026-10-27"
NUM=160

def id_of(par):
    title=str(par.get("title") or "").strip()
    body=str(par.get("paragraph_text") or "").strip()
    return hashlib.sha256((title.casefold()+"\x1f"+body).encode("utf8")).hexdigest()[:24]

def load_sample(outdir):
    import pyarrow.parquet as pq
    outdir.mkdir(parents=True,exist_ok=True)
    path=outdir/"musique_validation.parquet"
    if not path.exists():urllib.request.urlretrieve(URL,path)
    rows=pq.read_table(path,columns=["id","question","paragraphs","answerable"]).to_pylist()
    rows.sort(key=lambda r:hashlib.sha256((SEED+"|"+str(r["id"])).encode()).digest())
    selected=[]
    for r in rows:
        if not r.get("answerable"):continue
        p=r.get("paragraphs") or []
        gold=[q for q in p if q.get("is_supporting")]
        if 2<=len(gold)<=4 and all(q.get("title") and q.get("paragraph_text") for q in p):
            selected.append(r)
            if len(selected)>=NUM:break
    if len(selected)<NUM:raise ValueError("Need "+str(NUM)+" valid MuSiQue examples")
    return selected

def pool_documents(rows):
    docs={}
    for r in rows:
        for p in r["paragraphs"]:
            if not (p.get("title") and p.get("paragraph_text")):continue
            key=id_of(p)
            docs[key]={"_id":key,"title":str(p["title"]),"text":str(p["paragraph_text"])}
    return [docs[k] for k in sorted(docs)]

def score(rows,docs,model,output):
    system=Methods(docs,model)
    per=[]
    for idx,r in enumerate(rows):
        ranking,cost=system.run(r["question"])
        gold={id_of(p) for p in r["paragraphs"] if p.get("is_supporting")}
        if not gold<=set(system.ids):raise ValueError("Source missing from corpus")
        hops=len(gold)
        for method,indices in ranking.items():
            complete,partial=chain_scores(indices,gold,system.ids)
            per.append({"qid":str(r["id"]),"method":method,"hop_count":hops,
                **complete,**partial,"times":cost})
        if (idx+1)%40==0:print("MuSiQue evaluated",idx+1,"/",len(rows),flush=True)
    output.mkdir(parents=True,exist_ok=True)
    summaries={}
    for method in sorted(set(x["method"] for x in per)):
        arr=[x for x in per if x["method"]==method]
        summ={"n":len(arr),"chain_at_5":float(np.mean([x["chain_at_5"] for x in arr])),
           "chain_at_10":float(np.mean([x["chain_at_10"] for x in arr])),
           "recall_at_5":float(np.mean([x["evidence_recall_at_5"] for x in arr])),
           "by_hops":{str(k):{"n":sum(x["hop_count"]==k for x in arr),
                "chain_at_5":float(np.mean([x["chain_at_5"] for x in arr if x["hop_count"]==k]))}
                for k in sorted(set(x["hop_count"] for x in arr))}}
        summaries[method]=summ
        print("MuSiQue",method,"chain@5",f'{summ["chain_at_5"]:.4f}',flush=True)
    by=collections.defaultdict(dict)
    for p in per:by[p["qid"]][p["method"]]=p
    for k in summaries:
        if k=="bm25":continue
        diff=[x[k]["chain_at_5"]-x["bm25"]["chain_at_5"] for x in by.values()]
        summaries[k]["paired_wins_vs_bm25"]=sum(v>0 for v in diff)
        summaries[k]["paired_losses_vs_bm25"]=sum(v<0 for v in diff)
    original=[x for x in per if x["method"]=="bm25"]
    costs={k:float(np.mean([x["times"][k] for x in original])) for k in
       ["ms_bm","ms_tf","ms_dense","ms_hybrid","ms_graph","ms_proof"]}
    result={"setup":{"dataset":"awinml/musique validation","questions":len(rows),
       "documents":len(docs),"gold_unit":"exact supporting paragraph hash of title+text",
       "no_answer_generation":True,"no_IRCoT_HippoRAG2_run":True,
       "model":DENSE_MODEL,"reuse_v7_methods_unchanged":True,
       "question_selection":SEED,"dataset_url":URL},
       "methods":summaries,"timing_ms":costs,
       "embedding_index_s":system.embed_s}
    (output/"summary.json").write_text(json.dumps(result,indent=2))
    with (output/"per_question.jsonl").open("w") as f:
        for r in per:f.write(json.dumps(r)+"\n")
    print("MuSiQue complete",flush=True)

def smoke():
    a={"title":"X","paragraph_text":"X was born in 1960.","is_supporting":True}
    assert id_of(a)==id_of(dict(a))
    b={"id":"1","paragraphs":[a],"question":"Who"}
    docs=pool_documents([b])
    assert len(docs)==1 and docs[0]["_id"]==id_of(a)
    print("MuSiQue smoke passed",flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=["smoke","run"])
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-musique"))
    p.add_argument("--data",type=pathlib.Path,default=pathlib.Path("data"))
    args=p.parse_args()
    if args.command=="smoke":smoke()
    else:
        from sentence_transformers import SentenceTransformer
        import torch
        torch.set_num_threads(2)
        docs=load_sample(args.data)
        corpus=pool_documents(docs)
        model=SentenceTransformer(DENSE_MODEL,device="cpu")
        score(docs,corpus,model,args.out)
