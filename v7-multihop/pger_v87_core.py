"""V8.7 zero-shot ontology-constrained natural document relation probe.
Not end-to-end open relation extraction; given entities, no label leaked to inference.
Annotated DocRED relational evidence is scored POST prediction only.
"""
import re, math, hashlib
from dataclasses import dataclass

# Wikidata property identifiers in DocRED. Fixed before viewing evaluation docs.
TEMPLATES = {
 'P19':'{h} was born in {t}.',
 'P20':'{h} died in {t}.',
 'P27':'{h} is a citizen of {t}.',
 'P17':'{h} is located in the country {t}.',
 'P131':'{h} is located in {t}.',
 'P159':'{h} has its headquarters in {t}.',
 'P57':'{h} was directed by {t}.',
 'P50':'{h} was written by {t}.',
 'P26':'{h} is married to {t}.',
 'P36':'{h} has capital {t}.',
 'P108':'{h} works for {t}.',
 'P69':'{h} was educated at {t}.',
 'P40':'{h} has child {t}.',
 'P22':'{h} has father {t}.',
 'P25':'{h} has mother {t}.',
 'P161':'{h} has cast member {t}.',
}
# Weak lexical keywords are a comparator, NOT a factual claim extractor.
KEYWORDS={
 'P19':('born','birthplace'), 'P20':('died','death'), 'P27':('citizen','citizenship','nationality'),
 'P17':('country','nation'), 'P131':('located','district','municipality'),
 'P159':('headquarters','headquartered'), 'P57':('directed','director'),
 'P50':('author','written','wrote'), 'P26':('married','wife','husband','spouse'),
 'P36':('capital',), 'P108':('employed','employer','worked','works'),
 'P69':('educated','studied','university','attended'), 'P40':('child','children'),
 'P22':('father',), 'P25':('mother',), 'P161':('cast','starred','actor'),
}
WORDS=re.compile(r'\w+',re.UNICODE)
STOP=set('a the and to of in at on by for with was were is are has he she it this that whose who where which from'.split())

def tokenize(s):
    return {x for x in WORDS.findall(str(s).lower()) if len(x)>2 and x not in STOP}

def normalize_doc(row):
    """Hugging Face converted Parquet / original DocRED record compatibility."""
    sents=row.get('sents') or []
    if isinstance(sents,dict):
        sents=sents.get('feature',[])  # only if converter returns nested array feature
    sents=[' '.join(str(t) for t in s) if isinstance(s,(tuple,list)) else str(s) for s in sents]
    vertices=row.get('vertexSet') or []
    if isinstance(vertices,dict):
        raise ValueError('Unsupported vertexSet struct-of-arrays; inspect dataset format and adapt explicitly')
    verts=[]
    for group in vertices:
        if isinstance(group,dict):
            group=[group]
        entities=[]
        for m in group:
            if m is None:continue
            if not isinstance(m,dict):raise ValueError(f'Unexpected mention: {str(m)[:100]}')
            entities.append({'name':str(m.get('name','')),'sent_id':int(m.get('sent_id',-1)), 'type':str(m.get('type',''))})
        verts.append(entities)
    labels=row.get('labels') or []
    if isinstance(labels,dict):
        keys=('head','tail','relation_id','relation_text','evidence')
        n=len(labels.get('head') or [])
        labels=[dict(h=labels['head'][j],t=labels['tail'][j],r=labels['relation_id'][j],evidence=(labels.get('evidence') or [[]]*n)[j]) for j in range(n)]
    else:
        labels=[dict(h=x.get('h',x.get('head')),t=x.get('t',x.get('tail')),
                r=x.get('r',x.get('relation_id')),evidence=x.get('evidence') or []) for x in labels]
    return {'title':str(row.get('title','')),'sents':sents,'vertexSet':verts,'labels':labels}

def canonical_name(mentions):
    if not mentions:return ''
    counts={}
    for m in mentions:
        name=m['name'].strip()
        if name:counts[name]=counts.get(name,0)+1
    return sorted(counts,key=lambda s:(-counts[s],-len(s),s.lower()))[0] if counts else ''

def evidence_windows(doc,h,t,limit=4):
    """All selection based on ONLY query entities and document mentions; no gold evidence labels."""
    sents=doc['sents'];vs=doc['vertexSet']
    H=canonical_name(vs[h]);T=canonical_name(vs[t]);anchorsH={m['sent_id'] for m in vs[h]};anchorsT={m['sent_id'] for m in vs[t]}
    ht=tokenize(H)|tokenize(T)
    scores=[]
    for i,s in enumerate(sents):
        st=tokenize(s)
        points=2.0*int(i in anchorsH)+2.0*int(i in anchorsT)+0.17*len(ht&st)
        if i in anchorsH and i in anchorsT:points+=3.0
        scores.append((points,i))
    scores.sort(key=lambda z:(-z[0],z[1]))
    indices=[i for _,i in scores[:limit]]
    # A single window always carries its exact sentence IDs; no implicit invented citation.
    return [{'sentence_ids':[i],'premise':sents[i], 'source_hash':hashlib.sha256(sents[i].encode()).hexdigest()} for i in indices]

def hypotheses(h,t):
    return {rel:template.format(h=h,t=t) for rel,template in TEMPLATES.items()}

def lexical_baseline(windows):
    text=' '.join(w['premise'].lower() for w in windows)
    scores={r:sum(int(bool(re.search(r'\b'+re.escape(w)+r'\b',text))) for w in kws) for r,kws in KEYWORDS.items()}
    best=sorted(scores,key=lambda r:(-scores[r],r))[0]
    return best if scores[best]>0 else None

def predict_nli(logits,windows,threshold=.70,margin=.10):
    """logits has (relation,window_index,3 logits). Label order C,E,N pinned in V8.6."""
    byrel={r:(-1.,None,None) for r in TEMPLATES}
    for rel,j,raw in logits:
        if len(raw)!=3:raise ValueError('NLI label cardinality must be 3')
        x=[float(y) for y in raw];mx=max(x);v=[math.exp(z-mx) for z in x];v=[z/sum(v) for z in v]
        if v[1]>byrel[rel][0]:byrel[rel]=(v[1],int(j),v)
    ranked=sorted(byrel,key=lambda r:(-byrel[r][0],r))
    best=ranked[0];p,j,probs=byrel[best]
    assert j is not None
    # Conservative one-label abstain: do not infer absent labels as contradictions.
    accept=bool(p>=threshold and p-max(probs[0],probs[2])>=margin)
    selected=windows[j]
    return {'predicted':best if accept else None,'ungated':best,'confidence':p,
            'window':selected,'ranked':ranked, 'probs':probs}

def evaluate_one(doc,h,t,nli_predict,cap=4):
    hname=canonical_name(doc['vertexSet'][h]);tname=canonical_name(doc['vertexSet'][t])
    windows=evidence_windows(doc,h,t,cap);hyps=hypotheses(hname,tname)
    # Model budget is identical for all relation choices: K relations x cap windows.
    pairs=[(w['premise'],hyps[r]) for r in TEMPLATES for w in windows]
    result=nli_predict(pairs)
    if len(result)!=len(pairs):raise ValueError('NLI output mismatch')
    logits=[(r,j,result[ir*len(windows)+j]) for ir,r in enumerate(TEMPLATES) for j in range(len(windows))]
    pred=predict_nli(logits,windows)
    pred['lexical']=lexical_baseline(windows)
    pred['pair_count']=len(pairs)
    pred['candidate_sentence_ids']=[w['sentence_ids'][0] for w in windows]
    if pred['window']['premise'] != doc['sents'][pred['window']['sentence_ids'][0]]:raise AssertionError('Span provenance invariant')
    return pred

def bridge_windows(doc,h,t,cap=4):
    """Same number of NLI calls; each premise may include an additional anchor sentence.
    Exact document sentence IDs retained. Does NOT read gold evidence sentence IDs.
    """
    windows=evidence_windows(doc,h,t,cap)
    H={m['sent_id'] for m in doc['vertexSet'][h]};T={m['sent_id'] for m in doc['vertexSet'][t]}
    out=[]
    for w in windows:
        primary=w['sentence_ids'][0];cands=[]
        if primary in H and primary not in T:cands=sorted(T,key=lambda x:(abs(x-primary),x))
        elif primary in T and primary not in H:cands=sorted(H,key=lambda x:(abs(x-primary),x))
        elif primary not in T and primary not in H:cands=sorted(H|T,key=lambda x:(abs(x-primary),x))
        partner=next((s for s in cands if 0<=s<len(doc['sents']) and s!=primary),None)
        ids=sorted({primary,partner} if partner is not None else {primary})
        premise=' '.join(doc['sents'][s] for s in ids)
        out.append(dict(sentence_ids=ids,premise=premise,source_hash=hashlib.sha256(premise.encode()).hexdigest()))
    return out

def evaluate_windows(doc,h,t,nli_predict,windows):
    hname=canonical_name(doc['vertexSet'][h]);tname=canonical_name(doc['vertexSet'][t]); hyps=hypotheses(hname,tname)
    pairs=[(w['premise'],hyps[r]) for r in TEMPLATES for w in windows]
    result=nli_predict(pairs)
    if len(result)!=len(pairs):raise ValueError('NLI output mismatch')
    logits=[(r,j,result[ir*len(windows)+j]) for ir,r in enumerate(TEMPLATES) for j in range(len(windows))]
    pred=predict_nli(logits,windows);pred.update(lexical=lexical_baseline(windows),pair_count=len(pairs),candidate_sentence_ids=sorted({i for w in windows for i in w['sentence_ids']}))
    selected=pred['window']
    assert selected['premise']==' '.join(doc['sents'][s] for s in selected['sentence_ids'])
    return pred