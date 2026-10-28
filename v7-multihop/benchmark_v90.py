#!/usr/bin/env python3
"""PGER V9.0: new-document 2/3/6-sentence REBEL generation budget pilot.

Strict provenance and annotated-gold recall, no oracle entity/relation labels at inference.
These are standard sentence selection comparators; a novel proof-gap policy is NOT
being validated by this DocRED relation-extraction experiment.
"""
import argparse, hashlib, json, pathlib, time, collections, statistics
import numpy as np
from benchmark_v88_docred import load_docred,select_docs
from benchmark_v89 import fixed_sentences
from pger_v89_core import classify_output,accepted,gold_matches,verify_quote,RELATION_MAP
from pger_v88_core import regex_mentions,relation_triples
from pger_v90_core import selected_ids

SEED=20261027
MODEL='Babelscape/rebel-large'
REV='44eb6cb4585df284ce6c4d6a7013f83fe473c052'
METHODS=('first2','lexical2','coverage2','coverage3','full6')
DOCS=36


def select_fresh_docs(all_docs):
    selection=select_docs(all_docs,96)
    old={i for i,_ in selection[:60]}
    new=selection[60:96]
    assert len(new)==36 and not old.intersection({i for i,_ in new})
    return new


def score_doc(doc,by_sentence,methods,source_sents):
    out={}
    sents=doc['sents']
    for meth in METHODS:
        chosen=methods[meth]
        raw=[x for sid in chosen for x in by_sentence.get(sid,[])]
        anchored=accepted(raw)
        hit,overlap,_=gold_matches(anchored,doc)
        rawhit,rawov,_=gold_matches([x for x in raw if x['r']],doc)
        regex=[]
        for sid in chosen:
            sentence=sents[sid]
            for t in relation_triples(regex_mentions([sentence]),[sentence]):
                regex.append({'h':t.h,'r':t.r,'t':t.t,'sentence_id':sid,'quote':sentence,
                   'source_sha256':hashlib.sha256(sentence.encode()).hexdigest(),'surface_anchored':True})
        base,baseov,_=gold_matches(regex,doc)
        out[meth]={'hit':hit,'gold_evidence_overlap':overlap,'raw_mapped_hit':rawhit,
                    'regex_hit':base,'selected':chosen,'generated_count':len(raw),
                    'mapped_count':sum(bool(z['r']) for z in raw),
                    'anchored_count':len(anchored),
                    'source_valid':all(verify_quote(z,sents) for z in raw),
                    'gold_window_touch':sum(bool(set(l.get('evidence') or []) & set(chosen)) for l in doc['labels'] if l['r'] in RELATION_MAP.values())}
    return out


def boot(records,method_a,method_b,metric='hit'):
    rng=np.random.default_rng(SEED)
    sims=[]
    for _ in range(4000):
        chosen=rng.integers(0,len(records),len(records))
        d=sum(records[i]['methods'][method_a][metric]-records[i]['methods'][method_b][metric] for i in chosen)
        n=sum(records[i]['gold_count'] for i in chosen)
        sims.append(100*d/max(1,n))
    diff=100*sum(r['methods'][method_a][metric]-r['methods'][method_b][metric] for r in records)/max(1,sum(r['gold_count'] for r in records))
    return {'delta_pp':round(diff,3),'doc_cluster_ci95_pp':[round(float(x),3) for x in np.quantile(sims,[.025,.975])],
       'wins':sum(r['methods'][method_a][metric]>r['methods'][method_b][metric] for r in records),
       'losses':sum(r['methods'][method_a][metric]<r['methods'][method_b][metric] for r in records)}


def run(out):
    import torch
    from transformers import AutoTokenizer,AutoModelForSeq2SeqLM
    torch.set_num_threads(2)
    out.mkdir(parents=True,exist_ok=True)
    docs,docred_sha=load_docred();selection=select_fresh_docs(docs)
    IDs=[idx for idx,_ in selection]
    sample_sha=hashlib.sha256(','.join(map(str,IDs)).encode()).hexdigest()
    t=time.perf_counter()
    tok=AutoTokenizer.from_pretrained(MODEL,revision=REV)
    model=AutoModelForSeq2SeqLM.from_pretrained(MODEL,revision=REV).eval()
    model_load_s=time.perf_counter()-t
    records=[];costs=collections.defaultdict(list);all_pred=[];review=[]
    for k,(docid,doc) in enumerate(selection):
        sentences=fixed_sentences(doc['sents'])
        chosen={meth:selected_ids(sentences,meth) for meth in METHODS}
        assert len(set(chosen['coverage2']))==len(chosen['coverage2'])
        infer={};time_by_sentence={};raw=[]
        for sid,text in sentences:
            t=time.perf_counter()
            inputs=tok(text,return_tensors='pt',max_length=256,truncation=True)
            with torch.no_grad():
                tokens=model.generate(**inputs,do_sample=False,num_beams=1,max_new_tokens=96)
            cost=time.perf_counter()-t
            decoded=tok.batch_decode(tokens,skip_special_tokens=False)[0]
            infer[sid]=classify_output(decoded,text,sid)
            raw.extend(infer[sid]);time_by_sentence[sid]=cost
        # Do not inspect gold relations/DocRED evidence IDs until generation and sentence choice are complete.
        met=score_doc(doc,infer,chosen,sentences)
        total_gold=sum(l['r'] in RELATION_MAP.values() for l in doc['labels'])
        for meth in METHODS:
            met[meth]['measured_infer_sum_s']=round(sum(time_by_sentence[sid] for sid in chosen[meth]),4)
            costs[meth].append(met[meth]['measured_infer_sum_s'])
        records.append({'docid':docid,'title':doc['title'],'gold_count':total_gold,
            'methods':met,'all_sids':[sid for sid,_ in sentences],
            'per_sentence_cpu_s':{str(i):round(v,4) for i,v in time_by_sentence.items()},
            'raw_triples':raw[:100]})
        for pred in raw:
            if pred['r'] and pred['surface_anchored']:
                review.append({'docid':docid,'title':doc['title'],'triple':pred,'human_entailment':'PENDING',
                    'human_direction':'PENDING','human_contradiction':'PENDING'})
        print('V9.0 new DocRED',k+1,'/',DOCS,'gold',total_gold,'REBEL full',met['full6']['hit'],
              'coverage2',met['coverage2']['hit'],'first2',met['first2']['hit'],flush=True)
    total=sum(r['gold_count'] for r in records)
    summary={}
    for meth in METHODS:
        a=[r['methods'][meth] for r in records]
        seconds=costs[meth]
        summary[meth]={'calls':sum(len(x['selected']) for x in a),
         'gold_hits':sum(x['hit'] for x in a),
         'recall':round(sum(x['hit'] for x in a)/max(1,total),6),
         'gold_evidence_overlap':sum(x['gold_evidence_overlap'] for x in a),
         'regex_gold_hits':sum(x['regex_hit'] for x in a),
         'mapped_raw_gold_hits':sum(x['raw_mapped_hit'] for x in a),
         'all_quote_integrity':all(x['source_valid'] for x in a),
         'inference_cpu_s_sum_shared_run':round(sum(seconds),3),
         'inference_cpu_s_per_doc_mean':round(float(np.mean(seconds)),3),
         'inference_cpu_s_per_doc_p95':round(float(np.percentile(seconds,95)),3),
         'gold_evidence_in_selected_windows':sum(x['gold_window_touch'] for x in a)}
    report={'version':'V9.0','type':'new_docred_component_efficiency_pilot',
        'model':MODEL,'model_revision':REV,
        'license':'CC BY NC SA 4.0 / research non-commercial',
        'n_docs':len(records),'docred_sha256':docred_sha,'sample_ids_sha256':sample_sha,
        'new_docs_exclude_v87_54_and_v88_60':True,
        'selection':'V8.8 eligible deterministic positions 61-96 (zero overlap with V8.8 first60)',
        'source_gold_triples':total,'model_load_s':round(model_load_s,3),
        'methods':summary,
        'paired':{
          'coverage2_vs_first2':boot(records,'coverage2','first2'),
          'coverage2_vs_lexical2':boot(records,'coverage2','lexical2'),
          'coverage3_vs_full6':boot(records,'coverage3','full6'),
          'coverage2_vs_full6':boot(records,'coverage2','full6')},
        'caveats':['Official public dev data, new to PGER, not model-unseen or sealed','DocRED is positive annotation; do not calculate precision from unlabelled triples',
           'Quote integrity is not logical entailment','Question-level answer-changing proof-gap scheduler NOT evaluated here',
           'Inference per-arm CPU sums reconstructed from exact per-sentence measured generation in a shared run, not standalone full serving latency',
           'Greedy coverage is well-known; no algorithmic originality or SOTA claim']}
    (out/'summary.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    with (out/'per_doc.jsonl').open('w') as f:
        for rec in records:f.write(json.dumps(rec,ensure_ascii=False)+'\n')
    (out/'human_review_queue.json').write_text(json.dumps(review[:100],indent=2,ensure_ascii=False))
    print('V9.0 FROZEN EXPERIMENT COMPLETE');print(json.dumps(report,indent=2),flush=True)
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['smoke','run']);p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('results-v90'));args=p.parse_args()
    if args.command=='smoke':
        from pger_v90_core import selected_ids
        sample=[(1,'Alex was born in City A.'),(2,'Paris lies in France.'),(3,'The economy is stable.'),(4,'University has graduates.')]
        assert len(selected_ids(sample,'coverage2'))==2
        assert len(set(selected_ids(sample,'coverage2')))==2
        print('V9.0 smoke passed');return
    run(args.out)
if __name__=='__main__':main()