#!/usr/bin/env python3
"""PGER V16: bounded evidence-frontier / fact-link retrieval with an immutable ledger.

SAG2 cue: retain source-grounded evidence and select *new* next-hop search
frontiers, NOT merely diversify final ranked documents.
HippoRAG2 cue: amortize source token->fact associations (lexical link proxy;
NOT OpenIE/entity graph and NOT an entailment edge).
S2G-RAG cue: keep compact pending *provisional* missing-fact queries and
prevent repeated searches, NOT assert a learned sufficiency judgment.

PGER originality preserved: question-hypothesis task separate from source
evidence, source text hash + exact quote, bounded action ledger, unknown edges,
abstention-compatible outputs, no gold at inference.
Research claim: evaluate only source discovery under fixed search budgets.
No validated relation inference, answer truth, SOTA or official baseline runs.

Question-disjoint primary: EntailmentBank task1 train records [400:800], not
previously scored by PGER (first 400 used to train V14 model). Secondary
already-inspected validation/test are EXPLORATORY, never primary confirmation.
Uses original question only; no gold source ID, answer or proof hypothesis.
"""
import argparse,collections,hashlib,json,pathlib,time
from dataclasses import dataclass
import numpy as np
from expansion_v92 import propose,terms
from benchmark_v14c_prooftree import source_corpus,reference
from audit_v14_entailmentbank import get
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger
from benchmark_v95_controlled import initial,paired,cpu_ms,unique
from pger_v13_proof_gate import Claim,decide,Status

PRIMARY=(400,800)
SPLITS={"unseen_train_question_holdout":PRIMARY,
        "published_validation":(0,187),
        "previously_inspected_test":(0,340)}
ROUND_SNAPSHOTS=(0,1,2,4)
ACTIONS_PER_ROUND=2
BM_HITS=45
INITIAL_RESERVE=45
POOL_LIMIT=120
MAX_DOC_GRAPH_POSTINGS=110
MIN_DOC_GRAPH_POSTINGS=2
GRAPH_NEIGHBORS=9
MAX_FRONTIER=12
MAX_SOURCE_QUERY_WORDS=3
SEED=20261028
METHODS=("bm25_zero","static_first_pass","adaptive_frontier",
         "adaptive_frontier_factlinks")
K_VALUES=(5,10,20)
NO_ANSWER_LEAK=True

def digest(s):return hashlib.sha256(str(s).encode("utf-8")).hexdigest()

class FactLinkIndex:
    """Cheap, *lexical-only*, query-local fact-association adjacency.

    Not genuine HippoRAG2 OpenIE typed fact graph. Source IDs and exact
    text hashes required for every suggested path. Never marks entailment.
    """
    def __init__(self,docs):
        t=time.process_time()
        self.docs=docs
        self.token_sets=[set(terms(d["text"])) for d in docs]
        self.postings=collections.defaultdict(list)
        for i,ts in enumerate(self.token_sets):
            for token in ts:self.postings[token].append(i)
        self.terms_indexed=len(self.postings)
        self.build_cpu_ms=cpu_ms(t)
    def neighbors(self,source_id,n=GRAPH_NEIGHBORS):
        t=time.process_time()
        counter=collections.Counter()
        source=self.token_sets[source_id]
        for term in source:
            posting=self.postings[term]
            if not (MIN_DOC_GRAPH_POSTINGS <=len(posting)<=MAX_DOC_GRAPH_POSTINGS):
                continue
            weight=1.0/(len(posting)**.55)
            for i in posting:
                if i!=source_id:counter[i]+=weight
        ordered=[i for i,v in sorted(counter.items(),key=lambda x:(-x[1],x[0]))[:n]]
        return ordered,cpu_ms(t)

def source_query_candidates(q,docs,source_id,index,used_queries):
    """Exact source sentence + corpus-frequency checked *tentative* slots.

    These are possible bridge terms, not derived fact entailments. A
    source query is never permitted to claim it has proved any edge.
    """
    doc=docs[source_id]
    root=set(terms(q))
    tokens=list(dict.fromkeys(terms(doc["text"])))
    scored=[]
    for token in tokens:
        if token in root:continue
        freq=len(index.postings.get(token,[]))
        if freq<MIN_DOC_GRAPH_POSTINGS or freq>MAX_DOC_GRAPH_POSTINGS:continue
        scored.append((1/(freq**.50),token))
    scored.sort(key=lambda pair:(-pair[0],pair[1]))
    # Strongly prefer two novel linked terms; source text justifies both.
    candidates=[]
    for i,(a_score,a) in enumerate(scored[:5]):
        # Do not hallucinate atomic relations; the tentative slot remains unverified.
        phrase=a
        if phrase.casefold() not in used_queries:
            candidates.append((a_score,phrase,a))
    return candidates

def initialize(question,sm,graph):
    bm,fast,initial_ms=initial(question,sm,graph)
    return {"bm":bm,"fast":fast,"initial_ms":initial_ms}

def frontier_pick(question,docs,graphidx,rank,seen,expanded,used_queries,round_id):
    root=set(terms(question))
    eligible=[]
    for order,i in enumerate(rank[:MAX_FRONTIER*3]):
        if i in expanded:continue
        viable=source_query_candidates(question,docs,i,graphidx,used_queries)
        if not viable:continue
        root_overlap=len(root&graphidx.token_sets[i])/max(1,len(root))
        # PASS>0 preferentially uses truly newly retrieved evidence when
        # available, rather than indefinitely expanding the same initial top5.
        new_bonus=float(i in seen and seen[i]>0)
        score=.20*new_bonus + .5*root_overlap + .30/(1+order) + .12*viable[0][0]
        eligible.append((score,i,viable[0][1]))
    if not eligible:return None
    _,source_id,token=max(eligible,key=lambda p:(p[0],-p[1]))
    return source_id,token

def run_arm(question,docs,sm,graph,graphidx,mode,rounds=4):
    start=initialize(question,sm,graph)
    initial=start["bm"]
    original=start["fast"]
    if mode=="bm25_zero":
        return {0:{"rank":original,"pool":original[:POOL_LIMIT],
                   "actions":[],"queries":0,"cost_ms":start["initial_ms"],
                   "graph_ms":0,"graph_docs":0}}
    static=propose(question,docs,original,sm.index.idfs,
                   kind="mixed",seed_n=10,k=ACTIONS_PER_ROUND*rounds)
    static_terms=[a["term"] for a in static]
    hits=[];graph_hitlists=[];actions=[]
    used=set();expanded=set();last_seen={}
    expanded_docs=set(original[:20]);snapshots={}
    cpu_search=0.;cpu_graph=0.;cpu_selection=0.
    for h in range(rounds+1):
        # Same frozen candidate cap/reserve for all iterative arms.
        ranked,pool=assemble(original,hits,graph_hitlists)
        snapshots[h]={
          "rank":ranked[:POOL_LIMIT],
          "pool":pool,
          "actions":[dict(x) for x in actions],
          "queries":len(actions),
          "cost_ms":start["initial_ms"]+cpu_search+cpu_graph+cpu_selection,
          "graph_ms":cpu_graph,
          "graph_docs":sum(len(x) for x in graph_hitlists)}
        if h==rounds:break
        for a in range(ACTIONS_PER_ROUND):
            t=time.process_time()
            if mode=="static_first_pass":
                ix=h*ACTIONS_PER_ROUND+a
                if ix>=len(static_terms):continue
                term=static_terms[ix]
                src=int(static[ix]["witness_doc"])
            else:
                choice=frontier_pick(question,docs,graphidx,ranked,last_seen,
                                     expanded,used,h)
                if choice is None:continue
                src,term=choice
            if not term or term.casefold() in used:
                continue
            expanded.add(src)
            used.add(term.casefold())
            proposal={
               "turn":h+1,"action_index":len(actions),
               "query":term,
               "source_id":docs[src]["_id"],
               "source_sha256":digest(docs[src]["text"]),
               "source_quote":docs[src]["text"][:320],
               "candidate_missing_relation":{"anchor":term,
                  "target":"unknown_fact",
                  "verdict":"UNVERIFIED","not_an_entailment":True},
               "previously_seen_query":False}
            cpu_selection+=cpu_ms(t)
            t=time.process_time()
            got=[int(i) for i,_ in sm.index.search(term,"bm25",BM_HITS)]
            cpu_search+=cpu_ms(t)
            hits.append(got)
            for i in got[:12]:
                if i not in last_seen:last_seen[i]=h+1
            if mode=="adaptive_frontier_factlinks":
                neighbors,ms=graphidx.neighbors(src,GRAPH_NEIGHBORS)
                cpu_graph+=ms
                graph_hitlists.append(neighbors)
                proposal["graph_links"]=[{
                    "to_doc_id":docs[k]["_id"],
                    "linked_not_entailed":True,
                    "source_sha256":digest(docs[k]["text"])}
                    for k in neighbors[:5]]
            else:proposal["graph_links"]=[]
            proposal["bm_hits"]=len(got)
            actions.append(proposal)
    return {s:snapshots[s] for s in ROUND_SNAPSHOTS if s in snapshots}

def assemble(initial,hits,graph_hits):
    if not hits and not graph_hits:return initial[:POOL_LIMIT],initial[:POOL_LIMIT]
    scores=collections.defaultdict(float)
    for rank,doc in enumerate(initial[:120]):
        scores[doc]+=1/(25+rank)
    for n,hit in enumerate(hits):
        for rank,doc in enumerate(hit):
            scores[doc]+=.70/(25+rank)
    for hit in graph_hits:
        for rank,doc in enumerate(hit):
            scores[doc]+=.38/(25+rank)
    candidates=[i for i in scores if i not in set(initial[:INITIAL_RESERVE])]
    candidates.sort(key=lambda i:(-scores[i],i))
    pool=unique(initial[:INITIAL_RESERVE]+candidates)[:POOL_LIMIT]
    ordered=sorted(pool,key=lambda i:(-scores[i],i))
    return ordered,pool

def score(rank,pool,gold):
    present=not gold["strict_unavailable"] and not gold["unresolved_leafs"]
    ids=gold["gold_mapped"]
    n=max(1,gold["required_n"])
    x={"required_facts":gold["required_n"],
       "fact_depth":gold["depth"],
       "corpus_complete":int(present),
       "pool_complete":int(present and ids<=set(pool)),
       "pool_fact_recall":len(ids&set(pool))/n}
    for k in K_VALUES:
        x["complete_at"+str(k)]=int(present and ids<=set(rank[:k]))
        x["recall_at"+str(k)]=len(ids&set(rank[:k]))/n
    return x

def evaluate(folder,out):
    raw,hash_corpus=get(folder,"worldtree_corpus.jsonl")
    docs,txtmap,uuids=source_corpus(raw)
    sm=SparseMethods(docs)
    t=time.process_time();graph=EvidenceLedger(sm);graph_build=cpu_ms(t)
    idx=FactLinkIndex(docs)
    group_rows={}
    source_hash={"worldtree":hash_corpus}
    for name in ("train","validation","test"):
        rows,sha=get(folder,f"task1/{name}.jsonl")
        group_rows[name]=rows;source_hash[name]=sha

    out.mkdir(parents=True,exist_ok=True)
    for group,spec in SPLITS.items():
        name="train" if group.startswith("unseen_train") else (
             "validation" if group=="published_validation" else "test")
        lo,hi=spec;rows=group_rows[name][lo:hi]
        assert len(rows)==hi-lo,f"Invalid split {group}"
        cases=[]
        for rawq in rows:
            question=str(rawq.get("question","")).strip()
            if not question:continue
            # No access to proof, answer or gold until ALL arm results frozen.
            arms={m:run_arm(question,docs,sm,graph,idx,m)
                  for m in METHODS}
            gold=reference(rawq,txtmap,uuids,docs)
            metrics={}
            traces={}
            for method,stages in arms.items():
                metrics[method]={str(h):score(s["rank"],s["pool"],gold)
                                 for h,s in stages.items()}
                traces[method]={str(h):{
                   "top20":[docs[i]["_id"] for i in s["rank"][:20]],
                   "full_pool_size":len(s["pool"]),
                   "actions":s["actions"],
                   "n_extra_bm25_calls":s["queries"],
                   "cost_process_cpu_ms":round(s["cost_ms"],4),
                   "graph_cpu_ms":round(s["graph_ms"],4),
                   "graph_candidate_exposures":s["graph_docs"]
                 } for h,s in stages.items()}
            # Explicit PGER safety boundary. With no independently validated
            # fact-edge reviewers, no source-ranking outcome may authorize an answer.
            safety=decide([Claim("question_proof","question","requires","validated_evidence")],
                          {},[],0)
            assert safety.status==Status.ABSTAIN
            cases.append({
              "id":rawq.get("id"),"question":question,
              "proof_gate_status":safety.status.value,
              "n_required_leaves":gold["required_n"],
              "depth":gold["depth"],"steps":gold["steps"],
              "n_unavailable":len(gold["strict_unavailable"]),
              "metrics":metrics,"traces":traces})
            if len(cases)%50==0:print("V16_PROGRESS",group,len(cases),flush=True)
        summary={
          "stage":"V16 evidence-frontier proof-source discovery",
          "dataset":"EntailmentBank task1 CC BY 4.0",
          "corpus_unique_exact_statements":len(docs),
          "source_sha256":source_hash,"split":group,
          "split_range":list(spec),"n":len(cases),
          "primary_question_holdout_not_previously_pger_scored":group.startswith("unseen_train"),
          "published_validation_and_test_previously_inspected":not group.startswith("unseen_train"),
          "fixed_pool_limit":POOL_LIMIT,
          "max_extra_BM25_calls_at_h4":ACTIONS_PER_ROUND*4,
          "source_graph_build_cpu_ms":idx.build_cpu_ms,
          "source_graph_token_links":idx.terms_indexed,
          "title_graph_build_cpu_ms":graph_build,
          "bm25_index_build_seconds":sm.bm_index_seconds,
          "methods":{},
          "warnings":[
            "All methods are unverified lexical/fact association heuristics, NOT the three official systems",
            "Source quote + sha shows exact provenance, never supports entailment by itself",
            "No answer generation, factual correctness, semantic proof verification or calibrated abstention",
            "No gold answer/proof used for query generation, source search or ranking",
            "Four-plus leaf count and human annotated logical depth are different",
            "Complete@5 impossible for >5 distinct required facts; report @10/@20 and pool coverage",
            "Absent/rewritten proof premises count as corpus missing",
            "Primary question IDs unscored in previous PGER experiments but corpus/text and aggregates are public",
            "No full official SAG2/HippoRAG2/S2G comparison, no industry SOTA or cost dominance",
            "Graph token-neighbor source lookup adds CPU and storage costs; not true OpenIE"]
        }
        for method in METHODS:
            summary["methods"][method]={}
            for h in ROUND_SNAPSHOTS:
                key=str(h)
                rows_h=[c["metrics"][method].get(key) for c in cases]
                if any(x is None for x in rows_h):continue
                metrics={field:round(float(np.mean([x[field] for x in rows_h])),6)
                     for field in ("complete_at5","complete_at10","complete_at20",
                                   "recall_at5","recall_at10","recall_at20",
                                   "pool_complete","pool_fact_recall")}
                metrics["n_four_plus"]=sum(c["n_required_leaves"]>=4 for c in cases)
                metrics["four_plus_full_pool"]=sum(
                   c["n_required_leaves"]>=4 and c["metrics"][method][key]["pool_complete"]
                   for c in cases)
                metrics["four_plus_complete20"]=sum(
                   c["n_required_leaves"]>=4 and c["metrics"][method][key]["complete_at20"]
                   for c in cases)
                metrics["deep_four_plus_full_pool"]=sum(
                   c["depth"]>=4 and c["metrics"][method][key]["pool_complete"]
                   for c in cases)
                times=[c["traces"][method][key]["cost_process_cpu_ms"]
                       for c in cases]
                metrics["mean_cpu_ms"]=round(float(np.mean(times)),3)
                metrics["p95_cpu_ms"]=round(float(np.percentile(times,95)),3)
                metrics["mean_extra_calls"]=round(float(np.mean(
                     [c["traces"][method][key]["n_extra_bm25_calls"]
                       for c in cases])),3)
                if method!="bm25_zero":
                    baseline=[c["metrics"]["bm25_zero"]["0"]["pool_complete"] for c in cases]
                    metrics["vs_bm25_pool_full"]=paired([x["pool_complete"] for x in rows_h],baseline)
                    if method!="static_first_pass":
                        static_rows=[c["metrics"]["static_first_pass"][key]["pool_complete"]
                                     for c in cases]
                        metrics["vs_static_pool_full"]=paired([x["pool_complete"] for x in rows_h],static_rows)
                summary["methods"][method][key]=metrics
        (out/(group+"_summary.json")).write_text(json.dumps(summary,indent=2))
        with (out/(group+"_cases.jsonl")).open("w") as f:
            for c in cases:f.write(json.dumps(c,ensure_ascii=False)+"\n")
        print("V16_RESULT",group,json.dumps({
          "n":summary["n"],
          "methods":{m:{h:{"pool":v["pool_complete"],
                 "hard":v["four_plus_full_pool"],"c20":v["complete_at20"],
                 "cpu":v["mean_cpu_ms"],
                 "calls":v["mean_extra_calls"],
                 "vs_static":v.get("vs_static_pool_full")}
            for h,v in stages.items()} for m,stages in summary["methods"].items()}
          }),flush=True)

def smoke():
    d=[{"_id":"one","title":"Sun emits light","text":"The sun emits light and heat."},
       {"_id":"two","title":"Heat melts ice","text":"Heat causes ice to melt."},
       {"_id":"three","title":"Birds have feathers","text":"Birds have feathers."}]
    idx=FactLinkIndex(d)
    linked,t=idx.neighbors(0)
    assert all(i!=0 for i in linked)
    a=source_query_candidates("What does the sun emit?",d,0,idx,set())
    assert isinstance(a,list)
    r,p=assemble([0,1,2],[[1,2]],[])
    assert len(p)==3 and len(set(p))==3
    print("V16 provenance-bound frontier and dynamic candidate smoke PASS")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("command",choices=("smoke","run"))
    parser.add_argument("--data",type=pathlib.Path,
       default=pathlib.Path("data/entailmentbank_v14"))
    parser.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v16"))
    a=parser.parse_args()
    if a.command=="smoke":smoke()
    else:evaluate(a.data,a.out)
if __name__=="__main__":main()
