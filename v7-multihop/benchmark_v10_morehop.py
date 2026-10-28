#!/usr/bin/env python3
"""V10 human-verified MoreHopQA external transfer & missing-source stress.

CC-BY-4.0 dataset of 1,118 human-verified question records, official source:
https://huggingface.co/datasets/alabnii/morehopqa
Evaluation is title-level supporting-context retrieval, NOT actual answer
correctness or independently certified 5/6/8 logical-hop chain success.
A deterministic corpus blackout is imposed before indexing; no gold-derived
blackout/online features. No synthetic 8-hop validation recycled.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,pathlib,time,urllib.request
import numpy as np
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger
from benchmark_v95_controlled import two_actions,initial,paired,cpu_ms,unique
from expansion_v92 import rank_fuse

URL="https://huggingface.co/datasets/alabnii/morehopqa/resolve/main/data/with_human_verification.json"
LICENSE="CC BY 4.0"
BLACKOUT_FRACTION=15
TOP=(5,10)
METHODS=("bm25","v71_fast","v95_two_search")

def canonical_title(x):
    return " ".join(str(x).casefold().split())

def get(root):
    root.mkdir(parents=True,exist_ok=True)
    p=root/"morehopqa_verified.json"
    if not p.exists():
        req=urllib.request.Request(URL,headers={"User-Agent":"PGER-V10-Research/1.0"})
        with urllib.request.urlopen(req,timeout=360) as f:data=f.read()
        assert len(data)>10000
        tmp=p.with_suffix(".tmp");tmp.write_bytes(data);tmp.replace(p)
    raw=p.read_bytes();items=json.loads(raw)
    assert isinstance(items,list) and 700<=len(items)<=2000
    return items,hashlib.sha256(raw).hexdigest()

def parse_context(r):
    out=[]
    for p in r.get("context",[]):
        if isinstance(p,dict):
            name=p.get("title","");v=p.get("paragraphs",p.get("content",""))
        elif isinstance(p,(list,tuple)) and len(p)>=2:
            name,v=p[0],p[1]
        else:continue
        if isinstance(v,list):
            text=" ".join(str(x) for x in v)
        else:text=str(v)
        if name and text.strip():out.append((str(name).strip(),text.strip()))
    return out

def question_gold(r):
    found=[]
    for p in r.get("question_decomposition",[]):
        if isinstance(p,dict):
            label=p.get("paragraph_support_title","")
            if isinstance(label,str) and label.strip():
                found.append(canonical_title(label))
    return set(found)

def corpus(items):
    documents=[];seen=set()
    for r in items:
        for title,text in parse_context(r):
            key=title+"\n"+text
            if key in seen:continue
            seen.add(key)
            documents.append({"_id":"m"+str(len(documents)).zfill(6),
                "title":title,"text":text})
    return documents

def blackout_docs(docs,fraction):
    if fraction==0:return docs
    # Deterministic per unique source; selection is annotation/answer blind.
    keep=[]
    for d in docs:
        h=int(hashlib.sha256((d["title"]+"\n"+d["text"]).encode()).hexdigest()[:8],16)
        if h%100>=fraction:keep.append(d)
    return keep

def evaluate(items,docs,blackout,out):
    retained=blackout_docs(docs,blackout)
    t=time.process_time();sm=SparseMethods(retained);bmindex=cpu_ms(t)
    t=time.process_time();graph=EvidenceLedger(sm);graphindex=cpu_ms(t)
    available_titles={canonical_title(d["title"]) for d in retained}
    all_titles={canonical_title(d["title"]) for d in docs}
    counts=collections.Counter();per=[]
    for i,r in enumerate(items):
        q=str(r.get("question","")).strip()
        required=question_gold(r)
        decomp=r.get("question_decomposition") or []
        if not q or len(required)<2:
            counts["ineligible_no_multiple_gold_titles"]+=1;continue
        if not required<=all_titles:
            counts["ineligible_some_gold_not_in_official_context"]+=1;continue
        # Source availability known from a controlled blackout, NOT made
        # available to retrieval policies.
        available=required & available_titles
        bm,fast,base_ms=initial(q,sm,graph)
        raw=sm.index.search(q,"bm25",100)
        bm_rank=[j for j,_ in raw] or bm
        ex,actions,search_ms=two_actions(q,sm,fast)
        fuse=unique(rank_fuse(fast,bm,ex,mode="fuse",strength=.4,
                              protect=2,cutoff=150))
        rankings={"bm25":bm_rank,"v71_fast":fast,"v95_two_search":fuse}
        def metric(indices):
            pred=[canonical_title(retained[j]["title"]) for j in indices[:10]]
            return {f"title_chain_at{k}":int(required<=set(pred[:k]))
                    for k in TOP} | {f"title_recall_at{k}":
                                    len(required & set(pred[:k]))/len(required)
                                    for k in TOP}
        scored={k:metric(v) for k,v in rankings.items()}
        counts["eligible"]+=1
        if not required<=available_titles:counts["some_required_title_removed"]+=1
        try:additional=int(r.get("no_of_hops",0) or 0)
        except (TypeError,ValueError):additional=-1
        per.append({
            "id":r.get("_id",str(i)),"question":q,
            "gold_title_count":len(required),
            "decomposition_steps":len(decomp),
            "dataset_no_of_hops_field":additional,
            "gold_title_count_present":len(available),
            "all_required_title_present":int(required<=available_titles),
            "methods":scored,
            "top10":{k:[retained[j]["_id"] for j in v[:10]]
                     for k,v in rankings.items()},
            "search_actions":actions,
            "approx_cpu":{ "bm25_and_fast":base_ms,"two_expansions":search_ms}})
        if (i+1)%200==0:
            print("V10_PROGRESS",blackout,i+1,"of",len(items),flush=True)
    summaries={}
    for label in METHODS:
        rows=[p["methods"][label] for p in per]
        metrics={k:round(float(np.mean([r[k] for r in rows])),6)
                 for k in ("title_chain_at5","title_chain_at10",
                           "title_recall_at5","title_recall_at10")}
        metrics["breakdown_by_decomposition_steps"]={
          str(n):{"n":sum(p["decomposition_steps"]==n for p in per),
                  "title_chain_at5":sum(p["decomposition_steps"]==n and
                            p["methods"][label]["title_chain_at5"] for p in per)}
          for n in sorted(set(p["decomposition_steps"] for p in per))}
        metrics["breakdown_by_additional_reasoning_hops"]={
          str(n):{"n":sum(p["dataset_no_of_hops_field"]==n for p in per),
                  "title_chain_at5":sum(p["dataset_no_of_hops_field"]==n and
                            p["methods"][label]["title_chain_at5"] for p in per)}
          for n in sorted(set(p["dataset_no_of_hops_field"] for p in per))}
        for base in ("bm25","v71_fast"):
            if label!=base:
                metrics["paired_vs_"+base]=paired(
                    [p["methods"][label]["title_chain_at5"] for p in per],
                    [p["methods"][base]["title_chain_at5"] for p in per])
        summaries[label]=metrics
    result={"stage":"V10","dataset":"MoreHopQA human-verified",
            "blackout_percent":blackout,
            "dataset_license":LICENSE,"dataset_url":URL,
            "n_raw":len(items),"n_documents_before_blackout":len(docs),
            "n_documents_after_blackout":len(retained),
            "coverage_audit":dict(counts),
            "cpu_offline_index_ms":{"bm25":bmindex,"title_graph":graphindex},
            "methods":summaries,
            "warnings":[
             "Source title identities from question decomposition are NOT exact passage-level gold evidence",
             "Dataset no_of_hops field describes extra reasoning, not certified 5/6/8 document hops",
             "Only questions with at least two support titles present in original pooled corpus evaluated",
             "Gold-based inclusion is offline evaluation filtering, not online retrieval routing",
             "Blackout is deterministic SHA source removal, blind to question/gold annotations",
             "Missing gold title makes complete chain retrieval mathematically impossible",
             "There is no answer generator, relation-entailment checker, calibrated abstention or 8+ hop proof",
             "External human verification applies to dataset, not our model outputs",
             "Pooled contextual corpus differs from SAG2 and open-world web retrieval",
             "All reported title-chain metrics and CPU are not directly comparable to SAG2 complete passage-chain@5"
            ]}
    out.mkdir(parents=True,exist_ok=True)
    name="blackout_"+str(blackout)
    (out/(name+"_summary.json")).write_text(json.dumps(result,indent=2))
    with (out/(name+"_cases.jsonl")).open("w") as f:
        for item in per:f.write(json.dumps(item,ensure_ascii=False)+"\n")
    print("V10_RESULT",blackout,json.dumps(result),flush=True)
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("smoke","run"))
    p.add_argument("--data",type=pathlib.Path,default=pathlib.Path("data/morehop_verified"))
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v10"))
    a=p.parse_args()
    if a.command=="smoke":
        row={"question_decomposition":[{"paragraph_support_title":"A"},
                  {"paragraph_support_title":"B"}],
             "context":[["A",["One sentence"]],["B",["Second sentence"]]]}
        assert question_gold(row)=={"a","b"}
        assert len(parse_context(row))==2
        print("V10 MoreHopQA loader smoke PASS");return
    items,sha=get(a.data)
    docs=corpus(items)
    assert len(docs)>100
    source={"dataset_sha256":sha,"release_url":URL,
            "document_count":len(docs),"records":len(items)}
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/"source_manifest.json").write_text(json.dumps(source,indent=2))
    for pct in (0,BLACKOUT_FRACTION):
        evaluate(items,docs,pct,a.out)
    print("V10 HUMAN-VERIFIED EXTERNAL DATASET AND SOURCE-BLACKOUT AUDIT FINISHED",flush=True)

if __name__=="__main__":main()
