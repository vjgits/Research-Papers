#!/usr/bin/env python3
"""V17B NEW HoVer self-run of PGER and official SAG2 *BM25 stage*.

Same 120 claims (40 each annotated 2/3/4-hop) and exact same original HoVer
Wikipedia text pool. Corpus pooled from original claim-only DRQA titles,
NO supporting_facts used to choose documents (transductive unlabeled index).
Gold only consulted OFFLINE after all ranks computed.

SAG2's original official code is imported (pinned commit) and its SQLite
BM25/FTS retrieval genuinely executed. THIS IS NOT SAG2 JEV, does NOT
represent complete SAG2, and CANNOT be used to claim superiority to SAG2.
Our V16C trained archive selector is fitted exclusively on distinct
EntailmentBank science training questions, no HoVer labels or claims.
Report complete gold title@5/10/20, availability ceiling and CPU.
No answer verdict or sentence-level HoVer Score.
"""
import argparse,collections,hashlib,json,os,pathlib,sys,time,unicodedata
import numpy as np
from benchmark_v16_frontier import FactLinkIndex,run_arm
from benchmark_v16c_activation import (numeric_features,activation,fitted_model,
                                        get_bundles)
from benchmark_v14c_prooftree import source_corpus,reference
from audit_v14_entailmentbank import get
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger
from benchmark_v95_controlled import paired,cpu_ms,unique

def fold(t):
    return unicodedata.normalize("NFD",str(t)).casefold().strip()

def metric(order,gold,corpus_titles):
    relevant={fold(x) for x in gold}
    available=relevant<=corpus_titles
    ranked=[fold(x) for x in order]
    result={"corpus_fully_available":int(available),
            "required_titles":len(relevant)}
    for k in (5,10,20):
        have=relevant&set(ranked[:k])
        result["complete"+str(k)]=int(available and len(have)==len(relevant))
        result["recall"+str(k)]=len(have)/max(1,len(relevant))
    return result

def train_science_model():
    raw,_=get(pathlib.Path("data/entailmentbank_v17"),"worldtree_corpus.jsonl")
    docs,textmap,uuids=source_corpus(raw)
    qs,_=get(pathlib.Path("data/entailmentbank_v17"),"task1/train.jsonl")
    sm=SparseMethods(docs)
    graph=EvidenceLedger(sm)
    link=FactLinkIndex(docs)
    trainx,trainy=[],[]
    for r in qs[400:800]:
        root,h1,h4=get_bundles(r["question"],docs,sm,graph,link)
        idx,X=numeric_features(r["question"],docs,root,h4,sm.index.idfs)
        y=reference(r,textmap,uuids,docs)["gold_mapped"]
        if y:
            trainx.append(X)
            trainy.extend(int(i in y) for i in idx)
    X=np.vstack(trainx);Y=np.asarray(trainy)
    assert X.shape[1]==17 and Y.sum()>=500
    fit_start=time.process_time()
    model=fitted_model(X,Y)
    print("V17_SCIENCE_TRAINED",json.dumps({"n":len(Y),"positive":int(Y.sum()),"cpu_ms":cpu_ms(fit_start)}),flush=True)
    return model

def evaluate(folder,out,upstream):
    docs=json.loads((folder/"corpus.json").read_text())
    records=json.loads((folder/"questions.json").read_text())
    manifest=json.loads((folder/"manifest.json").read_text())
    assert manifest["gold_used_in_corpus_construction"] is False
    assert len(records)==120 and set(x["hops"] for x in records)=={2,3,4}
    assert len({x["uid"] for x in records})==120
    corptitles={fold(d["title"]) for d in docs}
    code_root=pathlib.Path(upstream).resolve()
    sys.path.insert(0,str(code_root/"sag2"/"scripts"))
    from sag2 import CorpusIndex,corpus_fingerprint
    sha=hashlib.sha256((folder/"corpus.json").read_bytes()).hexdigest()
    start=time.process_time()
    sag2index=CorpusIndex(out/"sag2-original.sqlite",docs,sha)
    sag2_build_cpu=cpu_ms(start)
    sm=SparseMethods(docs)
    graph=EvidenceLedger(sm)
    link=FactLinkIndex(docs)
    model=train_science_model()
    rows=[]
    for r in records:
        q=r["question"]
        start=time.process_time()
        expression=sag2index.match_query(q)
        official=sag2index.retrieve(expression,set(),100) if expression else []
        sag2_search_ms=cpu_ms(start)
        sag2bm=list(dict.fromkeys(str(x["title"]) for x in official))
        start=time.process_time()
        h0,h1,h4=get_bundles(q,docs,sm,graph,link)
        pger_search_cpu=cpu_ms(start)
        idx,X=numeric_features(q,docs,h0,h4,sm.index.idfs)
        start=time.process_time()
        pred=model.predict_proba(X)[:,1]
        act=activation(idx,pred,h4["rank"],protect=0)
        act_cpu=cpu_ms(start)
        arms={
          "sag2_official_bm25_only":sag2bm,
          "pger_v16_h0":[docs[i]["title"] for i in h0["rank"]],
          "pger_v16_h1":[docs[i]["title"] for i in h1["rank"]],
          "pger_v16_h4":[docs[i]["title"] for i in h4["rank"]],
          "pger_v16c_zero_shot_archive":[docs[i]["title"] for i in act]
        }
        # Strict isolation: read gold only after all retrieval and ranking done.
        gold=r["gold_titles"]
        results={k:metric(v,gold,corptitles) for k,v in arms.items()}
        rows.append({"uid":r["uid"],"hops":r["hops"],
                     "required_source_titles":len(set(fold(x) for x in gold)),
                     "label":r["label"],
                     "source_fully_available":results["pger_v16_h0"]["corpus_fully_available"],
                     "results":results,
                     "top20":{k:v[:20] for k,v in arms.items()},
                     "timing_cpu_ms":{"sag2_official_bm25":sag2_search_ms,
                         "pger_bounded_four_rounds":pger_search_cpu,
                         "pger_v16c_model_predict":act_cpu},
                     "n_query_actions":len(h4["actions"]),
                     "proof_edges_validated":False})
        if len(rows)%20==0:print("V17_COMPARE_PROGRESS",len(rows),flush=True)
    sag2index.close()
    summary={"stage":"V17 new HoVer dataset direct self-run",
      "dataset":"HoVer official dev, claim verification, original 2017 Wikipedia paragraphs",
      "eval_protocol":"TRANSDUCTIVE pooled first-stage candidate corpus, NOT official all-Wikipedia HoVer benchmark",
      "upstream_sag2":"Zleap-AI/SAG-Benchmark@bb7f82751ba1576219f9d9ebd021128603d130c3",
      "sag2_variant_ran":"OFFICIAL SQLite BM25 INDEX + READER ONLY; no JEV judge; not complete SAG2",
      "pger_variant":"V16 H0/H1/H4 and V16C development-trained archive selector (EntailmentBank training, zero HoVer labels)",
      "n":len(rows),"corpus_docs":len(docs),"corpus_sha256":sha,
      "source_coverage":manifest["full_gold_corpus_coverage"],
      "index_cpu_ms":{"sag2_official_sqlite":sag2_build_cpu,
        "pger_bm25_seconds":sm.bm_index_seconds,
        "pger_factlink_cpu_ms":link.build_cpu_ms},
      "methods":{},
      "warnings":[
        "NO JEV provided: do not compare official SAG2 BM25 result to SAG2 published end-to-end",
        "SAG2 original code executed for BM25; no local trained Qwen unless separately completed and verified",
        "Original DRQA titles taken from the same 120 claims (without labels) to create limited shared source corpus; transductive and optimistic",
        "All supporting fact titles unavailable from the indexed candidate pool count as failed complete retrieval",
        "Title-level evidence recall only; no original sentence-level HoVer Score, entailment, verdict accuracy or abstention",
        "PGER four rounds have extra queries; not matched query/model budgets to zero-call SAG2 BM25",
        "V16C ranker trained on EntailmentBank (other domain), no HoVer label tuning",
        "SAG2 JEV cost/latency cannot be compared since no provider model invoked",
        "Do not claim user system beats SAG2 or has solved 4-hop truth seeking"]}
    for m in rows[0]["results"]:
        summary["methods"][m]={}
        for h in (2,3,4):
            xx=[x for x in rows if x["hops"]==h]
            d={"n":len(xx),"fully_source_available":sum(x["source_fully_available"] for x in xx)}
            for metricname in ("complete5","complete10","complete20","recall5","recall10","recall20"):
                d[metricname]=round(float(np.mean([x["results"][m][metricname] for x in xx])),6)
            summary["methods"][m][str(h)+"hop"]=d
        summary["methods"][m]["overall"]={
            k:round(float(np.mean([x["results"][m][k] for x in rows])),6)
            for k in ("complete5","complete10","complete20","recall5","recall10","recall20")}
        if m!="sag2_official_bm25_only":
            summary["methods"][m]["paired_vs_sag2_official_bm25_at5"]=paired(
                [x["results"][m]["complete5"] for x in rows],
                [x["results"]["sag2_official_bm25_only"]["complete5"] for x in rows])
    for comp in ("sag2_official_bm25","pger_bounded_four_rounds","pger_v16c_model_predict"):
        a=[x["timing_cpu_ms"][comp] for x in rows]
        summary["index_cpu_ms"][comp+"_mean"]=round(float(np.mean(a)),3)
        summary["index_cpu_ms"][comp+"_p95"]=round(float(np.percentile(a,95)),3)
    out.mkdir(parents=True,exist_ok=True)
    (out/"summary.json").write_text(json.dumps(summary,indent=2))
    with (out/"cases.jsonl").open("w") as f:
        for x in rows:f.write(json.dumps(x,ensure_ascii=False)+"\n")
    print("V17_COMPARISON_COMPLETE",json.dumps(summary),flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--prepared",type=pathlib.Path,default=pathlib.Path("v17-hover-data/prepared"))
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v17-comparison"))
    p.add_argument("--upstream",type=pathlib.Path,default=pathlib.Path("sag-benchmark-v17"))
    a=p.parse_args();evaluate(a.prepared,a.out,a.upstream)
if __name__=="__main__":main()
