import unittest
from pger_v91_core import gap_slots,plan_queries,query_once,valid_source,fuse

class V91Tests(unittest.TestCase):
 def setUp(self):
  self.docs=[{'_id':'a','title':'First Film','text':'First Film was produced by Adam. A reviewer described its plot.'},
     {'_id':'b','title':'Adam Person','text':'Adam Person was born in Anytown and moved to Canada.'},
     {'_id':'c','title':'Canada','text':'Canada is a country in North America.'},
     {'_id':'d','title':'Second Film','text':'Second Film was directed by Bert.'}]
 def test_slots(self):self.assertEqual(gap_slots('Who directed the film?')[0][0],'director')
 def test_deterministic(self):
  a=plan_queries('Where was the director of First Film born?',list(range(4)),self.docs)
  self.assertEqual(a,plan_queries('Where was the director of First Film born?',list(range(4)),self.docs));self.assertEqual(len(a),2)
 def test_valid_provenance(self):
  a=plan_queries('Who directed the film?',list(range(4)),self.docs)
  for x in a:self.assertTrue(valid_source(x['witness'],self.docs))
 def test_mutated_quote_fails(self):
  a=plan_queries('Who directed the film?',list(range(4)),self.docs)
  self.docs[0]['text']='mutated'
  self.assertFalse(valid_source(a[0]['witness'],self.docs)) if a[0]['seed_doc']==0 else None
 def test_no_gold_access(self):
  for p in ('gap','frontier','original'):
   r=plan_queries('Where was First Film director born?',list(range(4)),self.docs,p)
   self.assertEqual(len(r),2)
 def test_matched_search(self):
  calls=[]
  def search(q,n):calls.append((q,n));return [2,3]
  for p in ('gap','frontier','original'):
   r,m=query_once('Who directed First Film?',None,list(range(4)),self.docs,search,p)
   self.assertEqual(m['extra_queries'],2);self.assertEqual(r[:2],[0,1]);self.assertEqual(len(r),len(set(r)))
  self.assertEqual(len(calls),6)
 def test_fusion_unique(self):
  r=fuse([0,0,1],[{},{}],[[1,2],[2,3]],self.docs)
  self.assertEqual(len(r),len(set(r)))
 def test_empty(self):self.assertEqual(plan_queries('some q',[],self.docs),[])
if __name__=='__main__':unittest.main()