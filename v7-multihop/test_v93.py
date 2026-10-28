import unittest,numpy as np
from benchmark_v93 import ranked,score,fresh_candidates
class DummyCE:
 def predict(self,pairs,**kwargs):return np.arange(len(pairs),dtype=float)
class DummyEngine:
 def __init__(self):
  self.index=self
  self.idfs={'beta':3,'town':2,'born':2,'gamma':2,'alpha':2}
 def search(self,q,mode,n):
  return [(i,1.) for i in range(min(n,5))]
class SemanticStageTests(unittest.TestCase):
 def test_anchor(self):self.assertEqual(ranked([4,1,3],{1:3,4:0,3:1},[4,1,3],2)[:2],[4,1])
 def test_score_budget(self):
  docs=[{'title':str(i),'text':'Doc source'} for i in range(3)]
  vals,t=score(DummyCE(),'question',docs,[0,2])
  self.assertEqual(set(vals),{0,2})
 def test_no_gold_in_candidate_api(self):
  docs=[{'title':'Alpha','text':'Alpha was born in Beta Town.'},
        {'title':'Beta Town','text':'Beta Town is in Gamma County.'},
        {'title':'Gamma County','text':'Some other information.'},
        {'title':'D','text':'D is unrelated.'},
        {'title':'E','text':'E is unrelated.'}]
  picks,trace=fresh_candidates('Where was Alpha born?',docs,[0,1,2,3,4],[0,1,2,3,4],DummyEngine(),[0],{0},2)
  self.assertTrue(all(i!=0 for i in picks))
  self.assertLessEqual(len(picks),2)
  self.assertTrue(all('quote' in x for x in trace))
if __name__=='__main__':unittest.main()
