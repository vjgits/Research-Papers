#!/usr/bin/env python3
"""Deterministic tests for the mandatory architecture review preflight."""
import copy,json,pathlib,unittest
from validate_three_system_review import errors_for_review,validate_file

ROOT=pathlib.Path(__file__).parent
REVIEW=ROOT/"reviews"/"v14_failure_three_systems.json"

class GovernanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.good=json.loads(REVIEW.read_text())
    def test_real_postmortem_passes(self):
        self.assertEqual(validate_file(REVIEW),[])
    def test_missing_one_reference_is_rejected(self):
        bad=copy.deepcopy(self.good)
        del bad["systems"]["S2GRAG"]
        self.assertTrue(any("all exactly three" in e for e in errors_for_review(bad)))
    def test_unreviewed_ppr_not_acceptable(self):
        bad=copy.deepcopy(self.good)
        bad["systems"]["HippoRAG2"]["what_pger_previously_tested"]="just PPR"
        self.assertTrue(any("HippoRAG2.what_pger_previously_tested" in e for e in errors_for_review(bad)))
    def test_empty_causal_hypothesis_is_rejected(self):
        bad=copy.deepcopy(self.good)
        bad["systems"]["SAG2"]["falsifier"]=""
        self.assertTrue(any("SAG2.falsifier" in e for e in errors_for_review(bad)))
    def test_cannot_assert_unverified_promotion(self):
        bad=copy.deepcopy(self.good)
        bad["should_promote"]=True
        self.assertTrue(any("should_promote" in e for e in errors_for_review(bad)))
    def test_cannot_fake_official_head_to_head(self):
        bad=copy.deepcopy(self.good)
        bad["actual_official_sag2_hipporag2_s2g_head_to_head_run"]=True
        self.assertTrue(any("full official" in e for e in errors_for_review(bad)))
    def test_unbounded_search_violates_pger_identity(self):
        bad=copy.deepcopy(self.good)
        bad["preserves"].remove("bounded_search")
        self.assertTrue(any("all six" in e for e in errors_for_review(bad)))
    def test_no_prior_negatives_is_rejected(self):
        bad=copy.deepcopy(self.good)
        bad["prior_negative_controls"]=[]
        self.assertTrue(any("prior_negative_controls" in e for e in errors_for_review(bad)))
    def test_wrong_official_repo_rejected(self):
        bad=copy.deepcopy(self.good)
        bad["systems"]["SAG2"]["official_source"]=bad["systems"]["S2GRAG"]["official_source"]
        self.assertTrue(any("SAG2.official_source" in e for e in errors_for_review(bad)))
    def test_failure_modes_required(self):
        bad=copy.deepcopy(self.good)
        bad["failure_modes"]=[]
        self.assertTrue(any("failure_modes" in e for e in errors_for_review(bad)))

if __name__=="__main__":unittest.main()
