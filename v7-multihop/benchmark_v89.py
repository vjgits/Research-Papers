#!/usr/bin/env python3
"""Frozen exploratory REBEL natural source-first generator. Not a DocRED leaderboard run.
Uses first 20 docs from previously inspected V8.8 cohort (NOT fresh). Official DocRED
source, 16-property projection, fixed first 6 short source sentences/doc; no gold
entities or labels passed into the model. Exact cited sentence not semantic entailment.
"""
import argparse,collections,hashlib,json,pathlib,time
import numpy as np
from pger_v89_core import classify_output,accepted,verify_quote,gold_matches,RELATION_MAP,norm
MODEL='Babelscape/rebel-large'
SEED=20261027
DOCS=20
MAX_SENT=6
MAX_CHARS=500

def fixed_sentences(sents):
    return [(i,x) for i,x in enumerate(sents) if 20<=len(x)<=MAX_CHARS][:MAX_SENT]

def score_one(doc,raw_predictions,baseline):
    r=accepted(raw_predictions)
    valid=all(verify_quote(x,doc['sents']) for x in raw_predictions)
    n,ev,examples=gold_matches(r,doc)
    raw_hits,raw_ev,_=gold_matches([x for x in raw_predictions if x['r'] is not None],doc)
    b,b_ev,_=gold_matches(baseline,doc)
    gold=[lab for lab in doc['labels'] if lab['r'] in RELATION_MAP.values()]
    return {'correct_rebel':n,'correct_rebel_evidence_overlap':ev,'correct_rebel_raw_mapped':raw_hits,'correct_rebel_raw_mapped_evidence_overlap':raw_ev,
            'correct_regex':b,'correct_regex_evidence_overlap':b_ev,
            'gold_total':len(gold),'source_valid':valid,'matches':examples,
            'raw_proposals':len(raw_predictions),'mapped_proposals':sum(x['r'] is not None for x in raw_predictions),
            'anchored_proposals':len(r),
            'relation_histogram':dict(collections.Counter(x['r_text'] for x in raw_predictions))}

def run(out):
    from benchmark_v88_docred import load_docred,select_docs
    from pger_v88_core import regex_mentions,relation_triples
    import torch
    from transformers import AutoTokenizer,AutoModelForSeq2SeqLM
    torch.set_num_threads(2)
    out.mkdir(exist_ok=True,parents=True)
    docs,sha=load_docred(); selection=select_docs(docs,60)[:DOCS]
    ids=[i for i,_ in selection]; idsha=hashlib.sha256(','.join(map(str,ids)).encode()).hexdigest()
    t=time.perf_counter();tok=AutoTokenizer.from_pretrained(MODEL)
    model=AutoModelForSeq2SeqLM.from_pretrained(MODEL).eval()
    load_s=time.perf_counter()-t
    resolved_revision=getattr(model.config,'_commit_hash',None)
    # This is a development cohort already used for V8.8. Freeze and disclose.
    results=[];cost=[];all_raw=[];pairs=0
    if (out/'per_doc.jsonl').exists(): (out/'per_doc.jsonl').unlink()
    for ix,(doc_idx,doc) in enumerate(selection):
        sents=doc['sents'];selected=fixed_sentences(sents)
        raw=[];t0=time.perf_counter()
        for sid,sentence in selected:
            inputs=tok(sentence,return_tensors='pt',max_length=256,truncation=True)
            with torch.no_grad():
                tokens=model.generate(**inputs,do_sample=False,num_beams=1,max_new_tokens=96)
            decoded=tok.batch_decode(tokens,skip_special_tokens=False)[0]
            raw.extend(classify_output(decoded,sentence,sid))
            pairs+=1
        inference_s=time.perf_counter()-t0;cost.append(inference_s)
        # Budget-aligned regex reads the same selected six sentences, not whole doc.
        # sentence indexes preserved when assigning source ids.
        baseline=[]
        for sid,sentence in selected:
            for c in relation_triples(regex_mentions([sentence]),[sentence]):
                baseline.append({'h':c.h,'r':c.r,'t':c.t,'sentence_id':sid,
                                 'quote':sentence,'source_sha256':hashlib.sha256(sentence.encode()).hexdigest(),
                                 'surface_anchored':True})
        summary=score_one(doc,raw,baseline)
        annotated=[x for x in doc['labels'] if x['r'] in RELATION_MAP.values()]
        chosen={sid for sid,_ in selected}
        evidence_reachable=sum(bool(set(x.get('evidence') or []).intersection(chosen)) for x in annotated)
        summary.update({'doc_id':doc_idx,'title':doc['title'], 'selected_sentence_ids':sorted(chosen),
                        'annotated_gold_with_evidence_in_selected_window':evidence_reachable,
                        'inference_s':round(inference_s,3), 'predictions':raw[:200]})
        results.append(summary)
        all_raw.extend(raw)
        print('V8.9 REBEL',ix+1,'/',DOCS,'sentences',len(selected),'gold',summary['gold_total'],'rebel',summary['correct_rebel'],'regex',summary['correct_regex'],flush=True)
        with (out/'per_doc.jsonl').open('a') as f:f.write(json.dumps(summary,ensure_ascii=False)+'\n')
    total=sum(x['gold_total'] for x in results)
    rebel=sum(x['correct_rebel'] for x in results)
    regex=sum(x['correct_regex'] for x in results)
    raw_rebel=sum(x['correct_rebel_raw_mapped'] for x in results)
    source=sum(x['annotated_gold_with_evidence_in_selected_window'] for x in results)
    rng=np.random.default_rng(SEED);paired=[]
    for _ in range(3000):
        z=rng.integers(0,len(results),len(results));den=sum(results[i]['gold_total'] for i in z)
        paired.append(100*sum(results[i]['correct_rebel']-results[i]['correct_regex'] for i in z)/max(1,den))
    report={
      'status':'exploratory_20_doc_development_pilot','model':MODEL,'model_revision':resolved_revision or 'not_pinned','model_load_s':round(load_s,3),
      'model_license':'cc-by-nc-sa-4.0 (non-commercial research restrictions)',
      'docred_sha256':sha,'v88_original_60_subset':'first_20','doc_ids_sha256':idsha,
      'n_documents':len(results),'n_inference_sentences':pairs,'sentence_limit_per_doc':MAX_SENT,
      'gold_positive_ontology_triples':total,'annotated_gold_with_evidence_in_window':source,
      'baseline_regex_gold_hits':regex,'rebel_raw_gold_hits':raw_rebel,
      'rebel_accepted_gold_hits':rebel,
      'baseline_recall':round(regex/max(1,total),6),'rebel_recall':round(rebel/max(1,total),6),
      'rebel_raw_mapped_recall':round(raw_rebel/max(1,total),6),
      'paired_gain_pp':round(100*(rebel-regex)/max(1,total),3),
      'paired_document_bootstrap_95_pp':[round(float(x),3) for x in np.quantile(paired,[.025,.975])],
      'raw_predictions':len(all_raw),'mapped_predictions':sum(x['r'] is not None for x in all_raw),
      'source_anchored_mapped':sum(bool(x['r'] and x['surface_anchored']) for x in all_raw),
      'prediction_relation_histogram':dict(collections.Counter(x['r_text'] for x in all_raw).most_common(30)),
      'all_source_span_valid':all(x['source_valid'] for x in results),
      'docs_with_no_accepted_triples':sum(x['anchored_proposals']==0 for x in results),
      'inference_total_s':round(sum(cost),3),'inference_mean_s_per_doc':round(float(np.mean(cost)),3),
      'inference_p95_s_per_doc':round(float(np.percentile(cost,95)),3),
      'limitations':['selected gold-positive DocRED dev docs, same as inspected V8.8 corpus','first six short sentences per document',
         'strict exact-name/16-property mapping undercounts paraphrases','no manual adjudication of unlabeled triples or false relations',
         'no final answer generation or 4+ hop retrieval','source citations are not semantic truth proofs',
         'REBEL model is published prior work, not PGER novelty']
    }
    (out/'summary.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    review=[]
    for x in results:
        for p in x['predictions'][:4]:
            review.append({'doc_id':x['doc_id'],'title':x['title'],'prediction':p,
                           'annotator_questions':['Is the source sentence about this head and tail?','Is the relationship logically entailed, neutral or contradicted?','Does it involve coreference?'],
                           'independent_human_review':'PENDING'})
    (out/'review_queue.json').write_text(json.dumps(review[:40],indent=2,ensure_ascii=False))
    print('PGER V8.9 COMPLETE');print(json.dumps(report,indent=2),flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['smoke','run']);p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('results-v89'));a=p.parse_args()
    if a.command=='smoke':
        from pger_v89_core import parse_rebel
        assert parse_rebel('<triplet> Ana <subj> Bob <obj> spouse')==[('Ana','spouse','Bob')]
        print('V8.9 smoke passed');return
    run(a.out)
if __name__=='__main__':main()