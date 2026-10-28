"""Research prototype: decision-sensitive proof-gap scheduling.

A formal, testable PGER hypothesis, NOT a proven original or state-of-art method.
Value of information and reachability are known concepts; distinguishing claim is
whether sourced dependency + decision sensitivity + cost achieves a new Pareto frontier
against S2G-RAG, A2RAG, AdaKG-RAG and simpler same-cost controls.
No LLM-as-judge hallucinated evidence is promoted to verified status.
"""
from dataclasses import dataclass
from typing import Mapping, Sequence
from hashlib import sha256

@dataclass(frozen=True)
class SourcedClaim:
    edge_id: str
    status: str # verified, refuted, unknown
    source_id: str = ''
    quote: str = ''
    quote_sha256: str = ''

    def valid(self):
        if self.status not in ('verified','refuted','unknown'):return False
        if self.status=='verified':
            return bool(self.source_id and self.quote and self.quote_sha256==sha256(self.quote.encode()).hexdigest())
        return True

@dataclass(frozen=True)
class ProofGap:
    edge_id: str
    cost_units: float
    source_dependency: tuple = ()

class ProofGraph:
    def __init__(self,proofs:Mapping[str,Sequence[Sequence[str]]],claims:Sequence[SourcedClaim]):
        self.proofs={answer:[tuple(p) for p in paths] for answer,paths in proofs.items()}
        self.claims={c.edge_id:c for c in claims}
        if len(self.claims)!=len(claims):raise ValueError('duplicate edge IDs')
        if not all(c.valid() for c in claims):raise ValueError('verified claims must preserve source hashes')
        if any(e not in self.claims for paths in self.proofs.values() for p in paths for e in p):
            raise ValueError('unknown dependency ID')
    def outcomes(self,decision=None):
        decision=decision or {}
        viable=set();supported=set()
        for answer,paths in self.proofs.items():
            for p in paths:
                values=[decision.get(e,self.claims[e].status) for e in p]
                if all(v!='refuted' for v in values):viable.add(answer)
                if all(v=='verified' for v in values):supported.add(answer)
        return frozenset(viable),frozenset(supported)
    def rank_gaps(self,gaps:Sequence[ProofGap],max_cost=float('inf')):
        """Testable *decision sensitivity proxy*, NOT true expected value of information.
        A gap is useful if its resolution can change feasible or supported answer sets.
        Strictly excludes false verification: simulated branches are never written to claims.
        """
        ranked=[]
        for gap in gaps:
            if gap.edge_id not in self.claims or self.claims[gap.edge_id].status!='unknown':continue
            if gap.cost_units<=0 or gap.cost_units>max_cost:continue
            if any(self.claims[e].status!='verified' for e in gap.source_dependency):continue
            good,supp_good=self.outcomes({gap.edge_id:'verified'})
            bad,supp_bad=self.outcomes({gap.edge_id:'refuted'})
            delta=len(good^bad) + 2*len(supp_good^supp_bad)
            if delta==0:continue
            ranked.append((delta/gap.cost_units,gap.edge_id,delta,gap.cost_units))
        ranked.sort(key=lambda x:(-x[0],x[1]))
        return [{'edge_id':e,'impact_per_cost':round(value,6),'decision_delta':int(delta),'cost_units':cost}
                 for value,e,delta,cost in ranked]
    def act_or_abstain(self,gaps,max_cost):
        # Unambiguous answer only when exactly one supported conclusion, and no
        # additional viable conflicting conclusion; else retrieve or abstain.
        viable,supported=self.outcomes()
        if len(viable)==len(supported)==1:return {'action':'answer','answer':next(iter(supported))}
        ranking=self.rank_gaps(gaps,max_cost=max_cost)
        if ranking:return {'action':'retrieve','gap':ranking[0]}
        return {'action':'abstain','reason':'insufficient discriminating sourced evidence under budget'}