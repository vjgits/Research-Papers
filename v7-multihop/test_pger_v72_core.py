import unittest
from pger_v72_core import ClaimIndex,make_shared_candidates,rank_with_claims,should_expand

class EvidenceTests(unittest.TestCase):
 def setUp(self):
  self.docs=[
   {'_id':'A','title':'Alpha Person','text':'Alpha Person was born in Beta Valley. Alpha Person directed Gamma Movie.'},
   {'_id':'B','title':'Beta Valley','text':'Beta Valley is located in Delta Country.'},
   {'_id':'C','title':'Gamma Movie','text':'Gamma Movie was written by Epsilon Writer.'},
   {'_id':'D','title':'Delta Country','text':'Delta Country has mountains.'},
   {'_id':'E','title':'Epsilon Writer','text':'Epsilon Writer is a playwright.'}]
  self.idx=ClaimIndex(self.docs)
 def test_offline_provenance(self):
  self.assertTrue(self.idx.claims)
  self.assertTrue(all(self.idx.valid(c) for c in self.idx.claims))
  self.assertIn(1,[c.target for c in self.idx.links[0]])
  self.assertIn(3,[c.target for c in self.idx.links[1]])
 def test_modified_source_invalid(self):
  c=self.idx.links[0][0];self.docs[0]['text']='changed'
  self.assertFalse(self.idx.valid(c))
 def test_claim_is_not_free_fact(self):
  self.assertTrue(any(c.asserted for c in self.idx.links[0]))
  self.assertTrue(any(c.predicate=='association' or c.asserted for c in self.idx.claims))
 def test_candidate_pool_common_and_rank_reproducible(self):
  calls=[]
  def search(q,n):calls.append(q);return [2,3,4]
  bm=[0,1,2,3,4]
  pool,meta=make_shared_candidates('Which country was Alpha Person born in?',self.docs,bm,bm,self.idx,search)
  a,sa=rank_with_claims('Which country was Alpha Person born in?',self.docs,bm,bm,self.idx,pool,False)
  b,sb=rank_with_claims('Which country was Alpha Person born in?',self.docs,bm,bm,self.idx,pool,True)
  self.assertEqual(len(meta),len(calls));self.assertEqual(set(a),set(b));self.assertEqual(a[0],b[0])
  self.assertEqual(a,rank_with_claims('Which country was Alpha Person born in?',self.docs,bm,bm,self.idx,pool,False)[0])
 def test_easy_gate(self):
  self.assertFalse(should_expand('Alpha Person',self.docs,[0]))
 def test_no_spans_without_evidence(self):
  self.assertEqual(self.idx.contradictions(),{})

if __name__=='__main__':unittest.main()
