"""V8.5 source-offset-validated chain-aware reranking, research-only.

All retrieval components, beam search, rerank and constraints are standard methods.
No natural-language entailment is claimed: verified offsets only show a mention.
No labels, ground-truth IDs, answers, or relevance judgements enter these methods.
"""
from collections import defaultdict
import re
import math
from pger_v84_core import stable_union

PROTECT=2
TOKEN=re.compile(r"[a-z0-9]+")
COMPARATIVE=frozenset('earlier later older younger compared comparison between both same which whose before after first last'.split())

def words(s):return set(TOKEN.findall(str(s).casefold()))

def deterministic_shortlist(fast,wide,rrf,docs,question,n):
    """Same fixed RRF ordering for all 32/64/96 CE budget arms."""
    assert n in (32,64,96)
    prefix=stable_union(fast[:PROTECT])
    qt=words(question);fpos={i:p for p,i in enumerate(fast)}
    def s(i):
        title=words(docs[i]['title'])
        return (float(rrf.get(i,0.))
                +0.005*len(title&qt)/max(1,len(title))
                + (0.006/(1+fpos[i]) if i in fpos else 0.))
    sorted_ids=sorted(set(wide)-set(prefix),key=lambda i:(-s(i),str(docs[i]['_id'])))
    return stable_union(prefix,sorted_ids)[:n]

def ce_plain(fast,pool,scores,ids,limit=100):
    """Protected CE, one common inference scoremap and deterministic tie-breaks."""
    if not set(pool)<=set(scores):raise AssertionError('missing CE score')
    prefix=stable_union(fast[:PROTECT])
    return stable_union(prefix,sorted(set(pool)-set(prefix),key=lambda i:(-scores[i],ids[i])),fast)[:limit]

def graph_evidence(pool,evidence):
    """Only valid exact source-spans. Returns observed edges, not entailed triples."""
    allowed=set(pool);out=defaultdict(list)
    for source in allowed:
        for c in evidence.out.get(source,()):
            if c.target in allowed and source!=c.target and evidence.claims.valid(c):
                out[source].append(c)
    return out

def connected_beam(fast,pool,scores,ids,docs,evidence,question,beam=8,width=5,limit=100):
    """Select source portfolio with globally connected evidence candidates.

    Maximize a *heuristic* sum: calibrated CE passage relevance, potential
    source-link connectivity and coverage of question operators. Valid source
    offsets required for all link rewards. This does not infer actual proof.
    No gold/answers, source entailment, or unproven facts are introduced.
    Input CE scores/candidates are IDENTICAL to ce_plain(..., 96).
    """
    if not set(pool)<=set(scores):raise AssertionError('missing CE score')
    prefix=stable_union(fast[:PROTECT]);original=set(prefix)
    allowed=set(pool)-original
    if not allowed:return stable_union(prefix,fast)[:limit],[]
    qt=words(question)
    edges=graph_evidence(pool,evidence)
    # Pairs may be linked in either direction; this is an observed reference
    # not a verified relationship. Only directional cues qualify for bonus.
    by_pair=defaultdict(list)
    for src,claims in edges.items():
        for c in claims:by_pair[frozenset((src,c.target))].append(c)
    def linkweight(i,j):
        claims=by_pair.get(frozenset((i,j)),())
        # Weak association never rewarded; orientation/cue still not entailment.
        return (0.12 if any(c.asserted for c in claims) else 0.)
    def value(seq):
        v=0.;covered=set();seen=set()
        for r,i in enumerate(seq):
            v+=float(scores.get(i,0.))
            ti=words(docs[i]['title'])&qt
            v+=0.028*len(ti-covered)
            covered.update(ti)
            # directional edges to any prior support, marginal not repeated.
            for j in seen:
                v+=linkweight(i,j)
            seen.add(i)
        return v
    # Efficient beam over top-24 CE candidates and their strong neighbors;
    # after portfolio selection, append all remaining passages by CE order.
    order=sorted(allowed,key=lambda i:(-float(scores[i]),ids[i]))
    candidates=set(order[:24]);
    for c in edges.values():
        for edge in c:
            if edge.asserted and edge.target in allowed and edge.source in candidates:
                candidates.add(edge.target)
    candidates=sorted(candidates,key=lambda i:(-scores[i],ids[i]))[:48]
    states=[tuple(prefix)]
    for _ in range(width):
        proposed=[]
        for seq in states:
            for i in candidates:
                if i in seq:continue
                proposal=seq+(i,)
                proposed.append((value(proposal),proposal))
        if not proposed:break
        proposed.sort(key=lambda a:(-a[0],tuple(ids[i] for i in a[1])))
        states=[s for _,s in proposed[:beam]]
    chosen=max(states,key=lambda s:(value(s),tuple(-ord(c) for i in s for c in ids[i][:2])))
    # Return 5 candidate-related items *after* protected anchors, not only a
    # five-source chain: complete@5 may degrade if selected 5 are wrong.
    ranked=stable_union(chosen,order,fast)[:limit]
    traces=[]
    for b,i in enumerate(chosen):
        for j in chosen[:b]:
            links=by_pair.get(frozenset((i,j)),())
            good=sorted((c for c in links if c.asserted),key=lambda c:(c.source_id,c.start,c.target_id))
            if good:
                c=good[0]
                traces.append(dict(source_id=c.source_id,target_id=c.target_id,
                        predicate=c.predicate,exact_quote=c.quote,start=c.start,end=c.end,
                        heuristic_only=True))
    return ranked,traces

def early_gate(question,fast,docs,bm_scores=None):
    """Only an explicitly conservative trivial-lookup gate; no corpus ID.
    Executes before dense/index query encoding, followups and cross-encoder.
    This checks query form, NEVER pretends evidence is fully proved.
    """
    if not fast:return False
    tok=words(question)
    if len(tok)>7 or tok&COMPARATIVE:return False
    text=question.casefold()
    if sum(text.count(x) for x in (' who ',' whose ',' that ',' which ',' where ',' when ',' after ',' before '))>1:
        return False
    title=words(docs[fast[0]].get('title',''))
    # Non-comparative short direct title lookup; plausible fast routing only.
    return len(title & tok)>=2 and len(title & tok)/max(1,len(title))>=0.65