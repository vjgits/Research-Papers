"""V9.1: question-conditioned gap-query proxy, NOT a solved proof-gap controller.
All evidence sources tracked by exact quote/hash; surface wording is NOT entailment.
No benchmark labels, gold ids, or official IRCoT/HippoRAG outputs enter policy.
"""
import hashlib, re, math, time
from dataclasses import dataclass,asdict

# Frozen lexical relation phrase inventory, not pretrained semantic interpretation.
RELATIONS = (
    ('birth','born birthplace birth'),('death','died death'),
    ('director','directed director film'),('author','written author book'),
    ('location','located country city state district'),
    ('organization','founded founder headquarters company'),
    ('parent','father mother parent child son daughter'),
    ('date','year date earlier later before after'),
    ('music','album song musician singer'),('sports','team match coach winner'),
    ('school','university studied school educated'),
)
STOP={'which','what','who','whom','whose','when','where','does','was','were','the','has','had','did','that','this','and','for','into','from','with','of','are','its','is','it','a','an','in','on','to','by','or','than','would','have','has','not','person','thing','one','their','they','them'}
def toks(s):
    return set(w for w in re.findall(r"[a-z0-9]{3,}",str(s).lower()) if w not in STOP)

def gap_slots(question):
    q=toks(question)
    matches=[]
    for name,words in RELATIONS:
        hit=q & toks(words)
        if hit:matches.append((name,len(hit),tuple(sorted(hit))))
    matches.sort(key=lambda x:(-x[1],x[0]))
    return matches[:4] or [('unknown',0,tuple())]

def normalize_doc_text(doc):return str(doc.get('text') or '')

def valid_source(witness,docs):
    d=docs[witness['doc_index']]
    t=normalize_doc_text(d)
    quote=witness['quote']
    return bool(quote) and t[witness['start']:witness['end']]==quote and hashlib.sha256(quote.encode()).hexdigest()==witness['sha256']

def source_witness(docs,i,words):
    txt=normalize_doc_text(docs[i]); segments=re.split(r'(?<=[.!?])\s+',txt[:1300]);q=set(words)
    offset=0; cands=[]
    for seg in segments[:18]:
        off=txt.find(seg,offset)
        if off<0:continue
        offset=off+len(seg)
        if not seg.strip():continue
        value=len(toks(seg)&q)
        cands.append((value,-off,off,seg[:260]))
    if not cands:return None
    _,__,pos,quote=max(cands)
    result={'doc_index':i,'start':pos,'end':pos+len(quote),'quote':quote,'sha256':hashlib.sha256(quote.encode()).hexdigest()}
    assert valid_source(result,docs)
    return result

def plan_queries(question,fast,docs,policy='gap',calls=2):
    """Matched-budget gap and frontier query plans. No gold sources consulted.
    'gap' is a lexical *proxy* for counterfactual decision-changing facts, not
    verified proof of answer sensitivity.
    """
    assert policy in ('gap','frontier','original')
    if not fast: return []
    slots=gap_slots(question); queryterms=toks(question)
    scored=[]
    for rank,i in enumerate(fast[:12]):
        d=docs[i]; title=str(d.get('title') or '').strip()
        if len(title)<3:continue
        docwords=toks(normalize_doc_text(d)[:1300]);titlewords=toks(title)
        for sl,_,hits in slots[:3]:
            if policy=='frontier':
                # Standard frontier baseline: choose highest ranked seed/title and
                # repeat an entity-focused search with original-question keywords.
                utility=1/(rank+1)+.02*len(titlewords&queryterms)
                follow=f'{title} {" ".join(sorted(queryterms)[:7])}'
            elif policy=='original':
                utility=1/(rank+1);follow=question
            else:
                # A previously unseen relation word suggests a missing bridge.
                # This is only a *lexical* gap proxy; lower score if source already
                # contains relation terms, and reward different source entities.
                missing=set(hits)-docwords
                novel=len(missing)
                title_match=len(titlewords&queryterms)
                utility=1.5*novel+0.3*title_match+0.06/(rank+1)
                follow=f'{title} {" ".join(sorted(hits or list(queryterms)[:3]))}'
            scored.append((utility,-rank,sl,i,follow))
    scored.sort(key=lambda r:(-r[0],-r[1],r[2],str(docs[r[3]].get('title',''))))
    selected=[];seeds=set();queries=set()
    for utility,_,relation,i,query in scored:
        if len(selected)>=calls:break
        if i in seeds or query.lower() in queries:continue
        seeds.add(i);queries.add(query.lower())
        support=source_witness(docs,i,queryterms)
        selected.append(dict(relation=relation,seed_doc=i,query=query,priority=round(float(utility),5),witness=support))
    # Ensure same number of calls on full datasets; deterministic fallback.
    while len(selected)<calls:
        i=fast[len(selected)%len(fast)]
        query=question+(' '+' '.join(sorted(toks(str(docs[i].get('title',''))))[:3]) if policy!='original' else '')
        selected.append(dict(relation='fallback',seed_doc=i,query=query,priority=0.,witness=source_witness(docs,i,queryterms)))
    return selected

def fuse(fast,plans,hits,docs,k=100):
    """Shared RRF projection for all equal-budget arms; never consults gold."""
    assert len(plans)==len(hits)
    scores={}; seen=set();ranks=[]
    for rank,i in enumerate(fast):scores[i]=scores.get(i,0)+1.0/(60+rank+1);seen.add(i)
    for item in hits:
        for rank,i in enumerate(item):
            scores[i]=scores.get(i,0)+.65/(60+rank+1);seen.add(i)
    # Preserve first 2 fast anchors (pre-registered conservative fallback).
    anchors=list(dict.fromkeys(fast[:2]));out=anchors.copy()
    order=sorted(seen,key=lambda i:(-scores[i],str(docs[i].get('_id',i))))
    for i in order:
        if i not in out:out.append(i)
    return out[:k]

def query_once(question,bmraw,fast,docs,search,policy='gap',calls=2,cap=60):
    t=time.perf_counter()
    plan=plan_queries(question,fast,docs,policy,calls)
    hitsets=[]
    for p in plan:hitsets.append(search(p['query'],cap))
    ranked=fuse(fast,plan,hitsets,docs)
    return ranked,dict(policy=policy,actions=plan,extra_queries=len(plan),retrieved=[len(x) for x in hitsets],extra_ms=(time.perf_counter()-t)*1000)