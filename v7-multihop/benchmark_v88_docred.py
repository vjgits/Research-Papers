#!/usr/bin/env python3
"""Frozen PGER V8.8 source-first entity/relation proposal diagnostic.
No gold entity pair or predicate supplied to extraction. Gold positive annotations used
only for cohort inclusion and post-prediction scoring. Unlabeled pairs NOT negatives.
Not official DocRED F1, multi-hop QA or truth claim validation.
"""
import argparse,collections,gzip,hashlib,json,pathlib,time,zipfile,sys
import numpy as np
from pger_v87_core import normalize_doc, TEMPLATES
from pger_v88_core import regex_mentions,spacy_mentions,pair_candidates,relation_triples,verify_triple,nli_filter,norm,name_set

SEED=20261027
# Previously inspected documents from V8.7 100-pair pilot; exclude their exact IDs.
EXCLUDE=frozenset([23,33,39,48,57,75,90,106,109,115,119,183,192,233,254,271,282,302,304,345,353,366,417,420,462,502,523,554,580,606,620,639,681,683,684,693,712,721,746,754,763,769,771,830,831,857,890,895,929,946,947,982,988,996])
NLI_MODEL='cross-encoder/nli-MiniLM2-L6-H768';NLI_REV='9aa22b250d25a10ac39ab4a6b2bc28213507cb0c'

def load_docred():
    path=pathlib.Path('/mnt/data/PGER_V87_DocRED_Results.zip')
    if path.exists():
        with zipfile.ZipFile(path) as z: raw=z.read('cache/docred_dev.json.gz')
    else:
        import urllib.request
        url='https://huggingface.co/datasets/thunlp/docred/resolve/main/data/dev.json.gz?download=true'
        with urllib.request.urlopen(url,timeout=120) as resp:raw=resp.read()
    if raw[:2]!=b'\x1f\x8b':raise RuntimeError('DocRED dataset missing/invalid')
    docs=json.loads(gzip.decompress(raw).decode())
    if len(docs)<900:raise AssertionError('Dataset invalid')
    return docs,hashlib.sha256(raw).hexdigest()

def select_docs(docs,n=60):
    # Deterministically choose disjoint document IDs with >=1 16-ontology gold-positive relation.
    from pger_v87_core import TEMPLATES
    order=sorted(range(len(docs)),key=lambda i:hashlib.sha256(f'v88-sealed-v1:{SEED}:{i}:{docs[i].get("title","")}'.encode()).digest())
    eligible=[]
    for idx in order:
        if idx in EXCLUDE:continue
        d=normalize_doc(docs[idx]);labels=[x for x in d['labels'] if x['r'] in TEMPLATES]
        if d['sents'] and labels:
            eligible.append((idx,d))
            if len(eligible)>=n:break
    if len(eligible)!=n:raise AssertionError('Too few eligible docs')
    return eligible

def canonical_aliases(group):
    return {norm(m['name']) for m in group if norm(m['name'])}

def scored_doc(idx,doc,regex,spacy,nli=None):
    """NO gold read until every extraction/verification output is frozen."""
    sents=doc['sents'];results={};preds={};objects={}
    for method,mentions in [('regex',regex),('spacy',spacy)]:
        pairs=pair_candidates(mentions,sents)
        ts=relation_triples(mentions,sents)
        objects[method]={'mentions':mentions,'pairs':pairs,'triples':ts}
        preds[method]=[dict(h=t.h,r=t.r,t=t.t,sentence_id=t.sentence_id,quote=t.quote[:600],method=t.method) for t in ts[:60]]
        if nli is not None:
            def infer(data):return nli.predict(data,batch_size=16,show_progress_bar=False)
            t0=time.perf_counter();accepted,status,calls=nli_filter(ts,infer,TEMPLATES,cap=48)
            objects[method+'_nli']={'triples':accepted,'model_pairs':calls,'model_ms':round((time.perf_counter()-t0)*1000,2),
                                     'preselected_candidates':min(len(ts),48)}
            preds[method+'_nli']=[dict(h=t.h,r=t.r,t=t.t,sentence_id=t.sentence_id) for t in accepted]
    # Gold is read ONLY here, after both methods, all candidate pairs and all inference calls.
    gold=[]
    for lab in doc['labels']:
        if lab['r'] not in TEMPLATES:continue
        try:h=int(lab['h']);t=int(lab['t'])
        except Exception:continue
        if h==t or h<0 or t<0 or h>=len(doc['vertexSet']) or t>=len(doc['vertexSet']):continue
        ha=canonical_aliases(doc['vertexSet'][h]);ta=canonical_aliases(doc['vertexSet'][t])
        if not ha or not ta:continue
        gold.append(dict(h=h,t=t,r=lab['r'],ha=ha,ta=ta,evidence=set(lab.get('evidence') or [])))
    def eval_mentions(ms):
        names=name_set(ms)
        return {'gold_head_detected':sum(bool(names&x['ha']) for x in gold),
                'gold_tail_detected':sum(bool(names&x['ta']) for x in gold),
                'gold_pair_both_entities_detected':sum(bool(names&x['ha']) and bool(names&x['ta']) for x in gold)}
    def eval_pairs(ps):
        signs={(norm(a.name),norm(b.name)) for a,b in ps}
        return sum(any((a,b) in signs or (b,a) in signs for a in x['ha'] for b in x['ta']) for x in gold)
    def eval_claims(ts):
        hit=[]
        for g in gold:
            found=[t for t in ts if t.r==g['r'] and norm(t.h) in g['ha'] and norm(t.t) in g['ta']]
            hit.append(found)
        return dict(gold_triples_found=sum(bool(x) for x in hit),
                    gold_triples_citation_overlap=sum(any(t.sentence_id in g['evidence'] for t in arr) for arr,g in zip(hit,gold)),
                    emitted=len(ts),exact_source_integrity=all(verify_triple(t,sents) for t in ts))
    for method,vals in objects.items():
        if 'mentions' in vals:
            ms=vals['mentions'];ps=vals['pairs'];ts=vals['triples']
            results[method]={**eval_mentions(ms),'mentions':len(ms),'proposed_pairs':len(ps),
                             'gold_pair_candidates':eval_pairs(ps),**eval_claims(ts)}
        else:
            results[method]={**eval_claims(vals['triples']),
                             'model_pairs':vals['model_pairs'],'model_ms':vals['model_ms'],
                             'preselected_candidates':vals['preselected_candidates']}
    return dict(id=idx,title=doc['title'],gold_count=len(gold),metrics=results,
                predictions=preds,gold_labels=[dict(h=x['h'],t=x['t'],r=x['r']) for x in gold])

def run(out,n=60,use_spacy=True,use_nli=True):
    docs,source_sha=load_docred();selection=select_docs(docs,n);out.mkdir(parents=True,exist_ok=True)
    nlp=None;nli=None;loaded={};start=time.perf_counter()
    if use_spacy:
        import spacy
        nlp=spacy.load('en_core_web_sm',disable=['textcat'])
        loaded['spacy_version']=spacy.__version__;loaded['pipeline_version']=nlp.meta.get('version')
    if use_nli:
        import torch
        from sentence_transformers import CrossEncoder
        torch.set_num_threads(2)
        nli=CrossEncoder(NLI_MODEL,device='cpu',revision=NLI_REV,max_length=256)
    loaded['model_load_s']=round(time.perf_counter()-start,3)
    records=[]
    for i,(idx,doc) in enumerate(selection):
        # ABSOLUTELY no call to doc['labels'] or doc['vertexSet'] until both models have proposed mentions and triples.
        sentences=doc['sents']
        regex=regex_mentions(sentences)
        spacy_m=spacy_mentions(sentences,nlp) if nlp else regex
        record=scored_doc(idx,doc,regex,spacy_m,nli=nli)
        records.append(record)
        if (i+1)%10==0:print('V88 DocRED source-first',i+1,'/',n,flush=True)
    names=sorted(records[0]['metrics']);summary={}
    for name in names:
        items=[r['metrics'][name] for r in records]
        fields=['gold_pair_both_entities_detected','gold_pair_candidates','gold_triples_found',
                'gold_triples_citation_overlap','emitted','mentions','proposed_pairs','model_pairs','model_ms']
        summary[name]={f:round(sum(x.get(f,0) for x in items),3) for f in fields if any(f in x for x in items)}
        summary[name]['source_invariant_all']=all(x.get('exact_source_integrity',True) for x in items)
    total=sum(r['gold_count'] for r in records)
    metrics=dict(version='V8.8',n_docs=n,n_gold_annotated_ontology_triples=total,
                 source_sha256=source_sha,
                 sample_ids_sha256=hashlib.sha256(','.join(str(r['id']) for r in records).encode()).hexdigest(),
                 excluded_v87_docs=len(EXCLUDE),model=loaded,methods=summary,
                 interpretation='Gold-positive recall only. Unlabeled outputs may be correct; no precision or official DocRED F1.',
                 scope='Document-level raw-text NER/cue triple proposals. No gold pair prompts. No open web, multi-hop answers or proof-gap retrieval yet.')
    (out/'summary.json').write_text(json.dumps(metrics,indent=2))
    with (out/'per_doc.jsonl').open('w') as f:
        for r in records:f.write(json.dumps(r)+'\n')
    print('V8.8 source-first benchmark COMPLETE',flush=True);print(json.dumps(metrics,indent=2),flush=True)
    return metrics

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['smoke','run'])
    p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('results-v88'))
    p.add_argument('--docs',type=int,default=60)
    p.add_argument('--no-spacy',action='store_true');p.add_argument('--no-nli',action='store_true')
    args=p.parse_args()
    if args.command=='smoke':
        from pger_v88_core import regex_mentions,relation_triples
        ss=['Kalank was directed by Abhishek Varman and produced by Karan Johar.']
        ts=relation_triples(regex_mentions(ss),ss)
        assert any(t.r=='P57' and t.t=='Abhishek Varman' for t in ts)
        print('V8.8 smoke PASS');return
    if args.docs!=60:raise ValueError('Frozen V8.8 run uses exactly 60 docs')
    run(args.out,n=args.docs,use_spacy=not args.no_spacy,use_nli=not args.no_nli)
if __name__=='__main__':main()