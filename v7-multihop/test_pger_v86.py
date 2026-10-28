import json, pathlib, unittest
from dataclasses import dataclass
from pger_v86_relation import lexical_scope, hypothesis, logits_to_probs, classify_nli, rerank, query_predicates

@dataclass
class Claim:
    quote:str
    predicate:str
    subject:str='Kalank'
    object:str='Karan Johar'
    asserted:bool=True

class RelationTests(unittest.TestCase):
    def test_v85_real_counterexample_director_vs_producer(self):
        s='Kalank was directed by Abhishek Varman and produced by Karan Johar.'
        self.assertFalse(lexical_scope(Claim(s,'directed_by')))
        self.assertTrue(lexical_scope(Claim(s,'produced_by')))
    def test_negated_relation_rejected(self):
        self.assertFalse(lexical_scope(Claim('Kalank was not directed by Karan Johar.','directed_by')))
    def test_mentions_without_clause_not_claim(self):
        self.assertFalse(lexical_scope(Claim('Kalank and Karan Johar were discussed together.','directed_by')))
    def test_positive_source_clause(self):
        self.assertTrue(lexical_scope(Claim('Kalank was directed by Karan Johar.','directed_by')))
    def test_nli_three_class_order_and_conservative_gate(self):
        self.assertTrue(classify_nli([-4,7,-2])[0])
        self.assertFalse(classify_nli([6,-1,2])[0])
        self.assertFalse(classify_nli([-1,1.5,1.5])[0])
    def test_no_gold_and_equal_ce_scores(self):
        ids=['a','b','c','d','e'];pool=[0,1,2,3,4];fast=[0,1,2,3,4]
        scores={0:.3,1:.9,2:.6,3:.7,4:.5}
        self.assertEqual(rerank(fast,pool,scores,ids,set()),[0,1,3,2,4])
        self.assertEqual(rerank(fast,pool,scores,ids,{(0,2,'directed_by')})[:3],[0,1,3])
    def test_frozen_cases_balanced_and_include_real_error(self):
        p=pathlib.Path(__file__).parent/'contrastive_relation_cases_v86.json'
        data=json.loads(p.read_text())['cases']
        self.assertEqual(len(data),272)
        self.assertEqual(sum(x['expected']=='entailment' for x in data),91)
        self.assertTrue(any(x['id']=='kalank_director_false' for x in data))
        self.assertEqual(len(set(x['id'] for x in data)),len(data))
    def test_query_predicate(self):
        self.assertIn('directed_by',query_predicates('Which director made the film?'))

if __name__=='__main__':unittest.main()