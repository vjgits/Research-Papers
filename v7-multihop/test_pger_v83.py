import unittest
from pger_v8_core import EvidenceMap
from pger_v83_core import TitleAnchors,select_guarded_chain

class SourceBridgeTests(unittest.TestCase):
 def setUp(self):
  self.docs=[
   {'_id':'film_a','title':'Film Alpha Example','text':'Film Alpha Example was directed by Director Carol Example.'},
   {'_id':'film_b','title':'Film Bravo Example','text':'Film Bravo Example was directed by Director David Example.'},
   {'_id':'director_c','title':'Director Carol Example','text':'Director Carol Example was born in 1950.'},
   {'_id':'director_d','title':'Director David Example','text':'Director David Example was born in 1960.'},
   {'_id':'distractor','title':'Different Film Example','text':'An unrelated distractor.'}]
  self.graph=EvidenceMap(self.docs);self.index=TitleAnchors(self.docs)
 def test_two_provenance_bridges(self):
  q='Which film has the director born earlier, Film Alpha Example or Film Bravo Example?'
  rank,meta=select_guarded_chain(q,[4,0,1,2,3],self.graph,self.index)
  self.assertTrue(meta['activated'])
  self.assertTrue({0,1,2,3}<=set(rank[:5]))
  self.assertTrue(all(self.graph.claims.valid(c) for c in self.graph.claims.claims))
 def test_easy_unchanged(self):
  fast=[0,2,4,1,3]
  rank,meta=select_guarded_chain('Who directed Film Alpha Example?',fast,self.graph,self.index)
  self.assertEqual(fast,rank);self.assertFalse(meta['activated'])
 def test_unproven_relation_unchanged(self):
  fast=[0,4,1,2,3]
  q='Which is older, Film Alpha Example or Different Film Example, by director?'
  rank,meta=select_guarded_chain(q,fast,self.graph,self.index)
  self.assertFalse(meta['activated']);self.assertEqual(rank,fast)
if __name__=='__main__':unittest.main()
