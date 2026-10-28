"""V9.5 preliminary deterministic workspace: no LLM, no semantic entailment.

Concept inspired by Hasson et al., ScalableRAG (2026). Do not claim original
set operations or source-string matches as verified facts. Inputs are raw
text documents keyed by unique identifiers.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import re
from typing import Mapping

@dataclass(frozen=True)
class Match:
    source_id: str
    start: int
    end: int
    text: str
    sha256: str

@dataclass(frozen=True)
class Partition:
    positive: str
    negative: str
    positive_count: int
    negative_count: int
    rejected_anchor_count: int
    complement_checked: bool

class Workspace:
    def __init__(self, docs: Mapping[str,str]):
        if len(docs)!=len(set(docs)) or any(not str(k) for k in docs):
            raise ValueError('Documents require unique, nonempty identifiers')
        self.docs=dict(docs)
        self.sets={'all':frozenset(docs)}
        self.matches:dict[str,tuple[Match,...]]={}
        self.history=[]
    def get(self,name):
        if name not in self.sets: raise KeyError(name)
        return self.sets[name]
    def _register(self,name,ids):
        if name in self.sets: raise ValueError('Name already used')
        ids=frozenset(ids)
        if not ids<=self.get('all'): raise ValueError('Unknown source IDs')
        self.sets[name]=ids
        return ids
    def combine(self,a,b,op,out):
        x,y=self.get(a),self.get(b)
        if op=='and':ids=x&y
        elif op=='or':ids=x|y
        elif op=='minus':ids=x-y
        else:raise ValueError('Unsupported set operation')
        self._register(out,ids)
        self.history.append({'action':'combine','a':a,'b':b,'op':op,'out':out,'count':len(ids)})
        return ids
    def partition(self,parent,regex,name,anchor_tokens=(),flags=re.IGNORECASE):
        """Partition without dropping negatives; record exact source positions.
        Anchor diagnostics reveal potential lexical false negatives, not truth.
        """
        source_ids=self.get(parent)
        pattern=re.compile(regex,flags)
        hits={};positive=set()
        for source_id in source_ids:
            content=self.docs[source_id]
            matched=list(pattern.finditer(content))
            if matched:
                positive.add(source_id)
                digest=hashlib.sha256(content.encode()).hexdigest()
                hits[source_id]=tuple(Match(source_id,m.start(),m.end(),m.group(0),digest) for m in matched)
        negative=source_ids-positive
        pos_name=f'{name}_yes';neg_name=f'{name}_no'
        if name in self.sets or pos_name in self.sets or neg_name in self.sets:
            raise ValueError('Name already used')
        self._register(pos_name,positive)
        self._register(neg_name,negative)
        self.matches[pos_name]=tuple(m for v in hits.values() for m in v)
        anchors=tuple(t.casefold() for t in anchor_tokens if t)
        excluded=sum(any(token in self.docs[i].casefold() for token in anchors) for i in negative)
        report=Partition(pos_name,neg_name,len(positive),len(negative),excluded,positive|negative==source_ids and not (positive&negative))
        self.history.append({'action':'partition','parent':parent,'name':name,'regex':regex,'positive':len(positive),'negative':len(negative),'excluded_anchor_count':excluded})
        return report
    def verify_matches(self,set_name):
        for match in self.matches.get(set_name,()):
            source=self.docs[match.source_id]
            if source[match.start:match.end]!=match.text:return False
            if hashlib.sha256(source.encode()).hexdigest()!=match.sha256:return False
        return True
    def preview_partition(self,parent,regex,anchor_tokens=()):
        """Side-effect-free filter preview for branch comparison."""
        source_ids=self.get(parent);pattern=re.compile(regex,re.IGNORECASE)
        positive={i for i in source_ids if pattern.search(self.docs[i])}
        negative=source_ids-positive
        anchors=tuple(t.casefold() for t in anchor_tokens if t)
        return {'matches':len(positive),'misses':len(negative),'anchor_misses':sum(any(t in self.docs[i].casefold() for t in anchors) for i in negative)}