#!/usr/bin/env python3
"""PGER V9.6B fixed-pool chain-assembly, NOT a verified relation engine.

Single controlled change: rank documented title-mention connections within
a shared, fixed two-BM25-search candidate pool. This tests whether extra
source-to-source evidence structure improves chain assembly. It is distinct
from source discovery, but mere text presence is NOT entailment. Prior V8.5
failure means no novelty claim. Freeze before confirmation.

Development offsets 400:520; additional confirmation 520:640; public corpus
has already been evaluated in earlier V7.1 work. All source identities and
gold annotations are used only AFTER ranking for post-hoc evaluation.
"""
import argparse,collections,hashlib,json,pathlib,re,time
import numpy as np
from benchmark_v71_sag2_corpus import download,official_records,SAG2_AUTHOR,RELEASE
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger
from benchmark_v95_controlled import initial,two_actions,unique,metric,paired,cpu_ms
from expansion_v92 import rank_fuse,terms

DEV=(400,520)
CONF=(520,640)
K=5
POOL_MAX=110
M=("v71_fast","two_query_fusion","independent_diversity","source_witness_chain")
NEG=re.compile(r"\b(?:not|never|no|neither|without|incorrectly|formerly|allegedly)\b",re.I)
SENTS=re.compile(r"(?<=[.!?])\s+|\n+")
CONNECT_BONUS=.020
QUERY_GAP_BONUS=.013
WITNESS_THRESHOLD=.5
PROTECT=1

def token_set(text):
    return set(terms(text))
def witnessed(src,target_title,qwords):
    """Return documented title-mention evidence score, not true relationship."""
    target=target_title.strip()
    if len(target)<5:return 0,None
    pattern=re.compile(r"(?<!\w)"+re.escape(target)+r"(?!\w)",re.I)
    for sentence in SENTS.split(src[:2600]):
        if not pattern.search(sentence):continue
        if NEG.search(sentence):continue
        ts=token_set(sentence)
        specificity=1.0 if qwords & ts else .6
        # This proves the title is mentioned in a specific source sentence only.
        return specificity,{"text":sentence[:400],"target":target}
    return 0,None

def make_ranking(q,docs,base,pool,kind):
    t=time.process_time()
    # fixed ordered candidate pool; retain all for complete rankings
    cand=unique([i for i in pool if i in set(base[:200])] + pool)
    # stable single pool, including candidates below 80 in original expansion
    stable={i:1.0/(25+pos) for pos,i in enumerate(base)}
    qwords=token_set(q)
    qcovered={i:token_set(docs[i]["title"]+" "+docs[i].get("text","")[:2000]) & qwords for i in cand}
    remaining=[i for i in cand if i not in base[:PROTECT]]
    selected=unique(base[:PROTECT])
    audit={"selected_witness_edges":[],"gate_used":False,"potential_edges":0}
    if kind=="independent_diversity":
        while remaining and len(selected)<10:
            seen=set().union(*(qcovered[x] for x in selected))
            def score(i):
                new=qcovered[i]-seen
                return stable.get(i,0) + QUERY_GAP_BONUS*len(new)/max(1,len(qwords))
            choice=max(remaining,key=lambda i:(score(i),-cand.index(i)))
            selected.append(choice);remaining.remove(choice)
    else:
        # Preview all recorded edges before deciding whether to activate.
        # Scans are included in CPU budget. Matched pool for both arms.
        edge={}
        for i in cand[:POOL_MAX]:
            text=docs[i].get("text","")
            for j in cand[:POOL_MAX]:
                if i==j:continue
                v,w=witnessed(text,docs[j]["title"],qwords)
                if v>=WITNESS_THRESHOLD:edge[(i,j)]=(v,w)
        audit["potential_edges"]=len(edge)
        if len(edge)<2:
            # A non-semantic graph should not overwrite a decent fast ranking.
            return unique(base),audit,cpu_ms(t)
        audit["gate_used"]=True
        while remaining and len(selected)<10:
            seen=set().union(*(qcovered[x] for x in selected))
            def eval_score(i):
                incoming=[(edge[(j,i)][0],j,edge[(j,i)][1]) for j in selected
                          if (j,i) in edge]
                outgoing=[(edge[(i,j)][0],j,edge[(i,j)][1]) for j in selected
                          if (i,j) in edge]
                witness=max([v for v,_,_ in incoming+outgoing],default=0)
                extra=len(qcovered[i]-seen)/max(1,len(qwords))
                return stable.get(i,0)+QUERY_GAP_BONUS*extra+CONNECT_BONUS*witness
            chosen=max(remaining,key=lambda i:(eval_score(i),-cand.index(i)))
            for prior in selected:
                if (prior,chosen) in edge:
                    v,w=edge[(prior,chosen)]
                    audit["selected_witness_edges"].append({
                        "from":docs[prior]["_id"],"to":docs[chosen]["_id"],
                        "quote":w["text"],"source_quote_hash":hashlib.sha256(
                         docs[prior].get("text","").encode()).hexdigest(),
                         "lexical_only":True})
            selected.append(chosen);remaining.remove(chosen)
    return unique(selected+base+pool),audit,cpu_ms(t)

def evaluate(name,root,out):
    hashes=download(name,root);ident,docs,questions=official_records(name,root)
    assert len(docs)==SAG2_AUTHOR[name]["corpus"] and len(questions)==1000
    source=list(ident)
    t=time.process_time();bm=SparseMethods(docs);bm_build=cpu_ms(t)
    t=time.process_time();graph=EvidenceLedger(bm);graph_build=cpu_ms(t)
    for split,(start,end) in (("development",DEV),("confirmation",CONF)):
        cases=[]
        for x,row in enumerate(questions[start:end]):
            q=row["question"]
            original,fast,fastcost=initial(q,bm,graph)
            hits,actions,searchcost=two_actions(q,bm,fast)
            t=time.process_time()
            fused=unique(rank_fuse(fast,original,hits,mode="fuse",strength=.4,
                                   protect=2,cutoff=150))
            fusecost=cpu_ms(t)
            pool=unique(fused[:80]+fast[:80]+original[:80]+[
                i for h in hits for i in h])
            diversified,diag_div,cost_div=make_ranking(q,docs,fused,pool,"independent_diversity")
            witnessed_rank,diag_wit,cost_wit=make_ranking(q,docs,fused,pool,"source_witness_chain")
            rankings={"v71_fast":fast,"two_query_fusion":fused,
                      "independent_diversity":diversified,
                      "source_witness_chain":witnessed_rank}
            # NO gold available to ranking procedures; only audit from here.
            gold=set(row["gold"]);assert gold and gold<=set(source)
            def as_src(indices):return {source[i] for i in indices}
            cases.append({
                "id":row["id"],"question":q,"support_count":len(gold),
                "metrics":{k:metric(v,source,gold) for k,v in rankings.items()},
                "pool_full_gold":int(gold<=as_src(pool)),
                "pool_recall":len(gold & as_src(pool))/len(gold),
                "pool_n":len(pool),
                "search_actions":actions,
                "witness_audit":diag_wit,
                "timing_ms_estimate":{
                    "v71_fast":fastcost,
                    "two_query_fusion":fastcost+searchcost+fusecost,
                    "independent_diversity":fastcost+searchcost+fusecost+cost_div,
                    "source_witness_chain":fastcost+searchcost+fusecost+cost_wit},
                "top10_doc_ids":{k:[docs[i]["_id"] for i in v[:10]]
                                 for k,v in rankings.items()}})
            if (x+1)%40==0:print("PROGRESS",name,split,x+1,flush=True)
        stats={}
        for m in M:
            s={k:round(float(np.mean([r["metrics"][m][k] for r in cases])),6)
               for k in ("ae5","ae10","r5","r10")}
            s["mean_cpu_ms_estimate"]=round(float(np.mean(
                [r["timing_ms_estimate"][m] for r in cases])),3)
            s["by_support"]={str(n):{"n":sum(r["support_count"]==n for r in cases),
                "ae5":sum(r["support_count"]==n and r["metrics"][m]["ae5"]
                         for r in cases)} for n in sorted(set(r["support_count"] for r in cases))}
            for control in ("v71_fast","two_query_fusion","independent_diversity"):
                if m!=control:s["paired_vs_"+control]=paired(
                    [r["metrics"][m]["ae5"] for r in cases],
                    [r["metrics"][control]["ae5"] for r in cases])
            stats[m]=s
        output={"stage":"V9.6B","dataset":name,"split":split,"range":[start,end],
                "sha256":hashes,"release":RELEASE,"index_cpu_ms":{
                    "bm25":bm_build,"graph":graph_build},
                "candidate_pool_full_gold":sum(x["pool_full_gold"] for x in cases),
                "candidate_pool_average_gold_recall":round(float(np.mean(
                    [x["pool_recall"] for x in cases])),6),
                "witness_gate_activations":sum(x["witness_audit"]["gate_used"] for x in cases),
                "methods":stats,"limits":{
                    "no_gold_for_ranking":True,"max_extra_searches":2,
                    "public_previously_evaluated":True,
                    "quote_match_not_entailment":True,
                    "candidate_pool_identical_for_all_extra_arms":True,
                    "index_build_not_in_query_ms":True}}
        out.mkdir(parents=True,exist_ok=True)
        p=name+"_"+split
        (out/(p+"_summary.json")).write_text(json.dumps(output,indent=2))
        with (out/(p+"_cases.jsonl")).open("w") as f:
            for r in cases:f.write(json.dumps(r,ensure_ascii=False)+"\n")
        print("STAGE_RESULT",name,split,json.dumps(output["methods"]),flush=True)

def smoke():
    d=[{"_id":"a","title":"Foo","text":"Alpha Borough is located in Bravo Town."},
       {"_id":"b","title":"Bravo Town","text":"Bravo Town was founded by Charles."},
       {"_id":"c","title":"Charles","text":"Charles moved."}]
    b=[0,1,2];rank,diag,ms=make_ranking("Who founded Bravo Town",d,b,b,"source_witness_chain")
    assert len(set(rank))==len(rank) and ms>=0
    assert "potential_edges" in diag
    print("V96B smoke PASS")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("smoke","run"))
    p.add_argument("--data",type=pathlib.Path,default=pathlib.Path("data/sag2_official"))
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v96b"))
    p.add_argument("--datasets",nargs="+",choices=list(SAG2_AUTHOR),default=list(SAG2_AUTHOR))
    a=p.parse_args()
    if a.command=="smoke":return smoke()
    for name in a.datasets:evaluate(name,a.data,a.out)
if __name__=="__main__":main()
