"""PGER V8.4: bounded diverse retrieval and conditional, protected semantic reranking.
No labels or dataset-specific method names; no novel primitive or fact entailment claim.
"""
import collections, re
import numpy as np

POOL_CAP=192
CE_CAP=64
PROTECT=2

def stable_union(*groups):
    return list(dict.fromkeys(j for group in groups for j in group))

def full_pool(fast, bm, dense, tfidf, followups, graph_reverse, doc_ids, cap=POOL_CAP):
    """Preserve 80 fast-ranked candidates, fill via RRF of independent channels.
    Important: rank-stage output is not the entire candidate pool.
    """
    first=stable_union(fast[:80])[:cap]
    allchannels=[fast[:100],bm[:100],dense[:120],tfidf[:120],followups[:150],graph_reverse[:150]]
    w=[1.0,1.0,1.2,0.8,0.9,0.9]
    scores=collections.defaultdict(float)
    for weight,group in zip(w,allchannels):
        for rank,j in enumerate(dict.fromkeys(group)):
            scores[j]+=weight/(40+rank+1)
    extras=sorted(set(scores)-set(first),key=lambda i:(-scores[i],doc_ids[i]))
    return stable_union(first,extras[:max(0,cap-len(first))]),scores

def short_rerank_pool(fast, wide, rrf_scores, docs, q, cap=CE_CAP, protect=PROTECT):
    """Low-cost shortlist. Preserve two known-high-ranking anchors, diversify by RRF.
    This is *not* an oracle and not a statement of factual evidence sufficiency.
    """
    prefix=stable_union(fast[:protect]); qtokens=set(re.findall(r'[a-z0-9]+',q.lower()))
    fpos={j:p for p,j in enumerate(fast)}
    def sc(i):
        title=set(re.findall(r'[a-z0-9]+',docs[i]['title'].lower()))
        return rrf_scores.get(i,0.)+0.005*len(title&qtokens)/max(1,len(title))+(0.006/(1+fpos[i]) if i in fpos else 0.)
    ordered=sorted(set(wide)-set(prefix),key=lambda i:(-sc(i),str(docs[i]['_id'])))
    return stable_union(prefix,ordered)[:cap]

def sorted_ce(fast,pool,scores,doc_ids,protect=PROTECT):
    prefix=stable_union(fast[:protect])
    tail=sorted(set(pool)-set(prefix),key=lambda i:(-float(scores[i]),doc_ids[i]))
    return stable_union(prefix,tail,fast)[:100]

def directional_bonus_rank(fast,pool,scores,engine,protect=PROTECT):
    """Compare same CE scores with/without exact-span observed directional edge.
    It is a surface relation cue, NOT entailment or contradiction verification.
    """
    prefix=stable_union(fast[:protect]);left=set(pool)-set(prefix);chosen=list(prefix);traces=[]
    while left:
        scored=[]
        for i in left:
            edges=[]
            for source in chosen[:10]:
                edges.extend(c for c in engine.out.get(source,()) if c.target==i and c.asserted and engine.claims.valid(c))
            scored.append((float(scores[i])+(0.08 if edges else 0.),i,edges))
        scored.sort(key=lambda a:(-a[0],engine.ids[a[1]]))
        _,j,e=scored[0];chosen.append(j);left.remove(j)
        if e:
            c=e[0];traces.append({'source_id':c.source_id,'target_id':c.target_id,'quote':c.quote,
                                    'start':c.start,'end':c.end,'asserted':c.asserted})
    return stable_union(chosen,fast)[:100],traces

def corpus_gate(question, fast, engine, graph_density):
    """Predeclared corpus structural routing (NOT universal query-level intelligence).
    Sparse title-mention corpora favor cheap indexed fast method in past diagnostics.
    """
    if graph_density<0.65:return 'fast'
    words=set(re.findall(r'[a-z0-9]+',question.casefold()))
    hard=set('whose earlier later older younger between both same compared comparison originally inspired'.split())
    if len(words)<=5 and not words&hard and fast:
        titlewords=set(re.findall(r'[a-z0-9]+',engine.docs[fast[0]]['title'].casefold()))
        if len(titlewords&words)>=2:return 'fast'
    return 'ce'

def context_rows(raw):
    """Normalize HF Sequence-of-struct representation of verified MoreHopQA.
    Gold titles only for PREVIOUS-question contexts; added last-hop evidence may be absent.
    """
    ctx=raw.get('context') or {};dec=raw.get('question_decomposition') or {}
    if isinstance(ctx,dict):
        titles=ctx.get('title') or []
        bodies=ctx.get('paragraphs') or []
    elif isinstance(ctx,list):
        titles=[x.get('title') for x in ctx]
        bodies=[x.get('paragraphs') for x in ctx]
    else:return [],set()
    pars=[]
    for title,body in zip(titles,bodies):
        if not title:continue
        if isinstance(body,list):body=' '.join(str(x) for x in body)
        pars.append((str(title),str(body or '')))
    if isinstance(dec,dict):
        support=dec.get('paragraph_support_title') or []
    else:support=[x.get('paragraph_support_title') for x in dec if isinstance(x,dict)]
    gold={str(t).strip().casefold() for t in support if t and str(t).strip().casefold() in {x[0].casefold() for x in pars}}
    return pars,gold