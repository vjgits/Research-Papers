#!/usr/bin/env python3
"""PGER V11: lexical facet support audit (not an entailment verifier).

Purpose: address 1/54 4-document external MultiHop-RAG chain@5 in V10.1.
Freeze question-facet retrieval + sentence-witness selection *before* the
development and additional public confirmation scoring. Full results by
2/3/4 distinct supporting documents with exact article identity.

No dataset labels, gold evidence, or answer text are passed to retrievers.
A lexical passage/facet overlap is NOT semantic relationship verification.
Existing decomposition, diversification, and lexical witness extraction are
prior art; no novel or state-of-the-art claim.

V10.1 question offsets 0:400 development and 400:800 confirmation; both
public, previously inspected in V10.1. No sealed generalization.
"""
import argparse,collections,hashlib,json,pathlib,re,time
import numpy as np
from benchmark_v101_multihoprag import get,make_corpus,map_gold
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger
from benchmark_v95_controlled import initial,two_actions,paired,unique,cpu_ms
from expansion_v92 import propose,rank_fuse,terms

SPLITS={"development":(0,400),"confirmation":(400,800)}
MAX_FACETS=4
BM_DEPTH=50
FAST_POOL=80
CANDBUDGET=120
SOURCE_CHARS=2200
MAX_SENTENCES=30
SENT=re.compile(r"(?<=[.!?])\s+|\n+")
CONTRAST=re.compile(r"\s*(?:[,;]\s*)?\b(?:while|whereas|meanwhile|in contrast|on the other hand|but|and also|and does|and did|and was|and is)\b[, ]*",re.I)
CLAUSE_AND=re.compile(r"\s+and\s+(?=(?:the|a|an|what|how|why|whether|does|did|was|were|is|are|which|who|in|on|at)\b)",re.I)
QUESTION_PREFIX=re.compile(r"^(?:does|do|did|is|are|was|were|what|which|who|how|when|where|whether)\s+",re.I)
METHODS=("bm25","v71_fast","v95_two_search","v11_facet2_fusion",
         "v11_facet2_witness","v11_facet4_fusion","v11_facet4_witness",
         "v11_source4_fusion")
SEED=20261028

def facet_queries(q):
    """Literal question-clause segmentation, source-agnostic and label blind."""
    parts=[x.strip(" ,;?.!") for x in CONTRAST.split(q) if x.strip(" ,;?.!")]
    if len(parts)<2:
        parts=[x.strip(" ,;?.!") for x in CLAUSE_AND.split(q) if x.strip(" ,;?.!")]
    clean=[]
    for part in parts:
        if len(terms(part))<3:continue
        k=" ".join(terms(part))
        if k not in {x[0] for x in clean}:clean.append((k,part))
    if len(clean)<2:
        # Multi-facet rule makes NO extra claims if clauses cannot be separated.
        clean=[(" ".join(terms(q)),q)]
    return [p for _,p in clean[:MAX_FACETS]]

def search_arms(q,sm,fast,bm):
    # V9.5 reference, same as V10.1.
    oldhits,oldactions,oldtime=two_actions(q,sm,fast)
    selected=facet_queries(q)
    t=time.process_time()
    results=[]
    for p in selected:
        results.append([i for i,_ in sm.index.search(p,"bm25",BM_DEPTH)])
    facet_ms=cpu_ms(t)
    # Matched four-search source-phrase alternative, no gold, frozen source.
    p4=propose(q,sm.docs,fast,sm.index.idfs,kind="mixed",seed_n=4,k=4)
    t=time.process_time()
    source4=[ [i for i,_ in sm.index.search(p["term"],"bm25",BM_DEPTH)]
             for p in p4]
    source4ms=cpu_ms(t)
    return oldhits,oldactions,oldtime,selected,results,facet_ms,p4,source4,source4ms

def candidate_pool(fast,bm,hits):
    # Same offline candidate diagnostic budget across arms.
    return unique(fast[:FAST_POOL]+bm[:FAST_POOL]+[i for hit in hits for i in hit])[:CANDBUDGET]

def fusion(fast,bm,hits):
    # Frozen reciprocal-rank-ish source list; never use a gold ID.
    return unique(rank_fuse(fast,bm,hits,mode="fuse",strength=.4,
                            protect=2,cutoff=150)+fast+bm)

def lexical_sentence_witness(text,facet,idf):
    wanted=set(terms(facet))
    if not wanted:return (0.0,"")
    denomin=max(1e-9,sum(float(idf.get(w,0)) for w in wanted))
    best=(0.0,"")
    for sentence in SENT.split(str(text)[:SOURCE_CHARS])[:MAX_SENTENCES]:
        seen=set(terms(sentence))
        coverage=sum(float(idf.get(w,0)) for w in wanted & seen)/denomin
        if coverage>best[0]:best=(float(coverage),sentence[:300])
    return best

def select_witnessed(q,docs,base,facets,hitlists,idf):
    """Fixed-pool marginal facet witness coverage, **lexical only**.

    Same inputs as facet RRF; neither method sees labels. Keep top lexical
    anchor. Upper-bound witness rescoring to first 80 fused candidates; no
    dynamic oracle invocation. Explicit source quote is retained for audit.
    """
    t=time.process_time()
    pool=unique(base[:80]+[i for hit in hitlists for i in hit[:20]])[:120]
    if not facets or not pool:
        return base,[],cpu_ms(t)
    protected=unique(base[:1])
    ranks={i:r for r,i in enumerate(base)}
    w={}
    for i in pool:
        body=docs[i]["title"]+". "+docs[i].get("text","")
        for f,p in enumerate(facets):
            w[i,f]=lexical_sentence_witness(body,p,idf)
    chosen=list(protected);audits=[]
    covered=[0.0]*len(facets)
    while len(chosen)<min(10,len(pool)):
        candidates=[i for i in pool if i not in chosen]
        if not candidates:break
        def utility(i):
            # A balanced answer needs evidence for weakly covered facets.
            marginal=sum(max(0.0,w[i,f][0]-covered[f])
                         for f in range(len(facets)))/len(facets)
            relevance=(1/(25+ranks.get(i,120)))
            return .65*marginal+.35*relevance
        nxt=max(candidates,key=lambda i:(utility(i),-ranks.get(i,1000),-i))
        for f in range(len(facets)):
            if w[nxt,f][0] > covered[f]:
                audits.append({"candidate_id":docs[nxt]["_id"],
                   "facet_index":f,"facet":facets[f],
                   "lexical_coverage":round(w[nxt,f][0],5),
                   "source_sentence":w[nxt,f][1],
                   "source_text_sha256":hashlib.sha256(
                       docs[nxt].get("text","").encode()).hexdigest(),
                   "entailment_verified":False})
                covered[f]=w[nxt,f][0]
        chosen.append(nxt)
    return unique(chosen+base),audits,cpu_ms(t)

def score(rank,gold):
    return {"ae5":int(gold<=set(rank[:5])),"ae10":int(gold<=set(rank[:10])),
            "r5":len(gold&set(rank[:5]))/len(gold),
            "r10":len(gold&set(rank[:10]))/len(gold)}

def evaluate(rawdocs,questions,hashes,out):
    docs=make_corpus(rawdocs)
    t=time.process_time();sm=SparseMethods(docs);build_bm=cpu_ms(t)
    t=time.process_time();graph=EvidenceLedger(sm);build_graph=cpu_ms(t)
    for split,(start,end) in SPLITS.items():
        per=[];skip=collections.Counter()
        for row in questions[start:end]:
            q=str(row.get("query",row.get("question",""))).strip()
            if not q:
                skip["question_missing"]+=1;continue
            gold,flags,orig=map_gold(row,docs)
            if orig<2 or len(gold)!=orig or "unresolved_evidence_identity" in flags:
                skip["gold_source_unresolved"]+=1;continue
            bm,fast,fasttime=initial(q,sm,graph)
            rawbm=sm.index.search(q,"bm25",100)
            bm=unique([i for i,_ in rawbm] or bm)
            oldhits,actions,oldms,facets,facethits,facetms,sourceacts,sourcehits,sourcems=search_arms(
                q,sm,fast,bm)
            first2=facethits[:2];first4=facethits[:4]
            t=time.process_time()
            fused2=fusion(fast,bm,first2)
            fused4=fusion(fast,bm,first4)
            fusedsrc=fusion(fast,bm,sourcehits)
            v95=fusion(fast,bm,oldhits)
            fusetime=cpu_ms(t)
            facet2w,w2,cpu2=select_witnessed(q,docs,fused2,facets[:2],first2,sm.index.idfs)
            facet4w,w4,cpu4=select_witnessed(q,docs,fused4,facets[:4],first4,sm.index.idfs)
            ranks={"bm25":bm,"v71_fast":fast,"v95_two_search":v95,
                   "v11_facet2_fusion":fused2,"v11_facet2_witness":facet2w,
                   "v11_facet4_fusion":fused4,"v11_facet4_witness":facet4w,
                   "v11_source4_fusion":fusedsrc}
            # Here and below only: gold labels enter offline diagnostics.
            pool={m:candidate_pool(fast,bm,hits) for m,hits in
              (("v95_two_search",oldhits),("v11_facet2_fusion",first2),
               ("v11_facet4_fusion",first4),("v11_source4_fusion",sourcehits))}
            pool.update({m:pool.get("v11_facet2_fusion" if "facet2" in m else
                    "v11_facet4_fusion",candidate_pool(fast,bm,[]))
                    for m in ("v11_facet2_witness","v11_facet4_witness")})
            pool.update({"v71_fast":candidate_pool(fast,bm,[]),
                         "bm25":bm[:80]})
            found={m:score(rank,gold) for m,rank in ranks.items()}
            per.append({
               "id":str(row.get("id",row.get("_id",""))),
               "question":q,"support_documents":len(gold),
               "source_mapping_methods":flags,"facets":facets,
               "metrics":found,
               "candidate_full":{m:int(gold<=set(v)) for m,v in pool.items()},
               "candidate_gold_recall":{m:len(gold&set(v))/len(gold)
                                         for m,v in pool.items()},
               "n_candidates":{m:len(v) for m,v in pool.items()},
               "top10_ids":{m:[docs[i]["_id"] for i in rank[:10]]
                            for m,rank in ranks.items()},
               "witness_spans":{"facet2":w2,"facet4":w4},
               "actions":{"v95":actions,"facet_queries":facets,
                          "source_proposals":sourceacts},
               "cost_cpu_ms":{"fast_base":fasttime,"v95_two_search":oldms,
                  "facets":facetms,"source4":sourcems,"fusion_total":fusetime,
                  "witness2":cpu2,"witness4":cpu4},
               "calls":{"v95":len(actions),"facets":len(facets),
                        "source4":len(sourceacts)}
            })
            if len(per)%50==0:print("V11_PROGRESS",split,len(per),flush=True)
        assert len(per)>=150,"Dataset schema/mapping unexpected"
        smm={"stage":"V11","dataset":"MultiHop-RAG ODC-BY",
             "original_file_sha256":hashes,
             "split":split,"offsets":[start,end],
             "original_questions":end-start,"n_scored":len(per),
             "skipped":dict(skip),"corpus_documents":len(docs),
             "cpu_index_ms":{"bm25":build_bm,"graph":build_graph},
             "methods":{},
             "limitations":["source-sentence overlap NOT verified entailment",
                            "no generated answers or truth/abstention proof",
                            "question-ID evidence excluded where ambiguous",
                            "this dataset had already been inspected in V10.1",
                            "2,3,4 source counts not certified logical hop counts",
                            "V11 4-query arm may run fewer queries if fewer facets",
                            "cpu process time per-query not production wall-time"]}
        for m in METHODS:
            rows=[x["metrics"][m] for x in per]
            stats={field:round(float(np.mean([r[field] for r in rows])),6)
                   for field in ("ae5","ae10","r5","r10")}
            stats["full_candidate"]=sum(x["candidate_full"][m] for x in per)
            stats["mean_candidate_gold_recall"]=round(float(np.mean(
                [x["candidate_gold_recall"][m] for x in per])),6)
            stats["by_support_count"]={str(n):{
                "n":sum(x["support_documents"]==n for x in per),
                "ae5":sum(x["support_documents"]==n and
                          x["metrics"][m]["ae5"] for x in per),
                "ae10":sum(x["support_documents"]==n and
                           x["metrics"][m]["ae10"] for x in per),
                "full_pool":sum(x["support_documents"]==n and
                              x["candidate_full"][m] for x in per)}
                for n in sorted(set(x["support_documents"] for x in per))}
            for b in ("bm25","v71_fast","v95_two_search","v11_facet2_fusion",
                      "v11_facet4_fusion"):
                if b==m:continue
                stats["paired_vs_"+b]=paired(
                    [x["metrics"][m]["ae5"] for x in per],
                    [x["metrics"][b]["ae5"] for x in per])
            smm["methods"][m]=stats
        smm["workload"]={"mean_facet_calls":round(float(np.mean([x["calls"]["facets"]
                                                 for x in per])),4),
                         "mean_source4_calls":round(float(np.mean(
                             [x["calls"]["source4"] for x in per])),4),
                         "mean_v95_calls":round(float(np.mean(
                             [x["calls"]["v95"] for x in per])),4),
                         "mean_witness2_cpu_ms":round(float(np.mean(
                             [x["cost_cpu_ms"]["witness2"] for x in per])),3),
                         "mean_witness4_cpu_ms":round(float(np.mean(
                             [x["cost_cpu_ms"]["witness4"] for x in per])),3)}
        out.mkdir(parents=True,exist_ok=True)
        (out/(split+"_summary.json")).write_text(json.dumps(smm,indent=2))
        with (out/(split+"_cases.jsonl")).open("w") as f:
            for x in per:f.write(json.dumps(x,ensure_ascii=False)+"\n")
        print("V11_RESULT",split,json.dumps(smm),flush=True)

def smoke():
    a=facet_queries("Does London have art while Madrid has football?")
    assert len(a)==2
    d=("Alpha City has a large river. Beta Town opened the museum in 2019.")
    s,q=lexical_sentence_witness(d,"Beta Town opened museum",{"beta":1,"town":1,"opened":1,"museum":1})
    assert s>.5 and "Beta Town" in q
    print("V11 lexical-facet witness smoke PASS")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("smoke","run"))
    p.add_argument("--data",type=pathlib.Path,
                   default=pathlib.Path("data/multihoprag_pinned"))
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v11"))
    a=p.parse_args()
    if a.command=="smoke":return smoke()
    rawdocs,questions,hashes=get(a.data)
    evaluate(rawdocs,questions,hashes,a.out)

if __name__=="__main__":main()
