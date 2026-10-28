"""V8.6 typed source-clause + open-weight NLI gate. Experimental, NOT truth proof.
No gold/answer labels enter retrieval. Provenance validates quote bytes only.
"""
from dataclasses import dataclass
import math
import re

RELATIONS = {
    'directed_by': 'was directed by', 'produced_by':'was produced by',
    'written_by':'was written by', 'born_in':'was born in',
    'died_in':'died in', 'located_in':'is located in',
    'founded_in':'was founded in', 'part_of':'is part of',
    'capital_of':'is the capital of', 'married_to':'is married to',
}
# A lexical clause break helps discriminate "directed by A and produced by B".
CUE_PATTERN=re.compile(r'\b(?:was\s+)?(?:directed|produced|written|born|died|located|founded|married)\s+(?:in|by|to)|\b(?:is|was)\s+(?:the\s+capital\s+of|part\s+of)',re.I)
NEGATION=re.compile(r'\b(?:not|never|neither|incorrectly|rumou?red|allegedly|reportedly|denied)\b',re.I)

@dataclass(frozen=True)
class Judgement:
    supported:bool
    p_entail:float
    p_contradict:float
    p_neutral:float
    label:str
    source_id:str
    target_id:str
    predicate:str
    span_start:int
    span_end:int

def lexical_scope(c):
    """Reject co-mention, cue leakage, explicit negation and wrong predicate scope.
    Does not establish identity, disambiguate passive voices or verify truth.
    """
    if not c.asserted or c.predicate not in RELATIONS:return False
    quote=c.quote.casefold(); subj=c.subject.casefold(); obj=c.object.casefold()
    subj_pos=quote.find(subj);obj_pos=quote.find(obj)
    if subj_pos<0 or obj_pos<0 or subj_pos>obj_pos:return False
    matches=list(CUE_PATTERN.finditer(quote))
    if not matches:return False
    preceding=[(i,m) for i,m in enumerate(matches) if m.end()<=obj_pos]
    if not preceding:return False
    i,cue=preceding[-1]
    expected=c.predicate
    # Specific predicate mapping; reject wrong cue even when the target appears later.
    x=cue.group().casefold()
    if expected=='directed_by':valid='directed' in x and 'by' in x
    elif expected=='produced_by':valid='produced' in x and 'by' in x
    elif expected=='written_by':valid='written' in x and 'by' in x
    elif expected=='born_in':valid='born' in x and 'in' in x
    elif expected=='died_in':valid='died' in x and 'in' in x
    elif expected=='located_in':valid='located' in x and 'in' in x
    elif expected=='founded_in':valid='founded' in x and 'in' in x
    elif expected=='married_to':valid='married' in x and 'to' in x
    elif expected=='capital_of':valid='capital of' in x
    else:valid='part of' in x
    if not valid:return False
    # Refuse negated or uncertain local clauses. Conjunction / name alignment remains heuristic.
    preceding_text=quote[max(subj_pos,cue.start()-36):cue.start()]
    clause=quote[cue.start():obj_pos]
    if NEGATION.search(preceding_text) or NEGATION.search(clause):return False
    return True

def hypothesis(c):
    """Explicit typed hypothesis; never infers a relationship absent from source.
    """
    verb=RELATIONS.get(c.predicate)
    return f'{c.subject} {verb} {c.object}.' if verb else None

def logits_to_probs(logits):
    if len(logits)!=3:raise ValueError('NLI must output contradiction, entailment, neutral logits')
    x=[float(t) for t in logits]
    norm=max(x); ex=[math.exp(t-norm) for t in x]; den=sum(ex)
    return [v/den for v in ex]

def classify_nli(logits,threshold=.70,margin=.10):
    probs=logits_to_probs(logits)
    # class 0=contradiction, 1=entailment, 2=neutral, official model label order
    supported=probs[1]>=threshold and (probs[1]-max(probs[0],probs[2]))>=margin
    labels=('contradiction','entailment','neutral')
    return supported,labels[max(range(3),key=lambda i:probs[i])],probs

def query_predicates(q):
    q=q.casefold()
    tags=set()
    for k,terms in {
       'directed_by':('directed','director'), 'produced_by':('produced','producer'),
       'written_by':('author','writer','written','wrote'), 'born_in':('born','birth','birthplace'),
       'died_in':('died','death'), 'located_in':('located','district','city','state','country'),
       'founded_in':('founded','foundation'), 'capital_of':('capital',),
       'married_to':('married','spouse')}.items():
        if any(re.search(r'\b'+re.escape(t)+r'\b',q) for t in terms):tags.add(k)
    return tags

def candidate_claims(evidence,pool,fast,question,cap=32):
    """Propose claims with valid spans only, sorted deterministically.
    Identical candidate claims are used for typed-only and typed+NLI scoring.
    """
    accepted=set(pool); seeds=set(fast[:12]); preds=query_predicates(question)
    edges=[]
    for src in sorted(accepted):
        for c in evidence.out.get(src,()):
            if (src in seeds or c.target in seeds) and c.target in accepted and c.asserted and evidence.claims.valid(c):
                edges.append(c)
    edges.sort(key=lambda c:(-int(c.predicate in preds),c.source_id,c.target_id,c.start,c.end))
    return edges[:cap]

def score_claims(claims,nli_predict,require_nli):
    """Returns accepted (source_idx,target_idx,predicate) and complete scored traces.
    Predict callback invoked once per query, only for typed-in-scope candidates.
    """
    selected=[c for c in claims if lexical_scope(c)]
    logits=nli_predict([(c.quote,hypothesis(c)) for c in selected]) if require_nli and selected else []
    if len(logits)!=len(selected):raise AssertionError('NLI scoring mismatch')
    observations=[];accepted=[]
    for i,c in enumerate(claims):
        typed=lexical_scope(c);usable=typed
        prob=None;label='not_run'
        if require_nli and typed:
            j=selected.index(c)
            usable,label,prob=classify_nli(logits[j])
        if usable:accepted.append((c.source,c.target,c.predicate))
        observations.append({'source_id':c.source_id,'target_id':c.target_id,
            'predicate':c.predicate,'quote':c.quote,'start':c.start,'end':c.end,
            'typed_scope':typed,'accepted':usable,'nli_label':label,
            'nli_probabilities':prob})
    return accepted,observations

def rerank(fast,pool,scores,ids,accepted_edges,limit=100,bonus=.08):
    """Same CE96 pool/scores and first two protected anchors for all ablations.
    Bonus only when the selected source and a candidate form a typed accepted edge.
    """
    prefix=list(dict.fromkeys(fast[:2]));todo=set(pool)-set(prefix)
    output=list(prefix);good=set(accepted_edges)
    while todo:
        scored=[]
        for d in todo:
            supported=any((p,d,k) in good for p in output[:10] for k in RELATIONS)
            scored.append((float(scores[d])+(bonus if supported else 0.0),d))
        scored.sort(key=lambda a:(-a[0],ids[a[1]]))
        chosen=scored[0][1];output.append(chosen);todo.remove(chosen)
    output.extend(d for d in fast if d not in set(output))
    return output[:limit]