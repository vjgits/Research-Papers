#!/usr/bin/env python3
"""V17 optional JEV-provider SAG2 reproduction, manual and paid opt-in only.

Uses unmodified SAG2 author's exact CorpusIndex, JevClient and search_sag2
on the same 120 HoVer claims, same transductive frozen 16,579 Wikipedia
article corpus as V17B. No API requests in --dry-run. Live requires both
explicit --paid-run and OPENROUTER_API_KEY, exact model response build check,
a per-run USD usage ceiling, and a user-defined claim limit.
JEV scorer is original provider model (not local Qwen), but this is NOT the
author's original MuSiQue benchmark; it is a custom HoVer transfer test.
"""
import argparse,asyncio,hashlib,json,os,pathlib,sys,time,unicodedata
from collections import Counter
EXPECTED_MODEL="typesafe/jev-1.13-20260917"
REQUEST_MODEL="typesafe/jev-1.13"
ENDPOINT="https://openrouter.ai/api/alpha/decisions"
INPUT_USD_PER_M=0.042

def fold(value):return unicodedata.normalize("NFD",str(value)).casefold().strip()
def safe_metric(ranked,required,corpus):
    g={fold(x) for x in required}
    r=[fold(x) for x in ranked]
    available=g<=corpus
    d={"required":len(g),"source_available":int(available)}
    for k in (5,10,20):
        d["complete_at"+str(k)]=int(available and g<=set(r[:k]))
        d["recall_at"+str(k)]=len(g&set(r[:k]))/max(1,len(g))
    return d

def verify_prepared(prepared):
    corpuspath=prepared/"corpus.json"
    qpath=prepared/"questions.json"
    manifest=json.loads((prepared/"manifest.json").read_text())
    docs=json.loads(corpuspath.read_text())
    qq=json.loads(qpath.read_text())
    assert manifest["gold_used_in_corpus_construction"] is False
    assert len(docs)==manifest["n_actual_corpus_docs"]==16579
    assert len(qq)==120
    assert {int(x["hops"]) for x in qq}=={2,3,4}
    assert len({x["uid"] for x in qq})==120
    return docs,qq,manifest,hashlib.sha256(corpuspath.read_bytes()).hexdigest()

class CostTracker:
    def __init__(self,expected_model,ceiling):
        self.expected_model=expected_model
        self.max_cost=ceiling
        self.cost=0.0
        self.tokens=0
        self.calls=0
        self.actual_models=set()
        self.prices=[]
    def record(self,result):
        actual=result.get("model")
        self.actual_models.add(str(actual))
        if actual!=self.expected_model:
            raise RuntimeError(f"Actual provider model changed ({actual}). STOP: do not count as exact historical reproduction.")
        usage=result.get("usage") or {}
        tokens=usage.get("input_tokens")
        if not isinstance(tokens,(int,float)) or tokens<0:
            raise RuntimeError("Missing numeric input token accounting; fail closed.")
        cost=usage.get("cost")
        if not isinstance(cost,(int,float)) or cost<0:
            cost=float(tokens)*INPUT_USD_PER_M/1000000
            self.prices.append("estimated from listed token price")
        else:self.prices.append("provider reported usage.cost")
        self.cost+=cost
        self.tokens+=int(tokens)
        self.calls+=1
    def precheck(self):
        if self.cost>=self.max_cost:
            raise RuntimeError(f"Budget reached, no further claims: consumed USD {self.cost:.6f} of {self.max_cost:.6f}")
    def status(self):return {"usd_consumed":round(self.cost,7),"input_tokens":self.tokens,"calls":self.calls,"actual_models":sorted(self.actual_models),"usage_accounting":sorted(set(self.prices))}

async def execute(args):
    docs,qq,manifest,sha=verify_prepared(args.prepared)
    print("V17_JEV_DRY_PREFLIGHT",json.dumps({
       "n_claims":len(qq),"source_docs":len(docs),"sha256":sha,
       "source_availability":manifest["full_gold_corpus_coverage"],
       "sag2_original_commit":"bb7f82751ba1576219f9d9ebd021128603d130c3",
       "jev_model_requested":REQUEST_MODEL,
       "expected_actual_model":EXPECTED_MODEL,
       "candidate_k":100,"seed_k":10,"max_hops":2,
       "term_limit":20,"endpoint":ENDPOINT,
       "paid_run_requested":args.paid_run,
       "max_cases":args.max_cases,"budget_usd":args.budget_usd}),flush=True)
    if not args.paid_run:return
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise RuntimeError("OPENROUTER_API_KEY absent; set GitHub Actions secret, NEVER commit/paste it.")
    if args.budget_usd<=0 or args.budget_usd>20:
        raise ValueError("Paid budget must be > 0 and <= 20 USD; change program only with new review.")
    args.out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(pathlib.Path(args.upstream).resolve()/"sag2"/"scripts"))
    from sag2 import CorpusIndex,JevClient,search_sag2
    import aiohttp
    cost=CostTracker(EXPECTED_MODEL,args.budget_usd)
    class MeteredJev(JevClient):
        async def request(self,payload):
            response=await super().request(payload)
            cost.record(response)
            return response
    start=time.perf_counter()
    index=CorpusIndex(args.out/"sag2_jev.sqlite",docs,sha)
    build_time=time.perf_counter()-start
    results=[]
    try:
        timeout=aiohttp.ClientTimeout(total=300)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            engine=MeteredJev(session,ENDPOINT,REQUEST_MODEL,os.environ["OPENROUTER_API_KEY"],question_type="noul")
            all_titles={fold(d["title"]) for d in docs}
            for q in qq[:args.max_cases]:
                cost.precheck()
                t=time.perf_counter()
                ans=await search_sag2(index,engine,q["question"],
                                      candidate_k=100,seed_k=10,
                                      max_hops=2,expansion_term_limit=20)
                elapsed=time.perf_counter()-t
                # Gold used only after full SAG2 result generated.
                rank=list(dict.fromkeys(str(c["title"]) for c in ans["candidates"]))
                metric=safe_metric(rank,q["gold_titles"],all_titles)
                row={"uid":q["uid"],"annotated_hops":q["hops"],
                     "label":q["label"],"metric":metric,
                     "top20_titles":rank[:20],"wall_seconds":round(elapsed,5),
                     "jev_usage":ans["jev_usage"],
                     "provider_accounting":cost.status(),
                     "claim_has_approved_proof":False}
                results.append(row)
                with (args.out/"cases.jsonl").open("w") as stream:
                    for item in results:stream.write(json.dumps(item,ensure_ascii=False)+"\n")
                print("V17_SAG2_PROVIDER_JEV",json.dumps({
                    "n":len(results),"hop":q["hops"],"AE5":metric["complete_at5"],
                    "req":ans["jev_usage"]["requests"],"judgments":ans["jev_usage"]["judgments"],
                    "wall_seconds":round(elapsed,3),"spent_usd":round(cost.cost,6)
                }),flush=True)
                if cost.cost>=args.budget_usd:break
    finally:index.close()
    summary={"kind":"Original SAG2 with original JEV provider, exact author code",
      "dataset":"HoVer 120 sampled 2/3/4-hop claims (transductive candidate pool)",
      "n_completed":len(results),"n_requested":args.max_cases,
      "sag2_git_commit":"bb7f82751ba1576219f9d9ebd021128603d130c3",
      "jev_actual_versions":sorted(cost.actual_models),
      "jev_requested_version":REQUEST_MODEL,
      "expected_historical_build":EXPECTED_MODEL,
      "jev_usage":cost.status(),"hard_budget_note":"post-request cumulative spend gate; a single request can overshoot the ceiling",
      "index_build_wall_sec":build_time,"corpus_sha256":sha,
      "model_calls_not_zero":True,
      "source_limitations":manifest["full_gold_corpus_coverage"],
      "methods":{"sag2_full_jev":{}},
      "warnings":[
        "This is original SAG2 JEV on NEW custom HoVer corpus, not identical original 1000 MuSiQue paper evaluation",
        "JEV model build verified in response; request alias is 1.13",
        "These are title-identity retrieval evidence metrics, not HoVer verdict or source-sentence verification",
        "The shared pooled corpus is transductive and only 10/40 sampled 4-hop claims have complete source coverage",
        "No claim of industry SOTA, answer correctness, or independently sealed generalization"]}
    for h in (2,3,4):
        subset=[r for r in results if r["annotated_hops"]==h]
        summary["methods"]["sag2_full_jev"][str(h)+"hop"]={
           "n":len(subset),
           **{field:sum(x["metric"][field] for x in subset) for field in ("complete_at5","complete_at10","complete_at20")}}
    summary["methods"]["sag2_full_jev"]["all"]={
        "n":len(results),
        **{field:sum(x["metric"][field] for x in results) for field in ("complete_at5","complete_at10","complete_at20")}}
    (args.out/"summary.json").write_text(json.dumps(summary,indent=2))
    print("V17_SAG2_JEV_FINISHED",json.dumps(summary),flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--prepared",type=pathlib.Path,default=pathlib.Path("v17-hover-data/prepared"))
    p.add_argument("--upstream",type=pathlib.Path,default=pathlib.Path("sag-benchmark-v17"))
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v17-original-jev"))
    p.add_argument("--max-cases",type=int,default=10)
    p.add_argument("--budget-usd",type=float,default=1.0)
    p.add_argument("--paid-run",action="store_true")
    a=p.parse_args()
    if not 1<=a.max_cases<=120:p.error("max cases must be 1..120")
    asyncio.run(execute(a))
if __name__=="__main__":main()
