import unittest
from pger_v88_core import *

class V88Tests(unittest.TestCase):
 def test_no_gold_name_detection(self):
  s=['Kalank was directed by Abhishek Varman and produced by Karan Johar.']
  names=regex_mentions(s)
  self.assertIn('kalank',name_set(names));self.assertIn('abhishek varman',name_set(names));self.assertIn('karan johar',name_set(names))
  self.assertTrue(all(valid_mention(m,s) for m in names))
 def test_predicate_clause_disambiguation(self):
  s=['Kalank was directed by Abhishek Varman and produced by Karan Johar.']
  tr=relation_triples(regex_mentions(s),s)
  triples={(norm(t.h),t.r,norm(t.t)) for t in tr}
  self.assertIn(('kalank','P57','abhishek varman'),triples)
  self.assertNotIn(('kalank','P57','karan johar'),triples)
 def test_spans(self):
  s=['Abc Film was directed by Jade Jones.']
  self.assertTrue(all(verify_triple(t,s) for t in relation_triples(regex_mentions(s),s)))
 def test_negation(self):
  s=['Kalank was not directed by Karan Johar.']
  tr=relation_triples(regex_mentions(s),s)
  self.assertEqual(len(tr),0)
 def test_paired_proposal_no_oracle(self):
  s=['Omega Studios met Mira Patel.','Mira Patel lived in London.']
  pairs=pair_candidates(regex_mentions(s),s)
  self.assertTrue(all(a.name!=b.name for a,b in pairs))
 def test_nli_gate(self):
  s=['Film Alpha was directed by Jane Vale.']
  ts=relation_triples(regex_mentions(s),s)
  def infer(p):return [[-2.,6.,-1.] for _ in p]
  keep,z,calls=nli_filter(ts,infer,{'P57':'{h} was directed by {t}.'})
  self.assertEqual(len(keep),len(ts));self.assertEqual(calls,len(ts))
 def test_exact_mention_no_gold(self):
  s=['Prague is located in Czechia.']
  self.assertIn('prague',name_set(regex_mentions(s)))
  self.assertIn('czechia',name_set(regex_mentions(s)))

if __name__=='__main__':unittest.main()