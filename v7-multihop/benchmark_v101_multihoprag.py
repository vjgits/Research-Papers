#!/usr/bin/env python3
"""V10.1 external MultiHop-RAG support-document retrieval (2/3/4 sources).

Motivation: MoreHopQA V10 unexpectedly had exactly TWO unique gold titles in
all questions, so it did not test 4-support evidence despite extra reasoning.
Here require actual annotated evidence_list document identities via URL/title.
No gold used online. This benchmark is external but public, NOT sealed SOTA.

Dataset Tang & Yang (COLM 2024), ODC-BY:
https://huggingface.co/datasets/yixuantt/MultiHopRAG
"""
import argparse,collections,hashlib,json,pathlib,re,time,urllib.request
import numpy as np
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger
from benchmark_v95_controlled import two_actions,initial,paired,cpu_ms,unique
from expansion_v92 import rank_fuse

BASE="https://huggingface.co/datasets/yixuantt/MultiHopRAG/resolve/main/"
FILES=("corpus.json","MultiHopRAG.json")
SPLITS={"development":(0,400),"confirmation":(400,800)}
SOURCE_LICENSE="ODC-BY"
METHODS=("bm25","v71_fast","v95_two_query")

def norm(x):
    return re.sub(r"\s+"," ",str(x or "").casefold()).strip()

def get(folder):
    folder.mkdir(parents=True,exist_ok=True)
    hashed={};items=[]
    for name in FILES:
        p=folder/name
        if not p.exists():
            req=urllib.request.Request(BASE+name,headers={"User-Agent":"PGER-V101-2026/1.0"})
            with urllib.request.urlopen(req,timeout=360) as f:data=f.read()
            assert len(data)>10000
            tmp=p.with_suffix(p.suffix+".tmp");tmp.write_bytes(data);tmp.replace(p)
        blob=p.read_bytes();hashed[name]=hashlib.sha256(blob).hexdigest()
        items.append(json.loads(blob))
    assert all(isinstance(x,list) for x in items)
    return items[0],items[1],hashed

def body(d):
    for k in ("body","content","text","article","paragraph","description"):
        x=d.get(k)
        if isinstance(x,str) and x.strip():return x.strip()
        if isinstance(x,list) and x:return " ".join(str(v) for v in x)
    return ""

def make_corpus(original):
    docs=[];seen=set()
    for idx,row in enumerate(original):
        title=str(row.get("title","")).strip()
        content=body(row)
        if not title or not content:continue
        url=str(row.get("url","")).strip()
        key=url if url else (title+"\n"+content)
        if key in seen:continue
        seen.add(key)
        docs.append({"_id":"news"+str(len(docs)).zfill(5),
                     "title":title,"text":content,
                     "url":url,"source":row.get("source",""),
                     "original_index":idx})
    return docs

def map_gold(item,docs):
    by_url=collections.defaultdict(list)
    by_title=collections.defaultdict(list)
    for j,d in enumerate(docs):
        if d["url"]:by_url[norm(d["url"])].append(j)
        by_title[norm(d["title"])].append(j)
    evid=item.get("evidence_list",[])
    if isinstance(evid,str):
        try:evid=json.loads(evid)
        except: evid=[]
    if isinstance(evid,dict):evid=[evid]
    evidence=[]
    flags=[]
    for e in evid if isinstance(evid,list) else []:
        if isinstance(e,str):
            try:e=json.loads(e)
            except:e={"title":e}
        if not isinstance(e,dict):continue
        url=norm(e.get("url",""))
        title=norm(e.get("title",""))
        matches=by_url.get(url,[]) if url else []
        how="exact_url" if matches else None
        if not matches and title and len(by_title.get(title,[]))==1:
            matches=by_title[title];how="unique_title_fallback"
        if len(matches)==1:
            evidence.append(matches[0]);flags.append(how)
        else:
            flags.append("unresolved_evidence_identity")
    return set(evidence),flags,len(evid) if isinstance(evid,list) else 0

def eval_dataset(raw_corpus,questions,hashes,out):
    docs=make_corpus(raw_corpus)
    assert len(docs)>100 and len(questions)>800
    t=time.process_time();sm=SparseMethods(docs);bm_index=cpu_ms(t)
    t=time.process_time();graph=EvidenceLedger(sm);graph_index=cpu_ms(t)
    for split,(start,end) in SPLITS.items():
        cases=[];skip=collections.Counter()
        for r in questions[start:end]:
            q=str(r.get("query",r.get("question",""))).strip()
            if not q:
                skip["no_question"]+=1;continue
            gold,flags,orig=len([]),[],0
            # Offline annotation resolution. This may run before retrieval,
            # but gold is never passed to or consulted by retrieval methods.
            gold,flags,orig=map_gold(r,docs)
            if (orig<2 or len(gold)!=orig or
                "unresolved_evidence_identity" in flags):
                skip["ambiguous_or_missing_gold_identity"]+=1;continue
            bm,fast,fastms=initial(q,sm,graph)
            rawbm=sm.index.search(q,"bm25",100)
            base=[i for i,_ in rawbm] or bm
            hits,actions,expand_ms=two_actions(q,sm,fast)
            t=time.process_time()
            fused=unique(rank_fuse(fast,bm,hits,mode="fuse",strength=.4,
                                   protect=2,cutoff=150))
            scorems=cpu_ms(t)
            ranking={"bm25":base,"v71_fast":fast,"v95_two_query":fused}
            def metric(ids):
                ranked=set(ids[:10])
                return {"ae5":int(gold<=set(ids[:5])),
                        "ae10":int(gold<=ranked),
                        "r5":len(gold&set(ids[:5]))/len(gold),
                        "r10":len(gold&ranked)/len(gold)}
            case={"question":q,"support_docs":len(gold),
                  "identity_matching":flags,
                  "metrics":{m:metric(ids) for m,ids in ranking.items()},
                  "top10_ids":{m:[docs[j]["_id"] for j in indices[:10]]
                               for m,indices in ranking.items()},
                  "extra_query_trace":actions,
                  "postindex_cpu_ms":{"v71":fastms,
                      "two_query_search":expand_ms,"fusion":scorems}}
            cases.append(case)
        summary={"stage":"V10.1","dataset":"MultiHop-RAG, Tang & Yang (COLM 2024)",
                 "source_license":SOURCE_LICENSE,"source_sha256":hashes,
                 "split":split,"question_offsets":[start,end],
                 "n_original":end-start,"n_evaluated":len(cases),
                 "n_skipped":dict(skip),
                 "corpus_documents":len(docs),
                 "index_cpu_ms":{"bm25":round(bm_index,2),
                                 "title_graph":round(graph_index,2)},
                 "methods":{}}
        assert len(cases)>=120,"Too few verified source mappings: audit schema"
        for m in METHODS:
            smet={key:round(float(np.mean([x["metrics"][m][key]
                                          for x in cases])),6)
                  for key in ("ae5","ae10","r5","r10")}
            smet["support_doc_counts"]={str(n):{
                "n":sum(x["support_docs"]==n for x in cases),
                "ae5":sum(x["support_docs"]==n and x["metrics"][m]["ae5"]
                          for x in cases)}
                for n in sorted(set(x["support_docs"] for x in cases))}
            for comp in ("bm25","v71_fast"):
                if m!=comp:
                    smet["paired_vs_"+comp]=paired(
                        [x["metrics"][m]["ae5"] for x in cases],
                        [x["metrics"][comp]["ae5"] for x in cases])
            summary["methods"][m]=smet
        summary["limitations"]=[
           "External public news article corpus, not sealed generalization",
           "Gold evidence_list document identity matched by URL or unambiguous title",
           "Original dataset may encode 2–4 source documents, not certified 5/8 logical steps",
           "No answer generator, source relation entailment, calibrated abstention",
           "Unmapped or ambiguous evidence identity excluded and counted, not silently labelled",
           "Indexing/CPU non-comparable to commercial latency or official external baselines",
           "Source metadata used only for offline gold matching, never query selection"]
        out.mkdir(parents=True,exist_ok=True)
        (out/(split+"_summary.json")).write_text(json.dumps(summary,indent=2))
        with (out/(split+"_cases.jsonl")).open("w") as f:
            for row in cases:f.write(json.dumps(row,ensure_ascii=False)+"\n")
        print("V101_RESULT",split,json.dumps(summary),flush=True)

def smoke():
    docs=[{"title":"A","url":"https://x.test/a","_id":"a"},
          {"title":"B","url":"https://x.test/b","_id":"b"}]
    q={"evidence_list":[{"title":"A","url":"https://x.test/a"},
                         {"title":"B","url":"https://x.test/b"}]}
    ids,flags,num=map_gold(q,docs)
    assert len(ids)==num==2 and flags==["exact_url","exact_url"]
    print("V10.1 URL gold-source identity smoke PASS")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("smoke","run"))
    p.add_argument("--data",type=pathlib.Path,default=pathlib.Path("data/multihoprag_pinned"))
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v101"))
    a=p.parse_args()
    if a.command=="smoke":return smoke()
    docs,questions,hashes=get(a.data)
    eval_dataset(docs,questions,hashes,a.out)

if __name__=="__main__":main()
