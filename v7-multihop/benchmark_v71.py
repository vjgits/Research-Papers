#!/usr/bin/env python3
"""V7.1: determine whether a compact evidence ledger prevents cross-hop loss.

Hypothesis: explicitly retaining and scoring previous evidence relationships
outperforms the SAME multi-hop traversal with the ledger reset each pass.
The retrieval *algorithm*, not the answer labels, chooses graph paths.
Run against untouched-within-this-version 2Wiki sample 2 and MuSiQue,
with original V7 / BM25 / dense / hybrid baselines.

This is NOT IRCoT, HippoRAG2 or multi-agent verification.
Graph construction uses the established open-source pyahocorasick algorithm.
Evidence state uses document IDs/term coverage/path edges, not full passages.
No paid APIs, no generated answers, no claims of scientific novelty.
"""
import argparse, collections, hashlib, json, math, pathlib, time
import numpy as np
import ahocorasick
from benchmark_v7 import Methods, chain_scores, make_corpus, DENSE_MODEL, DATA_URL, SEED as WIKI_SEED
from benchmark_musique import load_sample, pool_documents, id_of

SEED="v71-2026-10-27"
HOPS=4
BEAM=8
FANOUT=8
BASE_SEEDS=5
DOC_BUDGET=160
# all threshold/settings are frozen before execution on this benchmark
MIN_LINK_TITLE=5
MAX_SAME_TITLE_DOCS=16

def phrases(index,docs):
    """Build a one-time inverted title mention index using Aho-Corasick.
    No relevance labels, questions, or supporting facts are consulted.
    """
    titles=collections.defaultdict(list)
    for i,d in enumerate(docs):
        t=str(d["title"]).strip().casefold()
        if len(t)>=MIN_LINK_TITLE:
            titles[t].append(i)
    autom=ahocorasick.Automaton()
    for title,ids in titles.items():
        if len(ids)<=MAX_SAME_TITLE_DOCS:
            autom.add_word(title,(title,ids))
    autom.make_automaton()
    adjacency=[]
    for i,d in enumerate(docs):
        text=str(d.get("text") or "").casefold()
        targets=set()
        for end,(word,ids) in autom.iter(text):
            start=end-len(word)+1
            if start>0 and text[start-1].isalnum():continue
            if end+1<len(text) and text[end+1].isalnum():continue
            for j in ids:
                if i!=j:targets.add(j)
        adjacency.append(tuple(sorted(targets,key=lambda j:index.ids[j])))
    return adjacency,{"nodes":len(docs),"edges":sum(map(len,adjacency)),
        "nodes_with_outlinks":sum(bool(x) for x in adjacency),
        "indexed_title_strings":len(titles)}

def doc_terms(index,idx):
    p=index.count.indptr[idx];q=index.count.indptr[idx+1]
    return set(index.count.indices[p:q])

class EvidenceLedger:
    def __init__(self,methods):
        self.m=methods
        s=time.perf_counter()
        self.adj,self.stats=phrases(methods.index,methods.docs)
        self.stats["graph_index_seconds"]=time.perf_counter()-s
        self.term_sets=[doc_terms(methods.index,i) for i in range(len(methods.docs))]
        names=methods.index.words.get_feature_names_out()
        self.vocab_idf=np.asarray([methods.index.idfs.get(t,0.) for t in names],dtype=np.float32)
    def search(self,question,initial,mode="ledger",hops=HOPS,bmraw=None):
        """Ablation switches ONLY prior-hop term memory; all remaining
        traversal constraints, seed set, and hop budget are identical.
        """
        assert mode in ("ledger","reset","one-hop")
        t0=time.perf_counter()
        idx=self.m.index
        qset=set(idx.query_words.transform([question]).indices)
        if bmraw is None:
            bmraw=idx.search(question,"bm25",100)
        maxbm=max(1e-8,bmraw[0][1] if bmraw else 1.)
        bmscores={j:max(0.,s)/maxbm for j,s in bmraw}
        # initial is one ranking shared by both ledger and reset variants
        seeds=list(dict.fromkeys(initial[:BASE_SEEDS]))
        initial_baseline=list(initial)
        if not seeds:return initial_baseline,{"time_ms":0,"expanded":0,"edges_tested":0,"depth":0,"memory_ids":0}
        qidf={j:float(self.vocab_idf[j]) for j in qset}
        raremass=max(sum(qidf.values()),1e-8)
        def mass(terms):
            return sum(qidf[j] for j in terms&qset)/raremass
        # Non-parameter, non-LLM memory: a compact set of seen document IDs
        # and query-term indices, plus a path showing explicit source mentions.
        beam=[]
        for i in seeds:
            ts=self.term_sets[i]
            score=0.6*bmscores.get(i,0)+0.45*mass(ts)
            beam.append((score,(i,),ts))
        beam.sort(key=lambda r:(-r[0],tuple(self.m.ids[i] for i in r[1])))
        allstates=list(beam)
        expanded=0;edges_tested=0;deepest=0
        maxdepth=1 if mode=="one-hop" else hops
        for step in range(maxdepth):
            candidates=[]
            for score,path,seen in beam:
                src=path[-1]
                neighbors=self.adj[src]
                if not neighbors:continue
                available=[j for j in neighbors if j not in path]
                # Rank outgoing source transitions by cheap word-match and
                # new evidence content, not gold labels.
                pool=[]
                for j in available:
                    edges_tested+=1
                    if edges_tested>DOC_BUDGET*maxdepth*20:break
                    old=self.term_sets[src] if mode=="reset" else seen
                    gain=mass(self.term_sets[j]-old)
                    qfit=mass(self.term_sets[j])
                    orig=bmscores.get(j,0)
                    # Finite, bounded source-edge utility.
                    utility=0.50*orig+0.35*qfit+0.70*gain
                    if utility<=0.005:continue
                    pool.append((utility,j,gain))
                pool.sort(key=lambda x:(-x[0],self.m.ids[x[1]]))
                for utility,j,gain in pool[:FANOUT]:
                    expanded+=1
                    # Higher retained context rewards distinct unresolved
                    # evidence. Reset arm uses only the most recent passage.
                    nextseen=self.term_sets[j] if mode=="reset" else seen|self.term_sets[j]
                    newscore=0.79*score+utility-0.04*len(path)
                    candidates.append((newscore,path+(j,),nextseen))
            if not candidates:break
            # de-duplicate frontier by last node to limit redundant work.
            candidates.sort(key=lambda r:(-r[0],tuple(self.m.ids[i] for i in r[1])))
            chosen=[];seen_last=set()
            for state in candidates:
                if state[1][-1] in seen_last:continue
                chosen.append(state)
                seen_last.add(state[1][-1])
                if len(chosen)>=BEAM:break
            if not chosen:break
            beam=chosen;allstates.extend(chosen);deepest=step+1
        # Rerank *bundles* (paths), not unrelated passages; rank the best
        # evidence paths under a strict TopK projection.
        path_scores=sorted(allstates,key=lambda r:(-r[0],-len(r[1]),
                          tuple(self.m.ids[i] for i in r[1])))
        # To avoid arbitrary long paths displacing all lexical answers,
        # keep one lexical anchor and then select complementary path docs.
        result=[initial_baseline[0]]
        already={initial_baseline[0]}
        for score,path,seen in path_scores:
            for doc in path:
                if doc not in already:
                    result.append(doc)
                    already.add(doc)
                if len(result)>=10:break
            if len(result)>=10:break
        for i in initial_baseline:
            if len(result)>=100:break
            if i not in already:
                result.append(i)
                already.add(i)
        return result[:100],{"time_ms":(time.perf_counter()-t0)*1000,
           "expanded":expanded,"edges_tested":edges_tested,"depth":deepest,
           "memory_ids":max((len(path) for _,path,_ in allstates),default=0),
           "states":len(allstates)}

def evaluate_dataset(name,rows,docs,goldfn,output,model):
    system=Methods(docs,model)
    ledger=EvidenceLedger(system)
    observations=collections.defaultdict(list)
    timings=collections.defaultdict(list)
    for k,row in enumerate(rows):
        query=row["question"]
        ranks,cost=system.run(query)
        # All variants share the same BM25+MiniLM hybrid initial shortlist,
        # and hence the same index and dense query-computation cost.
        seedrank=ranks["hybrid"]
        methods={
            "bm25":ranks["bm25"],
            "dense":ranks["dense"],
            "hybrid":ranks["hybrid"],
            "v7_onehop":ranks["proofgap_v7"]}
        meta={}
        shared_bmraw=system.index.search(query,"bm25",100)
        for label,mode,depth in [("graph_onehop","one-hop",1),
             ("multihop_reset","reset",4),
             ("multihop_ledger","ledger",4),
             ("multihop_ledger2","ledger",2)]:
            ranksout,stats=ledger.search(query,seedrank,mode=mode,hops=depth,bmraw=shared_bmraw)
            methods[label]=ranksout
            meta[label]=stats
            timings[label].append(stats["time_ms"])
        gold=goldfn(row)
        assert len(gold)>=2 and gold<=set(system.ids)
        for method,docids in methods.items():
            complete,partial=chain_scores(docids,gold,system.ids)
            observations[method].append({"id":str(row["id"]),
                "method":method,"gold_count":len(gold),**complete,**partial,
                "walk":meta.get(method,{}),
                "base_ms":cost["ms_bm"],"dense_ms":cost["ms_dense"]})
        if (k+1)%40==0:print(name,"evaluated",k+1,"/",len(rows),flush=True)
    summary={}
    bm={x["id"]:x for x in observations["bm25"]}
    hy={x["id"]:x for x in observations["hybrid"]}
    for method,items in observations.items():
        primary={k:float(np.mean([x[k] for x in items])) for k in [
             "chain_at_3","chain_at_5","chain_at_10","evidence_recall_at_5"]}
        vs_b=[x["chain_at_5"]-bm[x["id"]]["chain_at_5"] for x in items]
        vs_h=[x["chain_at_5"]-hy[x["id"]]["chain_at_5"] for x in items]
        by_hops={str(n):{"n":sum(x["gold_count"]==n for x in items),
           "chain_at_5":float(np.mean([x["chain_at_5"] for x in items if x["gold_count"]==n]))}
           for n in sorted({x["gold_count"] for x in items})}
        summary[method]={"n":len(items),"metrics":primary,"by_hops":by_hops,
             "wins_vs_bm25":sum(x>0 for x in vs_b),"losses_vs_bm25":sum(x<0 for x in vs_b),
             "wins_vs_hybrid":sum(x>0 for x in vs_h),"losses_vs_hybrid":sum(x<0 for x in vs_h),
             "additional_latency_ms":float(np.mean(timings[method])) if method in timings else 0.,
             "mean_expansions":float(np.mean([x["walk"]["expanded"] for x in items])) if method in timings else 0.,
             "mean_edges_examined":float(np.mean([x["walk"]["edges_tested"] for x in items])) if method in timings else 0.,
             "mean_depth":float(np.mean([x["walk"]["depth"] for x in items])) if method in timings else 0.
             }
        print(name,method,"chain@5",round(primary["chain_at_5"],5),
              "byhop",[(k,round(v["chain_at_5"],3)) for k,v in by_hops.items()],
              flush=True)
    output.mkdir(parents=True,exist_ok=True)
    with (output/(name+"_per_question.jsonl")).open("w") as f:
        for arr in observations.values():
            for item in arr:f.write(json.dumps(item)+"\n")
    return {"dataset":name,"questions":len(rows),"documents":len(docs),
        "graph":ledger.stats,"dense_index_seconds":system.embed_s,
        "methods":summary}

def load_2wiki_second_sample(dest):
    """Read sample-2 IDs without modifying original V7 method or its sorting."""
    import pyarrow.parquet as pq
    import urllib.request
    dest.mkdir(parents=True,exist_ok=True)
    fname=dest/"2wiki_validation.parquet"
    if not fname.exists():urllib.request.urlretrieve(DATA_URL,fname)
    rows=pq.read_table(fname,columns=["id","question","type","supporting_facts","context"]).to_pylist()
    rows.sort(key=lambda x:hashlib.sha256((WIKI_SEED+"|"+str(x["id"])).encode()).digest())
    selected=[]
    for r in rows:
        ctx=r.get("context") or {}
        titles=ctx.get("title") or []
        paras=ctx.get("sentences") or []
        sf=r.get("supporting_facts") or {}
        required={t.strip().casefold() for t in sf.get("title") or [] if t}
        available={str(t).strip().casefold() for t in titles}
        if titles and len(titles)==len(paras) and len(required)>=2 and required<=available:
            selected.append(r)
            if len(selected)>=480:break
    if len(selected)<480:raise ValueError("Insufficient 2Wiki validation records")
    return selected[240:480]

def gold_2wiki(row):
    return {str(t).strip().casefold() for t in row["supporting_facts"]["title"]}

def gold_musique(row):
    return {id_of(par) for par in row["paragraphs"] if par["is_supporting"]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=["smoke","run"])
    p.add_argument("--datasets",nargs="+",choices=["2wiki","musique"],default=["2wiki","musique"])
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v71"))
    p.add_argument("--data",type=pathlib.Path,default=pathlib.Path("data"))
    args=p.parse_args()
    if args.command=="smoke":
        sample=[{"_id":"a","title":"Alpha Entity","text":"The Alpha Entity referred to Beta Entity."},
                {"_id":"b","title":"Beta Entity","text":"Beta Entity referred to Gamma Entity."},
                {"_id":"c","title":"Gamma Entity","text":"Gamma Entity was independently verified."}]
        from benchmark_v6 import Retriever
        idx=Retriever(sample)
        edges,stats=phrases(idx,sample)
        assert 1 in edges[0] and 2 in edges[1]
        print("V7.1 SMOKE PASS")
        return
    import torch
    from sentence_transformers import SentenceTransformer
    torch.set_num_threads(2)
    model=SentenceTransformer(DENSE_MODEL,device="cpu")
    result=[]
    if "2wiki" in args.datasets:
        rows=load_2wiki_second_sample(args.data)
        result.append(evaluate_dataset("2wiki_disjoint_sample2",rows,make_corpus(rows),
             gold_2wiki,args.out,model))
    if "musique" in args.datasets:
        rows=load_sample(args.data)
        result.append(evaluate_dataset("musique",rows,pool_documents(rows),
             gold_musique,args.out,model))
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"summary.json").write_text(json.dumps({"design":"same budgets, memory-reset vs ledger ablation",
          "no_gold_used_in_search":True,"no_answer_generation":True,
          "no_official_ircot_hipporag2_run":True,"retrieval_model":DENSE_MODEL,
          "datasets":result},indent=2))
    print("V7.1 EVALUATION COMPLETE",flush=True)
if __name__=="__main__":main()
