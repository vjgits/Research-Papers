#!/usr/bin/env python3
"""PGER V13B: open-weights entailment verifier *safety gate*, independent HANS.

Evaluate factual direction/lexical-subsequence failure on human-labeled
HANS test (McCoy et al, ACL 2019), 3 binary heuristic groups. This corpus
was NOT used in the MiniLM NLI's original SNLI/MNLI fine-tuning, subject to
normal public/pretraining contamination caveats. No hand-wavy sample labels.

Do NOT call the model PGER's edge verifier unless it passes this independent
specificity check AND subsequent human-labelled document-edge tests.
No changes to V7–V13 retrieval, no model-generated facts, no paid APIs.
"""
import argparse,collections,hashlib,json,pathlib,time,urllib.request
import numpy as np
from scipy.special import softmax

MODEL="cross-encoder/nli-MiniLM2-L6-H768"
MODEL_LICENSE="apache-2.0"
DATA_URL=("https://raw.githubusercontent.com/tommccoy1/hans/"
          "master/heuristics_evaluation_set.jsonl")
SEED=20261028
SAMPLE_PER_CELL=45
MAX_EXAMPLES=3*2*SAMPLE_PER_CELL
LABELS=("contradiction","entailment","neutral")
FPR_MAX=.10
PRECISION_MIN=.90
RECALL_MIN=.75

def download(root):
    root.mkdir(parents=True,exist_ok=True)
    p=root/"heuristics_evaluation_set.jsonl"
    if not p.exists():
        req=urllib.request.Request(DATA_URL,headers={"User-Agent":"PGER-V13B-independent-NLI-test"})
        with urllib.request.urlopen(req,timeout=180) as r:binary=r.read()
        assert len(binary)>100000
        tmp=p.with_suffix(".tmp");tmp.write_bytes(binary);tmp.replace(p)
    raw=p.read_bytes()
    rows=[json.loads(line) for line in raw.decode("utf8").splitlines() if line.strip()]
    assert len(rows)==30000,"Unexpected public HANS record count"
    return rows,hashlib.sha256(raw).hexdigest()

def sample(rows):
    groups=collections.defaultdict(list)
    for i,r in enumerate(rows):
        h=r.get("heuristic")
        g=r.get("gold_label")
        if h in ("lexical_overlap","subsequence","constituent") and g in (
            "entailment","non-entailment"):
            groups[(h,g)].append(i)
    rng=np.random.default_rng(SEED)
    indices=[]
    for h in ("lexical_overlap","subsequence","constituent"):
        for label in ("entailment","non-entailment"):
            pool=groups[(h,label)]
            assert len(pool)>=SAMPLE_PER_CELL
            choice=rng.choice(pool,SAMPLE_PER_CELL,replace=False)
            indices.extend(int(j) for j in choice)
    assert len(set(indices))==MAX_EXAMPLES
    return [rows[i] for i in indices],indices

def lexical_control(premise,hyp):
    # Deliberately simple false proof oracle: labels entailment whenever
    # all hypothesis words occur verbatim in the premise; HANS attacks this.
    import re
    lex=lambda s:set(re.findall(r"[a-z]+",str(s).lower()))
    return lex(hyp)<=lex(premise)

def measure(samples,predicted):
    true=np.asarray([r["gold_label"]=="entailment" for r in samples],dtype=bool)
    assert len(predicted)==len(true)
    pred=np.asarray(predicted,dtype=bool)
    tp=int(np.sum(true&pred));fp=int(np.sum(~true&pred))
    tn=int(np.sum(~true&~pred));fn=int(np.sum(true&~pred))
    p=tp/max(1,tp+fp)
    recall=tp/max(1,tp+fn)
    fpr=fp/max(1,fp+tn)
    acc=(tp+tn)/max(1,len(true))
    by={}
    for h in ("lexical_overlap","subsequence","constituent"):
        idx=np.asarray([s["heuristic"]==h for s in samples],dtype=bool)
        pos=int(np.sum(idx&true));neg=int(np.sum(idx&~true))
        hit=int(np.sum(idx&true&pred))
        false=int(np.sum(idx&~true&pred))
        by[h]={"n":int(sum(idx)),"entailment_recall":round(hit/max(1,pos),5),
               "false_entailment_rate":round(false/max(1,neg),5),
               "false_accept_count":false,"non_entailment_n":neg}
    return {"accuracy":round(acc,5),"precision":round(p,5),
            "entailment_recall":round(recall,5),
            "non_entailment_false_positive_rate":round(fpr,5),
            "tp":tp,"fp":fp,"tn":tn,"fn":fn,"by_heuristic":by}

def run(folder,out):
    from sentence_transformers import CrossEncoder
    from huggingface_hub import model_info
    import torch
    torch.set_num_threads(2)
    rows,sha=download(folder)
    samples,indices=sample(rows)
    t=time.process_time()
    info=model_info(MODEL)
    revision=info.sha
    model=CrossEncoder(MODEL,revision=revision,device="cpu",max_length=192)
    model_load= (time.process_time()-t)*1000.
    config=model.model.config
    labels={int(i):str(label).lower() for i,label in config.id2label.items()}
    assert set(labels.values())==set(LABELS),f"Unexpected NLI class order: {labels}"
    t=time.process_time()
    pairs=[(r["sentence1"],r["sentence2"]) for r in samples]
    logits=model.predict(pairs,batch_size=32,show_progress_bar=False)
    infer=(time.process_time()-t)*1000.
    logits=np.asarray(logits)
    assert logits.shape==(len(samples),3)
    probs=softmax(logits,axis=1)
    entail_idx=next(i for i,l in labels.items() if l=="entailment")
    pred=np.argmax(probs,axis=1)==entail_idx
    simple=[lexical_control(*v) for v in pairs]
    result=measure(samples,pred)
    baseline=measure(samples,simple)
    # Conservative predeclared gate: too many false proofs -> prohibit use.
    passing=(result["precision"]>=PRECISION_MIN
             and result["entailment_recall"]>=RECALL_MIN
             and result["non_entailment_false_positive_rate"]<=FPR_MAX
             and all(v["false_entailment_rate"]<=FPR_MAX
                     for v in result["by_heuristic"].values()))
    summary={"stage":"V13B independent NLI verification",
       "dataset":"HANS human-labeled diagnostic (ACL 2019)",
       "source_url":DATA_URL,"dataset_sha256":sha,
       "n_total_hans":len(rows),"n_evaluated":len(samples),
       "per_heuristic_per_gold_label":SAMPLE_PER_CELL,
       "seed":SEED,"model":MODEL,"model_revision":revision,
       "model_license":MODEL_LICENSE,"model_class_labels":labels,
       "model_load_cpu_ms":round(model_load,2),
       "inference_cpu_ms":round(infer,2),
       "inference_per_pair_batch_amortized_cpu_ms":round(infer/len(samples),3),
       "model_results":result,"lexical_control_results":baseline,
       "predeclared_gate":{"min_entailment_precision":PRECISION_MIN,
         "min_entailment_recall":RECALL_MIN,"max_non_entailment_false_positive":FPR_MAX,
         "max_each_heuristic_false_positive":FPR_MAX,
         "passed":bool(passing)},
       "pger_relation_verifier_approved":False,
       "interpretation":("Passing HANS alone would NOT establish trustworthy PGER factual link verification. "
         "Require independently labeled domain-specific premise/hypothesis/source spans and negative counterexamples."),
       "limitations":[
         "NLI entailment pairs are not PGER multi-source question edges",
         "Model trained on SNLI/MNLI; HANS separate known diagnostic public data",
         "Only 270 balanced fixed samples, not full 30000 HANS",
         "Model predictions no gold training/fine-tuning",
         "Inference CPU includes batch inference but not cold network download or production serving",
         "No factual answer, source provenance verification or evidence chain correctness measured",
         "If any safety gate fails, NLI must remain unpromoted"]}
    out.mkdir(parents=True,exist_ok=True)
    (out/"summary.json").write_text(json.dumps(summary,indent=2))
    with (out/"examples.jsonl").open("w") as f:
        for j,(i,r) in enumerate(zip(indices,samples)):
            f.write(json.dumps({
                "source_row":i,"premise":r["sentence1"],
                "hypothesis":r["sentence2"],"label":r["gold_label"],
                "heuristic":r["heuristic"],"subcase":r.get("subcase"),
                "predict_entailment":bool(pred[j]),
                "p_entailment":round(float(probs[j,entail_idx]),5),
                "lexical_control":bool(simple[j])})+"\n")
    print("V13B_RESULT",json.dumps(summary),flush=True)

def smoke():
    s=[
        {"gold_label":"entailment","heuristic":"lexical_overlap"},
        {"gold_label":"non-entailment","heuristic":"lexical_overlap"}]
    x=measure(s,[True,True])
    assert x["tp"]==1 and x["fp"]==1
    assert lexical_control("A woman visited Paris","Paris was visited") is False
    print("V13B independent NLI binary-gate smoke PASS")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("smoke","run"))
    p.add_argument("--data",type=pathlib.Path,default=pathlib.Path("data/hans_v13b"))
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v13b"))
    a=p.parse_args()
    if a.command=="smoke":return smoke()
    run(a.data,a.out)
if __name__=="__main__":main()
