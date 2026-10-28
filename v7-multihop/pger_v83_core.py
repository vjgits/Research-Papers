"""PGER V8.3: conservative question-title anchor + source-bridge ablation.

Recognize explicit question-document title mentions without gold relevance labels.
Never interpret topical co-occurrence as entailed evidence. All inserted edges
are observed source text with exact provenance, not logically proved facts.
"""
from collections import defaultdict
import re,time
from pger_v72_core import terms
try: import ahocorasick
except ImportError:ahocorasick=None

LINK_PRED={'director':{'directed_by'},'producer':{'produced_by'},
    'writer':{'written_by'},'author':{'written_by'},'born':{'born_in'},'capital':{'capital_of'}}

class TitleAnchors:
    def __init__(self,docs):
        t=time.perf_counter();self.docs=docs
        titles=defaultdict(list)
        for i,d in enumerate(docs):
            title=str(d['title']).casefold().strip()
            if len(title)>=9 and len(title.split())>=2:titles[title].append(i)
        self.lookup={k:tuple(v) for k,v in titles.items() if len(v)<=8}
        self.autom=None
        if ahocorasick is not None and self.lookup:
            self.autom=ahocorasick.Automaton()
            for title in sorted(self.lookup):self.autom.add_word(title,title)
            self.autom.make_automaton()
        self.seconds=time.perf_counter()-t

    def mentions(self,q,rank,cap=4):
        s=q.casefold();found={};pos={j:i for i,j in enumerate(rank)}
        if self.autom:
            matches=((end-len(k)+1,end+1,k) for end,k in self.autom.iter(s))
        else:
            matches=((m.start(),m.end(),k) for k in self.lookup for m in re.finditer(re.escape(k),s))
        for start,end,k in matches:
            if start>0 and s[start-1].isalnum():continue
            if end<len(s) and s[end].isalnum():continue
            ids=sorted(self.lookup[k],key=lambda i:(pos.get(i,1000),str(self.docs[i]['_id'])))
            if ids:found[k]=(len(k),ids[0])
        out=sorted(found.values(),key=lambda x:(-x[0],pos.get(x[1],1000),str(self.docs[x[1]]['_id'])))
        return [i for _,i in out[:cap]]

def relation_targets(question,anchor,em,excluded=()):
    """Returns sourced neighbor candidates, not inferred truth triples."""
    q=question.casefold();excluded=set(excluded);query_terms=terms(question)
    wanted=set()
    for label,predicates in LINK_PRED.items():
        if label in q:wanted|=predicates
    found=[]
    for c in em.out.get(anchor,[]):
        if c.target in excluded:continue
        if c.predicate not in wanted:continue
        if c.predicate=='association':continue
        sig=3*int(c.asserted)+min(2,len(query_terms&terms(c.quote)))
        found.append((sig,c.target,c))
    return sorted(found,key=lambda z:(-z[0],em.ids[z[1]]))

def select_guarded_chain(question,fast,em,titleindex,allowed=None):
    """Preserve fast results unless two named question anchors each have
    observed predicate-matching edges with exact source provenance."""
    originals=list(fast)
    anchors=titleindex.mentions(question,fast)
    if len(anchors)<2:return originals,{'activated':False,'reason':'fewer_than_two_question_titles','anchors':anchors}
    qt=terms(question)
    if not (qt&{'earlier','later','older','younger','first','same','both','more'}):
        return originals,{'activated':False,'reason':'no_compared_entities','anchors':anchors}
    anchors=anchors[:2]
    picked=[];trail=[]
    for src in anchors:
        options=relation_targets(question,src,em,excluded=anchors)
        if allowed is not None:options=[x for x in options if x[1] in allowed]
        if not options:return originals,{'activated':False,'reason':'missing_sourced_edge','anchors':anchors}
        _,j,c=options[0]
        if not em.claims.valid(c):raise AssertionError('Invalid source span')
        if j in picked:return originals,{'activated':False,'reason':'same_target_both_branches','anchors':anchors}
        picked.append(j)
        trail.append({'source_id':c.source_id,'target_id':c.target_id,'quote':c.quote,
                      'span':[c.start,c.end],'predicate':c.predicate,'asserted':c.asserted})
    proposed=[]
    for i in [anchors[0],picked[0],anchors[1],picked[1]]:
        if i not in proposed:proposed.append(i)
    if originals and originals[0] not in proposed:proposed.append(originals[0])
    for i in originals:
        if i not in proposed:proposed.append(i)
    return proposed,{'activated':True,'reason':'two_observed_source_bridges','anchors':anchors,'trail':trail}
