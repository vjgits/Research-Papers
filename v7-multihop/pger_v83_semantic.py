"""PGER V8.3: pretrained cross-encoder reranking and exact-sourced-edge ablation.

No labels, reference answers, or relevance judgements are read by this module.
A sourced link is not logical entailment. This is an experiment, not a novel
model or an end-to-end answer reader.
"""
import re
from pger_v72_core import terms
from pger_v8_core import EvidenceMap

FAST_N=32
RESCUE_N=32
PROTECT_N=2


def fixed_pools(question,fast,bm25,rescue,engine):
    """Candidate pools frozen before looking at gold. Rescue holds 16 fast
    anchors and selects 16 new candidates with inexpensive lexical signals.
    All cross-encoder variants share one scoring pass across their union.
    """
    f=list(dict.fromkeys(fast[:FAST_N]))
    preserve=list(dict.fromkeys(fast[:FAST_N//2]))
    qt=terms(question)
    bpos={x:p for p,x in enumerate(bm25)}
    fpos={x:p for p,x in enumerate(fast)}
    novel=set(rescue)-set(preserve)
    def score(i):
        doc=engine.docs[i]
        body=engine.doc_tokens[i]
        title=engine.title_tokens[i]
        return (len(qt&title)/max(1,len(title)) + 0.35*len(qt&body)/max(1,len(qt))
               + (0.12/(1+bpos[i]) if i in bpos else 0)
               + (0.06/(1+fpos[i]) if i in fpos else 0))
    ranked=sorted(novel,key=lambda i:(-score(i),engine.ids[i]))
    r=preserve + ranked[:max(0,RESCUE_N-len(preserve))]
    r=list(dict.fromkeys(r))
    if len(r)<RESCUE_N:
        r.extend(i for i in f if i not in set(r))
    return f,r[:RESCUE_N]


def make_passage(doc):
    return (str(doc['title'])+'\n'+str(doc.get('text') or '')[:1000]).strip()


def predict_union(question,fast_pool,rescue_pool,docs,predict):
    """Score union once to remove duplicated model work from ablations.
    `predict(pairs)` is an injected open-weight cross encoder or test double.
    """
    union=list(dict.fromkeys(fast_pool+rescue_pool))
    pairs=[(question,make_passage(docs[i])) for i in union]
    scores=predict(pairs)
    if len(scores)!=len(union):raise AssertionError('Cross encoder score length mismatch')
    return {i:float(v) for i,v in zip(union,scores)},len(pairs)


def rank_with_scores(fast,pool,scores,engine,mode='plain',limit=100):
    """Same scores/pool for plain vs protected vs sourced arms.
    SOURCE mode only bonuses an *observed directional cue with valid span*.
    Such an edge remains weak association evidence, NOT relation entailment.
    """
    assert mode in ('plain','protected','sourced')
    pool=list(dict.fromkeys(pool))
    if not set(pool)<=set(scores):raise AssertionError('Missing CE predictions')
    prefix=list(dict.fromkeys(fast[:PROTECT_N])) if mode!='plain' else []
    remaining=set(pool)-set(prefix)
    selected=list(prefix);edge_trail=[]
    while remaining:
        options=[]
        for i in remaining:
            val=scores[i]
            supporting=[]
            if mode=='sourced':
                for source in selected[:10]:
                    for c in engine.out.get(source,()):
                        if c.target==i and c.asserted and engine.claims.valid(c):
                            supporting.append(c)
                # Weak per-passage source mentions are never certified as truth.
                val+=0.08 if supporting else 0.
            options.append((val,i,supporting))
        options.sort(key=lambda x:(-x[0],engine.ids[x[1]]))
        _,best,links=options[0]
        selected.append(best);remaining.remove(best)
        if links:
            c=sorted(links,key=lambda c:(c.source_id,c.start,c.target_id))[0]
            edge_trail.append({'source_id':c.source_id,'target_id':c.target_id,
                               'predicate':c.predicate,'quote':c.quote,
                               'start':c.start,'end':c.end,'asserted':c.asserted})
    order=list(dict.fromkeys(selected+fast))[:limit]
    assert len(order)==len(set(order))
    return order,edge_trail


def cheap_gate(question,fast,engine):
    """Conservative query-only and source-only routing, no gold access.
    No answer sufficiency is inferred. Default to expensive if not obvious.
    """
    if not fast:return False
    qt=terms(question)
    words=question.casefold()
    if len(qt)>4:return False
    if any(t in words for t in ('earlier','later','older','younger','between','both','same','which of','whose')):
        return False
    coverage=len(qt&engine.doc_tokens[fast[0]])/max(1,len(qt))
    return coverage>=0.95