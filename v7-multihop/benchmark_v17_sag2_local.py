#!/usr/bin/env python3
"""V17 SAG2 author's FULL ITERATIVE local-Qwen variant on six new HoVer claims.

Executes official unmodified CorpusIndex, search_sag2 and LocalScorer,
no JEV cloud provider, no API key, 2 each annotated 2/3/4 hops, one
expansion round. SIX-CASE FEASIBILITY SMOKE ONLY, not powered superiority.
"""
import argparse,asyncio,hashlib,json,pathlib,sys,time,unicodedata
from benchmark_v16_frontier import FactLinkIndex,run_arm
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger
def norm(x):return unicodedata.normalize("NFD",str(x)).casefold().strip()
def metrics(rank,gold,all_titles):
    gold={norm(x) for x in gold};r=[norm(x) for x in rank]
    possible=gold<=all_titles
    z={"available":possible}
    for k in (5,10,20):
        z["complete_at"+str(k)]=int(possible and gold<=set(r[:k]))
        z["recall_at"+str(k)]=len(gold&set(r[:k]))/max(1,len(gold))
    return z
async def run(prepared,out,upstream,model_path):
    docs=json.loads((prepared/"corpus.json").read_text())
    questions=json.loads((prepared/"questions.json").read_text())
    sample=[q for h in (2,3,4) for q in [x for x in questions if x["hops"]==h][:2]]
    assert len(sample)==6
    out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(pathlib.Path(upstream).resolve()/"sag2"/"scripts"))
    from sag2 import CorpusIndex,search_sag2
    from local_reranker import LocalReranker,LocalScorer
    sha=hashlib.sha256((prepared/"corpus.json").read_bytes()).hexdigest()
    t=time.perf_counter()
    idx=CorpusIndex(out/"sag2_local.sqlite",docs,sha)
    build_seconds=time.perf_counter()-t
    t=time.perf_counter()
    engine=LocalReranker(pathlib.Path(model_path),"qwen","transformers","cpu",1)
    model_load_seconds=time.perf_counter()-t
    scorer=LocalScorer(engine,out/"responses")
    pger=SparseMethods(docs)
    graph=EvidenceLedger(pger)
    link=FactLinkIndex(docs)
    corpus_titles={norm(d["title"]) for d in docs}
    results=[]
    for q in sample:
        t=time.perf_counter()
        # Unmodified author SAG2 iterative algorithm with author local Qwen scorer
        sag=await search_sag2(idx,scorer,q["question"],candidate_k=16,seed_k=4,
                         max_hops=1,expansion_term_limit=8)
        sag_seconds=time.perf_counter()-t
        title_rank=list(dict.fromkeys(x["title"] for x in sag["candidates"]))
        t=time.perf_counter()
        p=run_arm(q["question"],docs,pger,graph,link,"static_first_pass",rounds=4)
        pger_seconds=time.perf_counter()-t
        methods={"sag2_official_local_qwen_h1":title_rank,
                 "pger_initial":[docs[i]["title"] for i in p[0]["rank"]],
                 "pger_h1":[docs[i]["title"] for i in p[1]["rank"]],
                 "pger_h4":[docs[i]["title"] for i in p[4]["rank"]]}
        # Gold labels accessed ONLY AFTER all ranks generated.
        gold=q["gold_titles"]
        record={"uid":q["uid"],"hops":q["hops"],"question":q["question"],
          "metrics":{m:metrics(rank,gold,corpus_titles) for m,rank in methods.items()},
          "top20_titles":{m:rank[:20] for m,rank in methods.items()},
          "sag2_usage":sag["jev_usage"],"sag2_trace":sag["trace"],
          "sag2_wall_seconds":sag_seconds,"pger_wall_seconds":pger_seconds,
          "local_model":engine.config,"no_verified_entailment":True}
        results.append(record)
        (out/"cases.jsonl").write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in results))
        print("V17_SAG2_LOCAL_CASE",json.dumps({
            "hop":q["hops"],"completed":len(results),
            "sag2":record["metrics"]["sag2_official_local_qwen_h1"],
            "pger":record["metrics"]["pger_h1"],
            "wall_seconds":round(sag_seconds,2),
            "local_judgments":sag["jev_usage"]["judgments"]}),flush=True)
    idx.close()
    summary={"experiment":"SAG2 official source with LOCAL Qwen scorer vs PGER on HoVer",
      "n":len(results),"hops":{"2":2,"3":2,"4":2},
      "upstream_sag2_git_commit":"bb7f82751ba1576219f9d9ebd021128603d130c3",
      "qwen_revision":"e61197ed45024b0ed8a2d74b80b4d909f1255473",
      "sag2_scorer":"local Qwen/Qwen3-Reranker-0.6B, author provided integration, NOT original JEV",
      "candidate_k":16,"expansion_hops":1,"seed_k":4,"expansion_term_limit":8,
      "source_articles":len(docs),"corpus_sha":sha,
      "sag2_build_wall_seconds":build_seconds,"local_model_load_wall_seconds":model_load_seconds,
      "judgments":sum(r["sag2_usage"]["judgments"] for r in results),
      "request_count":sum(r["sag2_usage"]["requests"] for r in results),
      "method_metrics":{},"cautions":[
         "Only six examples, NOT statistical comparison nor full original JEV SAG2",
         "Same transductive first-stage HoVer DRQA article corpus for both methods",
         "Comparison NOT equal scorer/model/search budget",
         "No HoVer verdict accuracy, no sentence-level verification, no open-Wikipedia benchmark",
         "No paid API keys, no claims of PGER superiority over SAG2"]}
    for m in results[0]["metrics"]:
        summary["method_metrics"][m]={str(h):{
            "n":2,
            "complete_at5":sum(r["hops"]==h and r["metrics"][m]["complete_at5"] for r in results),
            "complete_at10":sum(r["hops"]==h and r["metrics"][m]["complete_at10"] for r in results)
        } for h in (2,3,4)}
    (out/"summary.json").write_text(json.dumps(summary,indent=2))
    print("V17_SAG2_LOCAL_COMPLETE",json.dumps(summary),flush=True)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--prepared",type=pathlib.Path,default=pathlib.Path("v17-hover-data/prepared"))
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v17-sag2-local"))
    p.add_argument("--upstream",type=pathlib.Path,default=pathlib.Path("sag-benchmark-v17"))
    p.add_argument("--model-path",type=pathlib.Path,default=pathlib.Path("qwen-local-model"))
    a=p.parse_args();asyncio.run(run(a.prepared,a.out,a.upstream,a.model_path))
if __name__=="__main__":main()
