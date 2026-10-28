import unittest
from pger_v84_core import stable_union,full_pool,short_rerank_pool,sorted_ce,corpus_gate,context_rows
class V84Tests(unittest.TestCase):
 def setUp(self):
  self.docs=[{'_id':str(i),'title':'Place '+str(i),'text':'text '+str(i)} for i in range(150)]
  self.ids=[x['_id'] for x in self.docs]
 def test_pool_cap_preserves_fast(self):
  out,_=full_pool(list(range(100)),list(range(100)),list(range(100,150)),list(range(50,150)),[],[],self.ids,cap=120)
  self.assertEqual(out[:80],list(range(80)))
  self.assertEqual(len(out),120)
  self.assertEqual(len(out),len(set(out)))
 def test_crossencoder_protects(self):
  scores={i:float(150-i) for i in range(80)}
  out=sorted_ce([30,31,32],[30,31]+list(range(70)),scores,self.ids)
  self.assertEqual(out[:2],[30,31]);self.assertEqual(len(set(out)),len(out))
 def test_shortlist_is_bounded(self):
  pool,rrf=full_pool(list(range(100)),list(range(100)),list(range(50,150)),[],[],[],self.ids)
  r=short_rerank_pool(list(range(100)),pool,rrf,self.docs,'where was place 9',cap=64)
  self.assertEqual(r[:2],[0,1]);self.assertEqual(len(r),64)
 def test_morehop_sequence_dict(self):
  row={'context':{'title':['Alpha','Beta'],'paragraphs':[['a'],['b']]},'question_decomposition':{'paragraph_support_title':['Alpha','Beta','Absent']}}
  p,g=context_rows(row);self.assertEqual(len(p),2);self.assertEqual(g,{'alpha','beta'})
 def test_gate_corpus_not_gold(self):
  class Fake:
   docs=[{'title':'alpha beta'}]
  self.assertEqual(corpus_gate('any complex question', [0],Fake(),0.2),'fast')
 def test_stable_union(self):self.assertEqual(stable_union([0,1],[1,2]),[0,1,2])
if __name__=='__main__':unittest.main()