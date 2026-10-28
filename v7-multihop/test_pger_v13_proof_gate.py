#!/usr/bin/env python3
"""Mechanism-only tests with SIMULATED reviewer IDs, not human study."""
import unittest
from dataclasses import replace
from pger_v13_proof_gate import (
    Claim,Source,Witness,Verdict,Status,ProofPolicy,decide)

class GateTests(unittest.TestCase):
    def setUp(self):
        self.claims=[Claim("c1","Paris","is-capital-of","France",2)]
        self.sources={"one":Source("one","Paris is the capital of France."),
            "two":Source("two","France's capital city is Paris."),
            "three":Source("three","Paris is not the capital of France.")}
        self.policy=ProofPolicy(allowed_reviewers=frozenset({"reviewer_A"}))
        self.proofs=[
           Witness("c1","one",self.sources["one"].sha256,0,29,
                  self.sources["one"].text, Verdict.SUPPORTED,
                  "reviewer_A","audit-simulated-001"),
           Witness("c1","two",self.sources["two"].sha256,0,
                  len(self.sources["two"].text),self.sources["two"].text,
                  Verdict.SUPPORTED,"reviewer_A","audit-simulated-002")]
        # All tests are policy consistency tests, not entailment quality.

    def test_default_cannot_claim_verified(self):
        a=decide(self.claims,self.sources,self.proofs,1)
        self.assertEqual(a.status,Status.SEARCH_GAPS)
        self.assertEqual(a.validated_witnesses,0)
        self.assertFalse(a.to_dict()["proof_is_independently_verified"])

    def test_two_sources_with_simulated_allowlist_gate(self):
        a=decide(self.claims,self.sources,self.proofs,1,self.policy)
        self.assertEqual(a.status,Status.READY_FOR_ANSWER_GENERATION)
        self.assertEqual(a.supporting_sources["c1"],["one","two"])
        self.assertFalse(a.to_dict()["proof_is_independently_verified"])

    def test_duplicate_source_not_independent(self):
        a=decide(self.claims,self.sources,[self.proofs[0],self.proofs[0]],
                 1,self.policy)
        self.assertEqual(a.status,Status.SEARCH_GAPS)
        self.assertEqual(a.missing_claim_ids,["c1"])

    def test_stale_provenance_fails_closed(self):
        stale=replace(self.proofs[1],source_sha256="0"*64)
        a=decide(self.claims,self.sources,[self.proofs[0],stale],1,self.policy)
        self.assertEqual(a.status,Status.SEARCH_GAPS)
        self.assertIn("stale_source_hash",[w["reason"] for w in a.rejected_witnesses])

    def test_quote_mismatch_fails_closed(self):
        wrong=replace(self.proofs[1],quoted_span="A hallucinated quote")
        a=decide(self.claims,self.sources,[self.proofs[0],wrong],1,self.policy)
        self.assertEqual(a.status,Status.SEARCH_GAPS)
        self.assertIn("quote_mismatch",[w["reason"] for w in a.rejected_witnesses])

    def test_budget_exhaustion_abstains(self):
        a=decide(self.claims,self.sources,[self.proofs[0]],0,self.policy)
        self.assertEqual(a.status,Status.ABSTAIN)

    def test_contradiction_prevents_ready(self):
        contrasrc=self.sources["three"]
        contra=Witness("c1","three",contrasrc.sha256,0,len(contrasrc.text),
                       contrasrc.text,Verdict.CONTRADICTED,"reviewer_A",
                       "audit-simulated-003")
        a=decide(self.claims,self.sources,self.proofs+[contra],2,self.policy)
        self.assertEqual(a.status,Status.ABSTAIN)
        self.assertEqual(a.contradicted_claim_ids,["c1"])

    def test_failed_minilm_not_in_allowlist(self):
        m=replace(self.proofs[0],validator_id="nli_minilm_hans_failed")
        a=decide(self.claims,self.sources,[m],2,self.policy)
        self.assertEqual(a.status,Status.SEARCH_GAPS)
        self.assertIn("unapproved_validator",[w["reason"] for w in a.rejected_witnesses])

    def test_unknown_claim_not_accepted(self):
        m=replace(self.proofs[0],claim_id="unrequested")
        a=decide(self.claims,self.sources,[m],2,self.policy)
        self.assertEqual(a.status,Status.SEARCH_GAPS)

    def test_unchecked_unknown_verdict_not_supported(self):
        m=replace(self.proofs[0],verdict=Verdict.UNKNOWN)
        a=decide(self.claims,self.sources,[m],2,self.policy)
        self.assertEqual(a.status,Status.SEARCH_GAPS)

    def test_empty_proof_abstains(self):
        a=decide([],{},[],1,self.policy)
        self.assertEqual(a.status,Status.ABSTAIN)
    def test_policy_conflicting_claim_ids_rejected(self):
        with self.assertRaises(ValueError):
            decide(self.claims+self.claims,self.sources,self.proofs,1,self.policy)

if __name__=="__main__":
    unittest.main()
