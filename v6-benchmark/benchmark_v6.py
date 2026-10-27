#!/usr/bin/env python3
"""Truth-Seeking V6: reproducible BEIR *development-only* retrieval comparison.
No paid API, no use of relevance judgments in search or method selection at query time.
Sealed partition is NEVER scored by this script.
"""
import argparse, collections, hashlib, json, math, os, pathlib, time, urllib.request, zipfile
import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer, ENGLISH_STOP_WORDS

SETS={
 "scifact":("5f7d1de60b170fc8027bb7898e2efca1",300),
 "nfcorpus":("a89dba18a62ef92f7d323ec890a0d38d",323)
}
ROOT="https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets"
SEED="v6-crossdomain-2026-10-27"

def partition(dataset,qid):
    digest=hashlib.sha256((SEED+"|"+dataset+":"+qid).encode()).digest()
    return "dev" if int.from_bytes(digest[:8],"big")%2==0 else "sealed"

def download(name,dest):
    dest.mkdir(parents=True,exist_ok=True)
    folder=dest/name
    if (folder/"corpus.jsonl").exists():return folder
    archive=dest/(name+".zip")
    if not archive.exists():
        url=ROOT+"/"+name+".zip"
        print("Downloading "+url,flush=True)
        urllib.request.urlretrieve(url,archive)
    checksum=hashlib.md5(archive.read_bytes()).hexdigest()
    if checksum!=SETS[name][0]:raise ValueError(f"Checksum mismatch for {name}: {checksum}")
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            if not (dest/member.filename).resolve().is_relative_to(dest.resolve()):
                raise ValueError("Unsafe archive path")
        z.extractall(dest)
    if not (folder/"corpus.jsonl").exists():raise FileNotFoundError(folder/"corpus.jsonl")
    return folder

def jsonl(filename):
    with open(filename,encoding="utf8") as f:
        for line in f:
            if line.strip():yield json.loads(line)

def load(folder):
    documents=list(jsonl(folder/"corpus.jsonl"))
    queries={x["_id"]:x["text"] for x in jsonl(folder/"queries.jsonl")}
    qrels=collections.defaultdict(dict)
    with open(folder/"qrels"/"test.tsv",encoding="utf8") as f:
        header=f.readline().strip().split("\t")
        if header[:3]!=["query-id","corpus-id","score"]:
            raise ValueError("Unexpected qrels header")
        for line in f:
            q,d,v=line.strip().split("\t")[:3]
            if int(v)>0:qrels[q][d]=int(v)
    return documents,queries,qrels

class Retriever:
    def __init__(self,docs):
        self.ids=[d["_id"] for d in docs]
        text=[(d.get("title","")+" "+d.get("text","")).strip() for d in docs]
        self.words=CountVectorizer(stop_words="english",dtype=np.float32)
        self.count=self.words.fit_transform(text).tocsr()
        self.query_words=CountVectorizer(vocabulary=self.words.vocabulary_,binary=True)
        self.tfidf=TfidfVectorizer(stop_words="english",ngram_range=(1,2),sublinear_tf=True,dtype=np.float32)
        self.tf=self.tfidf.fit_transform(text).tocsr()
        dl=np.asarray(self.count.sum(axis=1)).reshape(-1)
        avg=max(float(dl.mean()),0.000001)
        df=np.asarray((self.count>0).sum(axis=0)).reshape(-1)
        idf=np.log(1+(len(docs)-df+0.5)/(df+0.5))
        self.idfs={term:float(idf[ix]) for term,ix in self.words.vocabulary_.items()}
        bm=self.count.copy()
        for i in range(bm.shape[0]):
            x=bm.data[bm.indptr[i]:bm.indptr[i+1]]
            bm.data[bm.indptr[i]:bm.indptr[i+1]]=x*2.2/(x+1.2*(0.25+0.75*dl[i]/avg))
        self.bm=bm.multiply(idf).tocsr()

    def search(self,question,method,cap=100):
        if method=="bm25":scores=np.asarray((self.bm@self.query_words.transform([question]).T).toarray()).ravel()
        elif method=="tfidf":scores=np.asarray((self.tf@self.tfidf.transform([question]).T).toarray()).ravel()
        else:raise ValueError(method)
        candidates=np.flatnonzero(scores>0)
        if not len(candidates):return []
        k=min(cap,len(candidates))
        shortlist=candidates[np.argpartition(scores[candidates],-k)[-k:]]
        return [(int(i),float(scores[i])) for i in sorted(shortlist,key=lambda i:(-float(scores[i]),self.ids[i]))]

def proofgap(index,question,cap=100,threshold=0.77):
    """Two-stage retrieval, searching terms missing from the first source.
    Explicitly count second search; never use reference qrels.
    """
    first=index.search(question,"bm25",cap)
    if not first:return [],1
    query=index.query_words.transform([question])
    query_terms=query.indices
    i=first[0][0]
    doc_terms=set(index.count.indices[index.count.indptr[i]:index.count.indptr[i+1]])
    covered=len([t for t in query_terms if t in doc_terms])/max(1,len(query_terms))
    if covered>=threshold:return [p for p,_ in first],1
    import re
    tokens=[w for w in re.findall(r"[a-z0-9]+",question.lower()) if len(w)>2 and w not in ENGLISH_STOP_WORDS]
    missing=[t for t in tokens if index.words.vocabulary_.get(t,-1) not in doc_terms]
    present=[t for t in tokens if index.words.vocabulary_.get(t,-1) in doc_terms]
    if not missing:return [p for p,_ in first],1
    anchor=max(present,key=lambda t:index.idfs.get(t,0),default="")
    second=index.search(" ".join(([anchor] if anchor else [])+missing),"bm25",cap)
    scores=collections.defaultdict(float)
    for r,(doc,_) in enumerate(first):scores[doc]+=1/(30+r+1)
    for r,(doc,_) in enumerate(second):scores[doc]+=0.6/(30+r+1)
    ranked=sorted(scores,key=lambda d:(-scores[d],index.ids[d]))
    return ranked[:cap],2

def measures(prediction,qrels):
    correct={k:v for k,v in qrels.items() if v>0}
    ideal=sorted(correct.values(),reverse=True)
    denom=sum((2**v-1)/math.log2(j+2) for j,v in enumerate(ideal[:10]))
    num=sum((2**correct.get(p,0)-1)/math.log2(j+2) for j,p in enumerate(prediction[:10]))
    first=next((i for i,p in enumerate(prediction[:10]) if p in correct),None)
    return {"ndcg10":num/denom if denom else 0,
        "recall10":sum(p in correct for p in prediction[:10])/max(1,len(correct)),
        "recall100":sum(p in correct for p in prediction[:100])/max(1,len(correct)),
        "mrr10":0 if first is None else 1/(first+1)}

def evaluate(name,folder,result_dir,limit=0):
    documents,queries,labels=load(folder)
    index=Retriever(documents)
    dev=[q for q in sorted(labels) if q in queries and partition(name,q)=="dev"]
    if limit:dev=dev[:limit]
    reports=[]
    result_dir.mkdir(parents=True,exist_ok=True)
    for method in ["bm25","tfidf","proofgap"]:
        rows=[]
        for number,qid in enumerate(dev):
            start=time.perf_counter()
            if method=="proofgap":ranked,calls=proofgap(index,queries[qid])
            else:ranked=[d for d,_ in index.search(queries[qid],method)];calls=1
            ms=(time.perf_counter()-start)*1000
            predicted_ids=[index.ids[d] for d in ranked]
            # Evaluation keys are NEVER passed into any retriever.
            values=measures(predicted_ids,labels[qid])
            rows.append({"id":qid,"method":method,"latency_ms":ms,"search_calls":calls,**values})
        keys=["ndcg10","recall10","recall100","mrr10","search_calls","latency_ms"]
        aggregate={key:float(np.mean([r[key] for r in rows])) if rows else None for key in keys}
        summary={"dataset":name,"partition":"dev","method":method,"number_questions":len(rows),
            "corpus_size":len(documents),"aggregate":aggregate,"split_seed":SEED}
        reports.append(summary)
        (result_dir/f"{name}_dev_{method}.json").write_text(json.dumps(summary,indent=2))
        with (result_dir/f"{name}_dev_{method}_per_question.jsonl").open("w") as f:
            for row in rows:f.write(json.dumps(row)+"\n")
        print(f'{name}/{method} nDCG@10={aggregate["ndcg10"]:.4f} R@10={aggregate["recall10"]:.4f} calls={aggregate["search_calls"]:.2f}',flush=True)
    return reports

def smoke():
    d=[{"_id":"a","title":"Water","text":"Water freezes at zero Celsius."},
       {"_id":"b","title":"Stars","text":"Stars make energy in stellar cores."},
       {"_id":"c","title":"Oceans","text":"Oceans contain salt water."}]
    model=Retriever(d)
    assert model.search("freezes Celsius","bm25")[0][0]==0
    assert model.search("stars stellar","tfidf")[0][0]==1
    rr,sc=proofgap(model,"stars stellar")
    assert rr[0]==1 and sc in (1,2)
    assert partition("scifact","q1")==partition("scifact","q1")
    m=measures(["a","b"],{"a":2})
    assert m["ndcg10"]==1 and m["recall10"]==1
    print("SMOKE PASS",flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=["smoke","dev"])
    p.add_argument("--data",type=pathlib.Path,default=pathlib.Path("data"))
    p.add_argument("--results",type=pathlib.Path,default=pathlib.Path("results"))
    p.add_argument("--datasets",nargs="+",choices=list(SETS),default=list(SETS))
    p.add_argument("--limit",type=int,default=0)
    args=p.parse_args()
    if args.command=="smoke":smoke()
    else:
        for ds in args.datasets:evaluate(ds,download(ds,args.data),args.results,args.limit)
