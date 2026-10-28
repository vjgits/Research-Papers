"""PGER V7.2 falsifiable, zero-API, *surface-semantic* evidence ledger.

The extraction is deterministic and deliberately weak: asserted predicate labels
are assigned only on exact observed cue phrases; other source-title mentions are
recorded as ASSOCIATIONS rather than interpreted as factual triples. A relation
is never considered evidence without a verifiable source offset/span.

Candidate generation is COMMON to both reset and retained-ledger arms; the only
ablation is whether previously observed sourced relations may influence scoring.
This is a baseline experiment, NOT a general natural-language relation parser.
"""
from dataclasses import dataclass
from collections import defaultdict, Counter
try:
    import ahocorasick
except ImportError:
    ahocorasick=None
import re
import time

CUES=(
 ("was born in", "born_in"), ("born in", "born_in"),
 ("died in", "died_in"), ("is located in", "located_in"),
 ("located in", "located_in"), ("was founded in", "founded_in"),
 ("founded in", "founded_in"), ("was directed by", "directed_by"),
 ("directed by", "directed_by"), ("was written by", "written_by"),
 ("written by", "written_by"), ("was produced by", "produced_by"),
 ("produced by", "produced_by"), ("is part of", "part_of"),
 ("was part of", "part_of"), ("is a member of", "member_of"),
 ("was a member of", "member_of"), ("is the capital of", "capital_of"),
 ("was the capital of", "capital_of"), ("is married to", "married_to"),
 ("married to", "married_to"), ("is the parent of", "parent_of"),
 ("was the parent of", "parent_of"), ("is a subsidiary of", "subsidiary_of"),
 ("was a subsidiary of", "subsidiary_of"),
)
CUES=tuple(sorted(CUES,key=lambda x:-len(x[0])))
STOP=frozenset('the a an of from for with and or in on to at by what which who when where how did is was were are it its their his her this that'.split())
FUNCTIONAL=frozenset(('born_in','died_in','capital_of'))
WORDS=re.compile(r"[\w]+",re.UNICODE)
SENTENCES=re.compile(r"[^.!?\n]+(?:[.!?]|$)")


def terms(s):
    return frozenset(w for w in WORDS.findall(s.casefold()) if len(w)>=3 and w not in STOP)

@dataclass(frozen=True)
class Claim:
    source: int
    target: int
    source_id: str
    target_id: str
    subject: str
    predicate: str
    object: str
    start: int
    end: int
    quote: str
    provenance: str       # exact_title or unique_alias
    asserted: bool         # false for topical association / unsourced relation

class ClaimIndex:
    """Build once from documents and titles, never from test labels/questions."""
    def __init__(self,docs):
        t0=time.perf_counter()
        self.docs=docs
        self.claims=[]
        self.links=defaultdict(list)
        titles=defaultdict(set)
        for i,d in enumerate(docs):
            title=str(d['title']).strip()
            if len(title)>=5:
                titles[title.casefold()].add(i)
            # Only unique, 2+-word long prefixes of full titles. This can
            # bridge some mentions without turning common one-word names into edges.
            base=re.sub(r'\s*\([^)]*\)\s*',' ',title).strip()
            parts=base.split()
            if len(parts)>=3:
                alias=' '.join(parts[:2]).casefold()
                if len(alias)>=9: titles[alias].add(i)
        # Reject ambiguous phrases; alias cannot assert entity identity if shared.
        unique={phrase:next(iter(ids)) for phrase,ids in titles.items() if len(ids)==1}
        pattern=None
        if unique:
            pattern=re.compile(r'(?<!\w)(?:'+ '|'.join(re.escape(t) for t in sorted(unique,key=lambda s:(-len(s),s)))+r')(?!\w)',re.I)
        autom=None
        if unique and ahocorasick is not None:
            autom=ahocorasick.Automaton()
            for alias,idx in sorted(unique.items()):autom.add_word(alias,(alias,idx))
            autom.make_automaton()
        for src,d in enumerate(docs):
            body=str(d.get('text') or '')
            for sentence in SENTENCES.finditer(body):
                if pattern is None:continue
                quote=sentence.group(0).strip()
                if not quote:continue
                observed=set()
                line=sentence.group(0)
                if autom is None:
                    matches=((m.start(),m.end(),m.group().casefold(),unique[m.group().casefold()]) for m in pattern.finditer(line))
                else:
                    folded=line.casefold()
                    matches=[]
                    for end,(alias,dst) in autom.iter(folded):
                        start=end-len(alias)+1
                        if start>0 and folded[start-1].isalnum():continue
                        if end+1<len(folded) and folded[end+1].isalnum():continue
                        matches.append((start,end+1,alias,dst))
                for start_match,end_match,alias,dst in matches:
                    if dst==src or dst in observed:continue
                    observed.add(dst)
                    predicate='association'
                    for cue,label in CUES:
                        if re.search(r'(?<!\w)'+re.escape(cue)+r'(?!\w)',quote,re.I):
                            predicate=label;break
                    # A cue in a sentence is not enough to infer subject/object
                    # direction. Keep assertion false unless source title is
                    # explicitly stated in the very same evidence span.
                    source_title=str(d['title']).strip()
                    src_match=re.search(r'(?<!\w)'+re.escape(source_title)+r'(?!\w)',quote,re.I)
                    cue_match=next((re.search(r'(?<!\w)'+re.escape(cue)+r'(?!\w)',quote,re.I)
                        for cue,label in CUES if label==predicate and re.search(r'(?<!\w)'+re.escape(cue)+r'(?!\w)',quote,re.I)),None)
                    # Only an observed subject BEFORE the relational cue and
                    # target AFTER it qualifies as a directional assertion.
                    asserted=bool(predicate!='association' and src_match and cue_match
                                  and src_match.end()<=cue_match.start() and end_match>cue_match.end())
                    exact=(alias==str(docs[dst]['title']).strip().casefold())
                    claim=Claim(src,dst,str(d['_id']),str(docs[dst]['_id']),source_title,
                        predicate,str(docs[dst]['title']),sentence.start(),sentence.end(),
                        sentence.group(0),'exact_title' if exact else 'unique_alias',asserted)
                    self.claims.append(claim)
                    self.links[src].append(claim)
        for src in self.links:
            self.links[src].sort(key=lambda c:(c.target_id,c.start,c.end))
        self.seconds=time.perf_counter()-t0

    def valid(self,claim):
        return (self.docs[claim.source]['_id']==claim.source_id and
                self.docs[claim.target]['_id']==claim.target_id and
                self.docs[claim.source]['text'][claim.start:claim.end]==claim.quote)

    def contradictions(self,source_subset=None):
        """Potential functional-relation conflicts, not truth adjudication."""
        groups=defaultdict(set)
        for c in self.claims:
            if c.asserted and c.predicate in FUNCTIONAL and (source_subset is None or c.source in source_subset):
                groups[(c.subject.casefold(),c.predicate)].add(c.object.casefold())
        return {k:sorted(v) for k,v in groups.items() if len(v)>1}


def should_expand(question,docs,bm25):
    """Both arms use exactly this predeclared cheap query-dependent gate."""
    if not bm25:return False
    q=terms(question)
    if not q:return False
    top=docs[bm25[0]]
    covered=terms(top['title']+' '+top.get('text',''))
    return len(q-covered)/len(q)>=0.25


def make_shared_candidates(question,docs,base,bm25,claims,search,max_queries=2,limit=40):
    """One shared candidate pool; no ledger-dependent retrieval leakage.

    Secondary queries are derived from original question and verified text.
    They are constructed independently of the retention mode. max_queries
    controls the EXACT number of search calls in both arms.
    """
    seen=set(base[:limit]); seen.update(bm25[:limit]); calls=[]
    if not should_expand(question,docs,bm25):
        return sorted(seen),calls
    qterms=terms(question)
    for anchor in base[:max_queries]:
        related=claims.links.get(anchor,[])
        if related:
            c=max(related,key=lambda c:(c.asserted,len(terms(c.quote)&qterms),c.target_id))
            query=' '.join((str(docs[c.target]['title']), ' '.join(sorted(qterms-terms(c.quote)))))
        else:
            query=' '.join((str(docs[anchor]['title']), ' '.join(sorted(qterms-terms(docs[anchor]['text'])))))
        query=query.strip() or question
        retrieved=search(query,limit)
        calls.append({'query':query,'source_id':docs[anchor]['_id'],
                      'retrieved':len(retrieved)})
        seen.update(retrieved[:limit])
    # Both variants get *exactly* the same candidate union, including link neighbors.
    for i in base[:limit]:
        seen.update(c.target for c in claims.links.get(i,[]))
    return sorted(seen),calls


def rank_with_claims(question,docs,base,bm25,claims,candidates,retain=True,toplimit=100):
    """Same beam, depth, candidate pool and path budget for both arms.

    The retained arm rewards NEW predicate/entity dependencies along supported
    paths. The reset arm can use only the most recent transition predicate.
    Neither arm uses gold labels, a generative model, or ungrounded triples.
    """
    qterms=terms(question); qpred={p for cue,p in CUES if cue in question.casefold()}
    basepos={i:k for k,i in enumerate(base)}
    bpos={i:k for k,i in enumerate(bm25)}
    allowed=set(candidates)
    protected=base[:1]
    seeds=base[:5]
    frontier=[(0.,(i,),(),frozenset(),frozenset()) for i in seeds]
    all_paths=list(frontier)
    # Exactly 3 expansions (enough to test 4-document chains), fixed beam/fanout.
    for depth in range(3):
        expanded=[]
        for prev,path,pathclaims,preds,entities in frontier:
            src=path[-1]
            available=[c for c in claims.links.get(src,[]) if c.target in allowed and c.target not in path]
            possible=[]
            for c in available:
                if not claims.valid(c):raise AssertionError('Invalid evidence offset/span')
                dest=c.target
                tf=len(qterms&terms(docs[dest]['title']+' '+docs[dest].get('text','')))/max(1,len(qterms))
                # Both arms can score an observed local relation. Retention
                # may additionally score *new dependent* sourced relations.
                newrel=int(c.predicate!='association' and c.predicate not in (preds if retain else frozenset()))
                newentity=int(c.target_id not in (entities if retain else frozenset()))
                strong=int(c.asserted)
                qrel=int(c.predicate in qpred)
                rankfit=1/(1+bpos.get(dest,200))*0.20
                local=0.40*tf+0.20*qrel+0.12*strong+0.08*newrel+0.04*newentity+rankfit
                if c.provenance=='unique_alias':local-=0.06
                if c.predicate=='association':local-=0.08
                possible.append((local,c))
            possible.sort(key=lambda x:(-x[0],x[1].target_id,x[1].start))
            for gain,c in possible[:8]:
                # Dependency chain is explicit: each claim starts where the
                # preceding one ended; source spans are checked separately.
                newpreds=(preds|{c.predicate}) if retain else frozenset({c.predicate})
                newentities=(entities|{c.target_id}) if retain else frozenset({c.target_id})
                expanded.append((prev*0.82+gain-0.035*depth,
                    path+(c.target,),pathclaims+(c,),newpreds,newentities))
        if not expanded:break
        expanded.sort(key=lambda x:(-x[0],tuple(docs[i]['_id'] for i in x[1])))
        frontier=[]; used=set()
        for state in expanded:
            if state[1][-1] in used:continue
            used.add(state[1][-1]);frontier.append(state)
            if len(frontier)>=8:break
        all_paths.extend(frontier)
    all_paths.sort(key=lambda x:(-x[0],-len(x[1]),tuple(docs[i]['_id'] for i in x[1])))
    result=list(protected);seen=set(result)
    # Bounded path selection, then preserve classical retrieval fallback.
    for score,path,trail,pred,entity in all_paths:
        for i in path:
            if i not in seen:
                result.append(i);seen.add(i)
            if len(result)>=10:break
        if len(result)>=10:break
    for i in base:
        if i not in seen:
            result.append(i);seen.add(i)
        if len(result)>=toplimit:break
    for i in bm25:
        if i not in seen:
            result.append(i);seen.add(i)
        if len(result)>=toplimit:break
    # Add source-only candidates at the tail; do not falsely lift them to top 5.
    for i in candidates:
        if i not in seen:
            result.append(i);seen.add(i)
        if len(result)>=toplimit:break
    best=next((trail for score,path,trail,pred,entity in all_paths if trail),())
    evidence=[{'source_id':c.source_id,'target_id':c.target_id,
        'predicate':c.predicate,'asserted':c.asserted,'provenance':c.provenance,
        'span':[c.start,c.end],'quote':c.quote,
        'depends_on_edge':(j-1 if j>0 else None)} for j,c in enumerate(best)]
    return result[:toplimit],{'paths':len(all_paths),'deepest':max((len(p)-1 for _,p,*_ in all_paths),default=0),
          'sourced_links':sum(bool(t) for _,_,t,*_ in all_paths),
          'best_evidence_dependency_path':evidence}