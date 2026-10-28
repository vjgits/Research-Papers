#!/usr/bin/env python3
"""PGER V13C: conservative source-witness / proof-gap ledger (NO truth oracle).

This module never asserts entailment from words, cosine similarity, co-necessity,
NLI logits, or user-editable unsupported claims. It checks exact source ranges,
source hashes, reviewer allowlists, distinct supporting sources, contradictions,
and remaining retrieval budget.

The trusted-reviewer allowlist MUST be provisioned by an independent external
review process; default empty means no 'ready' result. There is no signature,
identity attestation or model-based verifier in this module. Reviewers in tests
are SIMULATED, not actual human-validated research data.

READY_FOR_ANSWER_GENERATION is NOT a factual correctness guarantee and
does not produce an answer.
"""
from __future__ import annotations
from dataclasses import dataclass,field
from enum import Enum
from hashlib import sha256
from typing import Mapping,FrozenSet,Sequence

class Verdict(str,Enum):
    SUPPORTED="supported"
    CONTRADICTED="contradicted"
    UNKNOWN="unknown"

class Status(str,Enum):
    READY_FOR_ANSWER_GENERATION="ready_for_answer_generation"
    SEARCH_GAPS="search_gaps"
    ABSTAIN="abstain"

@dataclass(frozen=True)
class Claim:
    claim_id:str
    subject:str
    relation:str
    object:str
    min_distinct_sources:int=1

    def __post_init__(self):
        if not self.claim_id or not all((self.subject,self.relation,self.object)):
            raise ValueError("Structured claim needs ID, subject, relation and object")
        if self.min_distinct_sources < 1:
            raise ValueError("min_distinct_sources must be >=1")

@dataclass(frozen=True)
class Source:
    source_id:str
    text:str
    source_type:str="document"

    @property
    def sha256(self):
        return sha256(self.text.encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class Witness:
    claim_id:str
    source_id:str
    source_sha256:str
    start:int
    end:int
    quoted_span:str
    verdict:Verdict
    validator_id:str
    audit_reference:str=""

@dataclass(frozen=True)
class ProofPolicy:
    allowed_reviewers:FrozenSet[str]=frozenset()
    # Literal external trust policy, NOT asserted by model/user data.
    allow_single_reviewer_for_test:bool=False
    maximum_claims:int=32

@dataclass
class Decision:
    status:Status
    missing_claim_ids:list[str]=field(default_factory=list)
    contradicted_claim_ids:list[str]=field(default_factory=list)
    supporting_sources:dict[str,list[str]]=field(default_factory=dict)
    validated_witnesses:int=0
    rejected_witnesses:list[dict]=field(default_factory=list)
    remaining_budget:int=0
    proof_is_independently_verified:bool=False

    def to_dict(self):
        return {
            "status":self.status.value,
            "missing_claim_ids":self.missing_claim_ids,
            "contradicted_claim_ids":self.contradicted_claim_ids,
            "supporting_sources":self.supporting_sources,
            "validated_witnesses":self.validated_witnesses,
            "rejected_witnesses":self.rejected_witnesses,
            "remaining_budget":self.remaining_budget,
            "proof_is_independently_verified":False,
            "warning":"Evidence-checker and external reviewer authorization must be independently validated; no generated answer or fact entailment is proven."
        }

def decide(claims:Sequence[Claim],
           documents:Mapping[str,Source],
           witnesses:Sequence[Witness],
           search_budget_remaining:int,
           policy:ProofPolicy|None=None)->Decision:
    """Deterministic fail-closed controller, no generated-answer model call.

    Crucial: a REVIEWER ID in a provided witness is NOT cryptographic
    authentication; caller must supply the allowlist in a separate trusted
    context and authenticate reviewers externally. Otherwise use default empty
    policy. This module never auto-populates trusted reviewers.
    """
    policy=policy or ProofPolicy()
    if search_budget_remaining<0:raise ValueError("budget cannot be negative")
    if len(claims)>policy.maximum_claims:raise ValueError("too many claims")
    ids=[c.claim_id for c in claims]
    if len(ids)!=len(set(ids)):raise ValueError("claim IDs must be unique")
    d=Decision(status=Status.ABSTAIN,remaining_budget=search_budget_remaining)
    if not claims:
        d.rejected_witnesses=[{"reason":"no_required_claims"}]
        return d
    claims_by={c.claim_id:c for c in claims}
    accepted:dict[str,dict[str,set[str]]]={}
    # A single trusted validator may be permitted by an external policy.
    # Unit tests deliberately simulate this. Production should require
    # actual independent validator authentication and reviewer quorum.
    for w in witnesses:
        why=None
        src=documents.get(w.source_id)
        if w.claim_id not in claims_by:
            why="unknown_claim"
        elif w.validator_id not in policy.allowed_reviewers:
            why="unapproved_validator"
        elif src is None or src.source_id!=w.source_id:
            why="unknown_source"
        elif src.sha256!=w.source_sha256:
            why="stale_source_hash"
        elif not isinstance(w.verdict,Verdict):
            why="invalid_verdict"
        elif not isinstance(w.start,int) or not isinstance(w.end,int):
            why="invalid_offsets"
        elif w.start<0 or w.end>w.start+100000 or w.end>len(src.text) or w.end<=w.start:
            why="out_of_bounds_span"
        elif src.text[w.start:w.end]!=w.quoted_span:
            why="quote_mismatch"
        elif not w.audit_reference:
            why="missing_external_audit_reference"
        if why:
            d.rejected_witnesses.append({
                "claim_id":w.claim_id,"source_id":w.source_id,"reason":why})
            continue
        d.validated_witnesses+=1
        bucket=accepted.setdefault(w.claim_id,{"support":set(),"contra":set()})
        if w.verdict==Verdict.SUPPORTED:
            bucket["support"].add(w.source_id)
        elif w.verdict==Verdict.CONTRADICTED:
            bucket["contra"].add(w.source_id)

    for c in claims:
        entry=accepted.get(c.claim_id,{"support":set(),"contra":set()})
        d.supporting_sources[c.claim_id]=sorted(entry["support"])
        if entry["contra"]:
            d.contradicted_claim_ids.append(c.claim_id)
        elif len(entry["support"])<c.min_distinct_sources:
            d.missing_claim_ids.append(c.claim_id)

    if d.contradicted_claim_ids:
        # Contradiction is an unresolved dispute. Never silently choose
        # the most numerous agreeing passages as fact.
        d.status=Status.ABSTAIN
    elif d.missing_claim_ids:
        d.status=(Status.SEARCH_GAPS if search_budget_remaining>0
                  else Status.ABSTAIN)
    else:
        # Passing mechanical external-approval checks is NOT proof of
        # reviewer truth. Status is an *input gate*, not an answer.
        d.status=Status.READY_FOR_ANSWER_GENERATION
    return d
