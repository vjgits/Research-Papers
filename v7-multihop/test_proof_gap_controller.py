import unittest,hashlib
from proof_gap_controller import SourcedClaim,ProofGap,ProofGraph

def c(i,status='unknown'):
 text=f'source quote {i}'
 return SourcedClaim(i,status,'doc'+i,text,hashlib.sha256(text.encode()).hexdigest())

class TestCounterfactualPlanner(unittest.TestCase):
 def test_discriminating_gap_selected(self):
  graph=ProofGraph({'A':[['a','b']], 'B':[['c']]},[c('a','verified'),c('b'),c('c','verified')])
  r=graph.rank_gaps([ProofGap('b',1)])
  self.assertEqual(r[0]['edge_id'],'b')
 def test_eight_step_dependencies(self):
  ids=[f'e{i}' for i in range(8)]
  g=ProofGraph({'End':[ids],'Other':[['other']]},[c(i,'verified') for i in ids[:7]]+[c('e7'),c('other','verified')])
  self.assertEqual(g.act_or_abstain([ProofGap('e7',1)],3)['action'],'retrieve')
 def test_weak_source_does_not_validate(self):
  x=SourcedClaim('a','verified','doc','x','wrong hash')
  with self.assertRaises(ValueError):ProofGraph({'End':[['a']]},[x])
 def test_unsupported_source_dependency_skip(self):
  g=ProofGraph({'A':[['a','b']]},[c('a'),c('b')]);self.assertEqual(g.rank_gaps([ProofGap('b',1,('a',))]),[])
 def test_expensive_gap_abstains(self):
  g=ProofGraph({'A':[['a']]},[c('a')]);self.assertEqual(g.act_or_abstain([ProofGap('a',100)],1)['action'],'abstain')
 def test_no_oracle_trick(self):
  g=ProofGraph({'A':[['a']]},[c('a')]);_ = g.act_or_abstain([ProofGap('a',1)],1)
  self.assertEqual(g.claims['a'].status,'unknown')
 def test_supported_only_answer(self):
  g=ProofGraph({'A':[['a']]},[c('a','verified')]);self.assertEqual(g.act_or_abstain([],1)['action'],'answer')
if __name__=='__main__':unittest.main()