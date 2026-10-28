"""PGER V8 research prototype: zero API evidence candidate rescue and proof-aware ranking.

V7.3 = target missing candidates; V8.0 = joint selection; V8.1 = sourced
multi-step dependencies and discriminating source selection; V8.2 = cheap
routing.  All operations are heuristics, not natural-language entailment.  No
benchmark labels enter this module.  Measured novelty and accuracy not assumed.
"""
from collections import defaultdict, Counter, deque
from dataclasses import dataclass
import math, re, time
from pger_v72_core import ClaimIndex, terms, STOP, CUES

WORD=re.compile(r"[\w]+",re.UNICODE)
RELATIONS={
 'birth':('born','birth','birthplace','young','older','earlier','later'),
 'death':('died','death','dead','earlier','later'),
 'director':('directed','director','film','movie'),
 'author':('wrote','written','author','book','novel'),
 'location':('located','district','country','city','state','capital','place'),
 'family':('parent','son','daughter','brother','sister','spouse','married'),
}

def qfeatures(question):
    qt=terms(question)
    concepts={name for name,v in RELATIONS.items() if set(v)&qt}
    return qt,concepts

@dataclass(frozen=True)
class Dependency:
    source_id:str
    target_id:str
    relation:str
    exact_quote:str
    start:int
    end:int
    parent_edge:int|None
    asserted:bool

class EvidenceMap:
    """Indexed source-mentioned title links and their reverse edges (offline)."""
    def __init__(self,docs,claim_index=None):
        t=time.perf_counter()
        self.docs=docs
        self.claims=claim_index or ClaimIndex(docs)
        self.out=defaultdict(list); self.rev=defaultdict(list)
        self.doc_tokens=[terms(d['title']+' '+d.get('text','')) for d in docs]
        self.title_tokens=[terms(d['title']) for d in docs]
        self.ids=[str(d['_id']) for d in docs]
        for c in self.claims.claims:
            if not self.claims.valid(c):raise AssertionError('provenance mismatch')
            self.out[c.source].append(c)
            self.rev[c.target].append(c)
        self.build_seconds=time.perf_counter()-t

    def nearby(self,docs,limit=160):
        """Offline source graph expansions; no read of relevance labels."""
        found=set(docs)
        for i in docs[:12]:
            found.update(c.target for c in self.out.get(i,()))
            found.update(c.source for c in self.rev.get(i,()))
        return found

    def chain(self,seed,candidates,max_edges=8,beam=16):
        """Follow sourced mentions for up to 8 steps, avoid cycles/candidate leakage.
        Outputs dependency objects, not logical truth or final answers.
        """
        allowed=set(candidates)
        frontier=[(seed,(),frozenset([seed]))]
        result=[]
        for _ in range(max_edges):
            nxt=[]
            for node,trail,seen in frontier:
                for c in self.out.get(node,()):
                    if c.target not in allowed or c.target in seen:continue
                    d=Dependency(c.source_id,c.target_id,c.predicate,c.quote,c.start,c.end,
                                 len(trail)-1 if trail else None,c.asserted)
                    nt=trail+(d,)
                    result.append(nt);nxt.append((c.target,nt,seen|{c.target}))
            if not nxt:break
            nxt.sort(key=lambda r:(-sum(d.asserted for d in r[1]),-len(r[1]),r[0]))
            frontier=nxt[:beam]
        return result

    def source_valid(self,dep):
        index={d['_id']:i for i,d in enumerate(self.docs)}
        i=index.get(dep.source_id)
        return i is not None and self.docs[i]['text'][dep.start:dep.end]==dep.exact_quote


def missing_terms(question,doc_tokens,seed_ids):
    qt,_=qfeatures(question)
    observed=set()
    for i in seed_ids[:3]:observed.update(doc_tokens[i])
    return sorted(qt-observed)


def build_candidate_rescue(question,base,bm25,engine,search,budget=2,limit=100):
    """At most two BM25 followups. Offline reverse edges cost no query calls.

    Generate different search requests from *unresolved question tokens* and
    source-visible named titles, not a new query from the gold answers. Return
    common pool used by all V8 ranking ablations.
    """
    start=time.perf_counter()
    qt,concepts=qfeatures(question)
    pool=set(base[:min(limit,80)])|set(bm25[:min(limit,80)])
    graph=engine.nearby(base[:12],limit)
    pool.update(graph)
    targets=[]
    for i in base[:12]:
        if i not in pool:continue
        # Titles of documents *referenced in a source* are potential missing
        # intermediate entities even when those words are absent in the question.
        for c in engine.out.get(i,()):
            if c.target not in pool:pool.add(c.target)
            overlap=len(engine.doc_tokens[c.target]&qt)
            pri=(2 if c.asserted else 0)+overlap+len(engine.title_tokens[c.target]&qt)
            targets.append((pri,c.target,i))
    targets.sort(key=lambda x:(-x[0],engine.ids[x[1]]))
    gaps=missing_terms(question,engine.doc_tokens,base)
    options=[]
    for _,dst,src in targets[:8]:
        title=engine.docs[dst]['title']
        query=' '.join([title]+gaps[:5])
        options.append(('edge',query,src))
    # Original title anchors can be needed when the graph is sparse.
    for i in bm25[:5]:
        q=' '.join([engine.docs[i]['title']]+gaps[:7])
        options.append(('anchor',q,i))
    # Cross-hop query: relation vocab + missing question terms, not a title
    # walk, helpful on paragraphs without exact linked page titles.
    relation_terms=[w for k in sorted(concepts) for w in RELATIONS[k][:2]]
    options.append(('gap',' '.join((gaps+relation_terms)[:12]) or question,bm25[0] if bm25 else -1))
    # A neutral lexical control always performs as many searches as rescue.
    chosen=[];seen_queries=set()
    for tag,q,anchor in options:
        q=q.strip()
        if not q or q.casefold() in seen_queries:continue
        seen_queries.add(q.casefold());chosen.append((tag,q,anchor))
        if len(chosen)>=budget:break
    while len(chosen)<budget:
        # Reusing a real query is allowed; duplicate BM25 calls are billed to
        # both baseline controls, avoiding inflated 'equal-cost' claims.
        chosen.append(('fallback',question,bm25[0] if bm25 else -1))
    logs=[]
    for tag,q,anchor in chosen:
        ids=search(q,limit)
        pool.update(ids)
        logs.append({'type':tag,'query':q,'anchor':engine.ids[anchor] if anchor>=0 else None,
                     'returned':len(ids)})
    # Defensive hard cap: preserve all baseline documents first, then selected
    # candidate ordering only using observable query/source signals.
    if len(pool)>320:
        keep=set(base[:80])|set(bm25[:80])
        rest=sorted(pool-keep,key=lambda i:(-len(qt&engine.doc_tokens[i]),engine.ids[i]))
        pool=keep|set(rest[:max(0,320-len(keep))])
    return pool,logs,(time.perf_counter()-start)*1000


def rank_candidates(question,base,bm25,engine,pool,mode='rescue',top=100):
    """Modes V7.3 rescue, V8.0 joint, V8.1 proofgap.

    All modes have SAME exact candidate pool and query calls. Counterfactual
    target is operationalized as an uncovered question relation + distinct
    source path. It is NOT causal inference / semantic entailment.
    """
    assert mode in ('rescue','joint','proofgap')
    start=time.perf_counter()
    qt,concepts=qfeatures(question)
    bpos={d:k for k,d in enumerate(bm25)};fpos={d:k for k,d in enumerate(base)}
    def rankfit(i):
        return 1.0/(1+bpos[i]) if i in bpos else 0.
    evidence=[]
    for i in pool:
        hits=len(qt&engine.doc_tokens[i])/max(1,len(qt))
        title_hits=len(qt&engine.title_tokens[i])/max(1,len(engine.title_tokens[i]))
        relevance=0.50*hits+0.45*rankfit(i)+0.08*title_hits
        if i in fpos:relevance+=0.10/(1+fpos[i])
        evidence.append((relevance,i))
    evidence.sort(key=lambda x:(-x[0],engine.ids[x[1]]))
    if mode=='rescue':
        order=[i for _,i in evidence]
        return order[:top],{'mode':mode,'scoring_ms':(time.perf_counter()-start)*1000,
                             'dependency_edges':[]}

    candidates=[i for _,i in evidence[:100]]
    scores={i:sc for sc,i in evidence}
    selected=[];left=set(candidates);covered=set();link_count=0;dependencies=[]
    # Explicit coherent-source score, not naive concatenation of high BM25 hits.
    # Reserve a strong source anchor; investigate all subsequent candidates.
    if base and base[0] in left:
        selected.append(base[0]);left.remove(base[0]);covered.update(engine.doc_tokens[base[0]]&qt)
    while left and len(selected)<min(12,len(candidates)):
        choices=[]
        for i in left:
            uncovered=len((engine.doc_tokens[i]&qt)-covered)/max(1,len(qt))
            # Observed edges are cheap; weak 'association' cannot be a fact.
            support=[]
            for src in selected:
                support.extend(c for c in engine.out.get(src,()) if c.target==i)
                support.extend(c for c in engine.out.get(i,()) if c.target==src)
            strong=max((int(c.asserted) for c in support),default=0)
            edge=bool(support)
            value=scores[i]+0.19*uncovered+0.20*edge+0.10*strong
            if mode=='proofgap':
                # Question-concept discrimination. Bonus only for a concrete
                # source quote connecting a selected source to a new candidate.
                # A relation keyword is only a heuristic; we do not certify
                # actual answer-changing semantics.
                rel=set(w for c in support for w in c.predicate.split('_'))
                qrel=len(rel&qt)>0
                value+=0.16*int(qrel)+0.10*edge*(1-uncovered)
                # Avoid pursuing a known dependency twice.
                if support and any(d.target_id==engine.ids[i] for d in dependencies):value-=0.15
            choices.append((value,i,support))
        choices.sort(key=lambda x:(-x[0],engine.ids[x[1]]))
        _,picked,spans=choices[0]
        left.remove(picked);selected.append(picked);covered.update(qt&engine.doc_tokens[picked])
        if spans:
            c=next((x for x in spans if x.asserted),spans[0]);link_count+=1
            dependencies.append(Dependency(c.source_id,c.target_id,c.predicate,c.quote,
                c.start,c.end,len(dependencies)-1 if dependencies else None,c.asserted))
    rest=[i for i in candidates if i not in set(selected)]
    order=selected+rest
    # preserve tail fallback to all initial BM25/graph candidates
    used=set(order)
    order.extend(i for i in base if i not in used and not used.add(i))
    used=set(order)
    order.extend(i for i in bm25 if i not in used and not used.add(i))
    order=order[:top]
    assert len(order)==len(set(order))
    assert all(engine.source_valid(d) for d in dependencies)
    return order,{'mode':mode,'scoring_ms':(time.perf_counter()-start)*1000,
                  'dependency_edges':[vars(d) for d in dependencies],
                  'relation_count':link_count}


def route_cost(question,base,engine):
    """Conservative cheap path for short unambiguous queries.
    Complex comparative/relative questions remain on expensive retrieval.
    """
    qt,concepts=qfeatures(question)
    if not base or len(qt)>6:return 'investigate'
    if any(w in qt for w in ('earlier','later','older','younger','compare','both','same')):
        return 'investigate'
    q=question.casefold()
    if q.count(' who ')>1 or q.count(' that ')>1 or q.count(' which ')>1:
        return 'investigate'
    covered=len(qt&engine.doc_tokens[base[0]])/max(1,len(qt))
    return 'fast' if covered>=0.80 else 'investigate'
