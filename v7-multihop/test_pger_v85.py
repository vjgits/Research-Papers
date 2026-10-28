import unittest
from types import SimpleNamespace
from pger_v85_chain import deterministic_shortlist,ce_plain,connected_beam,early_gate,graph_evidence
from pger_v8_core import EvidenceMap
class V85Tests(unittest.TestCase):
 def setUp(self):
  self.docs=[{'_id':'a','title':'Alpha Person','text':'Alpha Person was born in Beta Valley.'},
   {'_id':'b','title':'Beta Valley','text':'Beta Valley is located in Gamma State.'},
   {'_id':'c','title':'Gamma State','text':'Gamma State has valleys.'}]
  self.e=EvidenceMap(self.docs)
 def test_source_offsets(self):
  edges=graph_evidence([0,1,2],self.e)
  self.assertTrue(all(self.e.claims.valid(c) for x in edges.values() for c in x))
 def test_same_budget(self):
  fast=[0,1,2];scores={0:0.5,1:0.6,2:0.9};ids=['a','b','c']
  a=ce_plain(fast,[0,1,2],scores,ids)
  b,traces=connected_beam(fast,[0,1,2],scores,ids,self.docs,self.e,'Where was Alpha Person born?',width=2)
  self.assertEqual(set(a),set(b));self.assertEqual(len(b),len(set(b)))
  self.assertTrue(all(t['heuristic_only'] for t in traces))
 def test_shortlists_nested_and_deterministic(self):
  docs=[{'_id':str(i),'title':f'Title {i}','text':''} for i in range(130)]
  ids=list(range(130));rrf={i:1/(i+40) for i in ids}
  p32=deterministic_shortlist(ids,ids,rrf,docs,'Title 1',32)
  p64=deterministic_shortlist(ids,ids,rrf,docs,'Title 1',64)
  p96=deterministic_shortlist(ids,ids,rrf,docs,'Title 1',96)
  self.assertEqual(p32,p64[:32]);self.assertEqual(p64,p96[:64])
 def test_gate_does_not_use_dataset(self):
  self.assertTrue(early_gate('Where is Beta Valley?', [1,0],self.docs))
  self.assertFalse(early_gate('Which of Alpha Person and Beta Valley was born earlier?', [0,1],self.docs))
 def test_invalid_span_ignored(self):
  self.docs[0]['text']='corrupted'
  self.assertFalse(any(c.source==0 for claims in graph_evidence([0,1,2],self.e).values() for c in claims))
if __name__=='__main__':unittest.main()