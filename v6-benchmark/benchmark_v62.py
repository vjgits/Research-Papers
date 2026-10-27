#!/usr/bin/env python3
"""V6.2 Counterfactual Proof-Gap Search: dev-training / dev-validation ONLY.

Designed from V6/V6.1 errors, not a reproduction of a published RAG algorithm.
An action is worthwhile only if it is predicted to change the ranking toward
additional evidence more than its retrieval cost. We learn *action effects*,
rather than copying a library of retrieval recipes. This is not a novelty proof.

No reference judgments are accessed by the search controller at inference time.
Never loads or evaluates the BEIR sealed half.
"""
import argparse, collections, hashlib, json, pathlib, time
import numpy as np
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from benchmark_v6 import Retriever,download,load,measures,partition,SEED,proofgap
from benchmark_v61 import guarded, query_terms, document_terms, evidence_gap

INNER_SEED="v6-2-action-value-2026-10-27"
# Fixed *before* development-validation scoring.
PRE_GAP_FLOOR=0.12
PRE_SEARCH_PROB=0.58
POST_PREDICTED_GAIN=0.008
COST_PER_SEARCH=0.002  # nDCG units, heuristic opportunity cost
MAX_ACTIONS=24

def inner_part(dataset,qid):
    value=int.from_bytes(hashlib.sha256((INNER_SEED+"|"+dataset+"|"+qid).encode()).digest()[:8],"big")
    return "fit" if value%10<6 else "validate"

def scores(index, question, base):
    allterms=query_terms(index,question)
    if not base:return [],[],[],0.,0.
    topterm=document_terms(index,base[0][0])
    top2=document_terms(index,base[1][0]) if len(base)>1 else set()
    union=topterm|top2
    missing=[t for t in allterms if index.words.vocabulary_[t] not in union]
    present=[t for t in allterms if index.words.vocabulary_[t] in union]
    denom=sum(index.idfs.get(t,0) for t in allterms)
    weighted=sum(index.idfs.get(t,0) for t in missing)/max(denom,1e-8)
    lead=base[0][1]
    margin=(lead-base[1][1])/max(abs(lead),1e-8) if len(base)>1 else 1.
    return allterms,missing,present,weighted,max(0.,min(1.,margin))

def question_features(index,question,base):
    allterms,missing,present,gap,margin=scores(index,question,base)
    top=base[0][1] if base else 0.
    second=base[1][1] if len(base)>1 else 0.
    third=base[2][1] if len(base)>2 else 0.
    def doc_overlap(i):
        if i>=len(base):return 0.
        d=document_terms(index,base[i][0])
        return len([t for t in allterms if index.words.vocabulary_[t] in d])/max(1,len(allterms))
    return np.asarray([gap,margin,len(allterms)/20,len(missing)/max(1,len(allterms)),
        len(present)/max(1,len(allterms)),max(0.,second)/max(1e-8,top),
        max(0.,third)/max(1e-8,top),doc_overlap(0),doc_overlap(1),
        min(1.,len(base)/100),min(1.,top/30)],dtype=float)

def candidate_actions(index,question,base,second):
    """Actions connect a missing premise to a corroborating or rival document.
    Never change original top hit, and never manufacture source relevance labels.
    """
    base_ids=[i for i,_ in base]
    by_rank={idx:j for j,idx in enumerate(base_ids)}
    base_score={idx:score for idx,score in base}
    top=max(base[0][1],1e-8)
    qterms,missing,present,gap,margin=scores(index,question,base)
    missingids={index.words.vocabulary_[t] for t in missing}
    qids={index.words.vocabulary_[t] for t in qterms}
    firstterms=document_terms(index,base[0][0])
    missingmass=max(sum(index.idfs.get(t,0) for t in missing),1e-8)
    totalmass=max(sum(index.idfs.get(t,0) for t in qterms),1e-8)
    answer=[]
    # Prefer a distinct source that explains the unresolved concepts and
    # already possesses some independent original-query relevance.
    for srank,(idx,second_score) in enumerate(second[:35]):
        original_rank=by_rank.get(idx,100)
        if original_rank<=1:continue
        dt=document_terms(index,idx)
        shared={t for t in missing if index.words.vocabulary_[t] in dt}
        fill=sum(index.idfs.get(t,0) for t in shared)/missingmass
        coverage=sum(index.idfs.get(t,0) for t in qterms if index.words.vocabulary_[t] in dt)/totalmass
        novelty=len(dt-firstterms)/max(1,len(dt))
        sourcefit=base_score.get(idx,0.)/top
        # If it is a wholly unrelated document the new search cannot promote it.
        if coverage<0.15 or sourcefit<0.11:continue
        for pos in [1,2,3]:
            if original_rank<=pos:continue
            already=set(base_ids[:pos])
            if idx in already:continue
            # Ranking action: preserve top one, only re-order one candidate.
            proposal=base_ids[:pos]+[idx]+[i for i in base_ids[pos:] if i!=idx]
            proposal=proposal[:100]
            # There must be a meaningful change to the evaluated top 10.
            if proposal[:10]==base_ids[:10]:continue
            features=[gap,margin,coverage,fill,novelty,sourcefit,
               1/(1+srank),min(1.,original_rank/100.),pos/3.,
               len(shared)/max(1,len(missing)),len(qterms)/20.,
               (base_score.get(idx,0.)/max(1e-8,base[pos][1])) if pos<len(base) else 0.,
               len(present)/max(1,len(qterms))]
            answer.append({"candidate":idx,"position":pos,"second_rank":srank,
                           "features":features,"proposal":proposal,
                           "source_rank":original_rank})
        if len(answer)>=MAX_ACTIONS:break
    return answer[:MAX_ACTIONS]

def proposed_followup(index,question,base):
    allterms,missing,present,gap,margin=scores(index,question,base)
    # Preserve the original question's hardest unresolved concepts while
    # anchoring a distinctive known concept, not simply repeating all words.
    if not missing:return ""
    missing=sorted(missing,key=lambda t:(-index.idfs.get(t,0),t))[:10]
    anchors=sorted(present,key=lambda t:(-index.idfs.get(t,0),t))[:2]
    return " ".join(anchors[:1]+missing)

def hypothetical_actions(index,question,base):
    followup=proposed_followup(index,question,base)
    if not followup:return [],False
    extra=index.search(followup,"bm25",100)
    return candidate_actions(index,question,base,extra),True

def make_train_rows(data):
    gate_X=[];gate_y=[];action_X=[];action_y=[]
    by_dataset=collections.Counter()
    for name,engine,queries,qrels,ids in data:
        for qid in ids:
            text=queries[qid]
            base=engine.search(text,"bm25",100)
            if len(base)<5:continue
            qf=question_features(engine,text,base)
            actions,_=hypothetical_actions(engine,text,base)
            baseline=measures([engine.ids[i] for i,_ in base],qrels[qid])["ndcg10"]
            best=-1.
            if actions:
                for action in actions:
                    delta=measures([engine.ids[i] for i in action["proposal"]],qrels[qid])["ndcg10"]-baseline
                    action_X.append(action["features"])
                    action_y.append(delta)
                    best=max(best,delta)
            # Cost-sensitive: only search if a proposed action really improves
            # retrieval by >1 percentage point in the training observation.
            gate_X.append(qf)
            gate_y.append(int(best>=0.012))
            by_dataset[name]+=1
    return np.asarray(gate_X),np.asarray(gate_y),np.asarray(action_X),np.asarray(action_y),dict(by_dataset)

class Controller:
    def __init__(self):
        self.gate=None
        self.regressor=None
        self.positive_rate=None
        self.action_stats=None
    def fit(self,train_data):
        gx,gy,ax,ay,sizes=make_train_rows(train_data)
        self.positive_rate=float(gy.mean()) if len(gy) else 0.
        self.action_stats={"gate_positive":int(sum(gy)),"gate_total":len(gy),
            "actions":len(ay),"positive_actions":int(sum(ay>0.00001)),"fit_by_dataset":sizes}
        if len(set(gy))>1:
            self.gate=make_pipeline(StandardScaler(),LogisticRegression(
                C=0.5,class_weight="balanced",max_iter=1500,random_state=2026))
            self.gate.fit(gx,gy)
        if len(ay)>20 and np.std(ay)>0:
            self.regressor=make_pipeline(StandardScaler(),Ridge(alpha=50.0))
            self.regressor.fit(ax,ay)
        return self
    def run(self,index,question):
        base=index.search(question,"bm25",100)
        ranked=[i for i,_ in base]
        d={"searched":False,"accepted":False,"calls":1,"gap":0.,"gate_probability":0.,
            "predicted_delta":0.,"candidates":0}
        if len(base)<5:return ranked,d
        _,missing,_,gap,margin=scores(index,question,base)
        d["gap"]=gap
        if gap<PRE_GAP_FLOOR or len(missing)<1 or self.gate is None:
            return ranked,d
        probability=float(self.gate.predict_proba([question_features(index,question,base)])[0,1])
        d["gate_probability"]=probability
        if probability<PRE_SEARCH_PROB:return ranked,d
        d["searched"]=True;d["calls"]=2
        actions,_=hypothetical_actions(index,question,base)
        d["candidates"]=len(actions)
        if not actions or self.regressor is None:return ranked,d
        predictions=self.regressor.predict(np.asarray([a["features"] for a in actions]))
        pick=int(np.argmax(predictions))
        value=float(predictions[pick])
        d["predicted_delta"]=value
        if value<=POST_PREDICTED_GAIN+COST_PER_SEARCH:
            return ranked,d
        proposal=actions[pick]["proposal"]
        d["accepted"]=True
        d["selected_rank"]=actions[pick]["source_rank"]
        return proposal,d

def evaluate(records,controller,result_dir):
    result_dir.mkdir(parents=True,exist_ok=True)
    methods=["bm25","v61","v62"]
    all_summary=[]
    for name,engine,queries,qrels,ids in records:
        observations={m:[] for m in methods}
        for qid in ids:
            for method in methods:
                start=time.perf_counter()
                if method=="bm25":
                    pred=[i for i,_ in engine.search(queries[qid],"bm25",100)]
                    info={"calls":1,"searched":False,"accepted":False}
                elif method=="v61":
                    pred,info=guarded(engine,queries[qid])
                else:pred,info=controller.run(engine,queries[qid])
                ms=(time.perf_counter()-start)*1000
                metric=measures([engine.ids[i] for i in pred],qrels[qid])
                observations[method].append({"qid":qid,**metric,"calls":info["calls"],
                    "searched":info["searched"],"accepted":info["accepted"],
                    "latency_ms":ms,"gate_probability":info.get("gate_probability"),
                    "predicted_delta":info.get("predicted_delta")})
        baseline={r["qid"]:r for r in observations["bm25"]}
        for method,rows in observations.items():
            change=[r["ndcg10"]-baseline[r["qid"]]["ndcg10"] for r in rows]
            summary={"dataset":name,"partition":"development-validation","method":method,
                 "count":len(rows),"corpus":len(engine.ids),"split_seed":INNER_SEED,
                 "metrics":{k:float(np.mean([r[k] for r in rows])) for k in ["ndcg10","recall10","recall100","mrr10","calls","latency_ms"]},
                 "wins":sum(v>1e-10 for v in change),"losses":sum(v< -1e-10 for v in change),
                 "ties":sum(abs(v)<=1e-10 for v in change),
                 "second_searches":sum(x["searched"] for x in rows),
                 "reorders":sum(x["accepted"] for x in rows)}
            all_summary.append(summary)
            path=result_dir/f"{name}_{method}_per_query.jsonl"
            with path.open("w") as f:
                for row in rows:f.write(json.dumps(row)+"\n")
            print(f'{name}/{method}: n={summary["count"]} nDCG@10={summary["metrics"]["ndcg10"]:.5f} '
                  f'recall10={summary["metrics"]["recall10"]:.5f} '
                  f'calls={summary["metrics"]["calls"]:.3f}, searches={summary["second_searches"]}, '
                  f'win/loss={summary["wins"]}/{summary["losses"]}',flush=True)
    (result_dir/"summary.json").write_text(json.dumps({"design":"action-value learned on dev-fit only",
              "model_train":controller.action_stats,"validation":all_summary},indent=2))
    return all_summary

def smoke():
    from benchmark_v6 import Retriever
    doc=[{"_id":"one","title":"stellar spectroscopy","text":"spectroscopy records stellar bright emissions"},
         {"_id":"two","title":"oceans","text":"oceans contain salinity and dissolved minerals"},
         {"_id":"three","title":"climate","text":"global heat changes climate measurements"},
         {"_id":"four","title":"trees","text":"trees capture carbon through photosynthesis"},
         {"_id":"five","title":"soil","text":"soil nutrition and minerals alter tree growth"}]
    idx=Retriever(doc)
    b=idx.search("stellar bright emissions","bm25",100)
    assert len(b)>0
    f=question_features(idx,"stellar bright emissions",b)
    assert len(f)==11
    assert inner_part("scifact","123")==inner_part("scifact","123")
    assert set(inner_part("scifact",str(i)) for i in range(100))=={"fit","validate"}
    c=Controller()
    r,d=c.run(idx,"stellar bright emissions")
    assert r[0]==b[0][0] and d["calls"]==1
    print("V6.2 SMOKE PASS")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=["smoke","dev"])
    p.add_argument("--data",type=pathlib.Path,default=pathlib.Path("data"))
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v62"))
    args=p.parse_args()
    if args.command=="smoke":return smoke()
    train=[];validate=[]
    for name in ["scifact","nfcorpus"]:
        folder=download(name,args.data)
        docs,queries,labels=load(folder)
        engine=Retriever(docs)
        dev=[q for q in sorted(labels) if q in queries and partition(name,q)=="dev"]
        fit=[q for q in dev if inner_part(name,q)=="fit"]
        valid=[q for q in dev if inner_part(name,q)=="validate"]
        train.append((name,engine,queries,labels,fit))
        validate.append((name,engine,queries,labels,valid))
        print(f'{name}: dev_fit={len(fit)}, dev_validate={len(valid)}, sealed=NEVER READ',flush=True)
    controller=Controller().fit(train)
    print("TRAINING:",json.dumps(controller.action_stats),flush=True)
    evaluate(validate,controller,args.out)

if __name__=="__main__":main()
