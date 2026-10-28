#!/usr/bin/env python3
"""PGER experimental-review preflight: require three *substantive* official-architecture contrasts.

A syntactic governance gate, not a truth checker, SOTA reproduction, model,
reviewer attestation or GitHub branch protection. Call in EVERY future
experimental workflow BEFORE running benchmarks.
"""
from __future__ import annotations
import argparse,json,pathlib,sys

SYSTEMS={
 "SAG2":"github.com/Zleap-AI/SAG-Benchmark",
 "HippoRAG2":"github.com/OSU-NLP-Group/HippoRAG",
 "S2GRAG":"github.com/nianaaa/S2G-RAG",
}
ROOT_FIELDS={
 "experiment_id":8,
 "review_date":10,
 "observed_failure":80,
 "baseline":40,
 "pger_native_proposal":100,
 "preregistered_evaluation":120,
 "acceptance_criteria":100,
 "status":15
}
SYSTEM_FIELDS={
 "official_source":30,
 "actual_mechanism":80,
 "what_pger_previously_tested":60,
 "failure_specific_contrast":80,
 "proposed_adaptation":80,
 "costs_and_risks":60,
 "falsifier":80
}
MANDATORY_PRESERVATION={
 "competing_hypotheses","proof_gap_ledger","provenance_hashes",
 "independent_sources","bounded_search","contradiction_abstention"
}
ALLOWED_STATUS={
 "review_accepted_proposal_not_implemented",
 "implementation_pending_frozen_test",
 "experimental_negative",
 "replication_pending",
 "rejected"
}
MANDATORY_FAILURE_MODES={
 "candidate_missing","wrong_ranking","unproven_entailment",
 "search_drift","missing_source","indexing_cost","evaluation_integrity",
 "domain_transfer"
}

def errors_for_review(r):
    e=[]
    if not isinstance(r,dict):return ["Review root must be a JSON object"]
    for k,minimum in ROOT_FIELDS.items():
        v=r.get(k)
        if not isinstance(v,str) or len(v.strip())<minimum:
            e.append(f"{k}: explain at least {minimum} characters")
    if r.get("status") not in ALLOWED_STATUS:
        e.append("status: must identify proposal/rejection/replication state")
    if r.get("should_promote") is not False:
        e.append("should_promote must be false at review/preflight stage")
    if r.get("actual_official_sag2_hipporag2_s2g_head_to_head_run") is not False:
        e.append("full official three-system reproduction cannot be asserted without separately audited run evidence")
    runs=r.get("evidence_run_urls")
    if not isinstance(runs,list) or not runs or any(not isinstance(x,str) or "github.com/" not in x for x in runs):
        e.append("evidence_run_urls: require at least one recorded official source experiment")
    modes=r.get("failure_modes")
    if not isinstance(modes,list) or not modes or any(x not in MANDATORY_FAILURE_MODES for x in modes):
        e.append("failure_modes: classify the observed failure using known categories")
    preserve=r.get("preserves")
    if not isinstance(preserve,list) or not MANDATORY_PRESERVATION.issubset(set(str(x) for x in preserve)):
        e.append("preserves: all six PGER distinctive controls must be explicitly retained")
    controls=r.get("prior_negative_controls")
    if not isinstance(controls,list) or not controls:
        e.append("prior_negative_controls: account for earlier failed PGER approaches")
    systems=r.get("systems")
    if not isinstance(systems,dict) or set(systems)!=set(SYSTEMS):
        e.append("systems: review all exactly three official references (SAG2, HippoRAG2, S2GRAG)")
    else:
        for name,domain in SYSTEMS.items():
            s=systems[name]
            if not isinstance(s,dict):
                e.append(name+": expected section object");continue
            for k,minimum in SYSTEM_FIELDS.items():
                v=s.get(k)
                if not isinstance(v,str) or len(v.strip())<minimum:
                    e.append(f"{name}.{k}: explain >= {minimum} characters")
            src=s.get("official_source")
            if not isinstance(src,str) or domain.lower() not in src.lower():
                e.append(f"{name}.official_source must link the matching official repository")
    return e

def validate_file(path):
    try:
        data=json.loads(pathlib.Path(path).read_text(encoding="utf8"))
    except (OSError,json.JSONDecodeError) as exc:
        return [f"Cannot parse review JSON: {exc}"]
    return errors_for_review(data)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("review",type=pathlib.Path)
    a=p.parse_args()
    e=validate_file(a.review)
    if e:
        for error in e:print("REVIEW_GATE_FAIL:",error,file=sys.stderr)
        raise SystemExit(1)
    print("PGER_REVIEW_GATE_PASS:",a.review)
    print("NOTE: STRUCTURAL ONLY; evidence/source claims and causality require independent expert review.")

if __name__=="__main__":
    main()
