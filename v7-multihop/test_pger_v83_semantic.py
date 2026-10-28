import unittest
from pger_v8_core import EvidenceMap
from pger_v83_semantic import fixed_pools,predict_union,rank_with_scores,cheap_gate

class V83SemanticTests(unittest.TestCase):
    def setUp(self):
        self.docs=[{'_id':'a','title':'Alpha Film','text':'Alpha Film was directed by Beta Person.'},
                   {'_id':'b','title':'Beta Person','text':'Beta Person was born in Gamma Town.'},
                   {'_id':'c','title':'Gamma Town','text':'Gamma Town is located in Delta Country.'},
                   {'_id':'d','title':'Delta Country','text':'Delta Country lies in mountains.'},
                   {'_id':'e','title':'Noise Page','text':'Noise is merely noise.'}]
        self.em=EvidenceMap(self.docs)
    def test_shared_scores_once_and_same_pool(self):
        fast=list(range(5));f,r=fixed_pools('Where was Alpha Film director born?',fast,fast,set(fast),self.em)
        called=[]
        def model(pairs):
            called.append(len(pairs));return [float(i)/10 for i in range(len(pairs))]
        scores,n=predict_union('Where was Alpha Film director born?',f,r,self.docs,model)
        self.assertEqual(called,[n]);self.assertEqual(n,len(set(f+r)))
        self.assertTrue(set(f+r)<=set(scores))
    def test_guarded_preserves_two_strong_anchors(self):
        fast=[0,1,2,3,4];scores={i:float(i)/4 for i in fast}
        a,_=rank_with_scores(fast,fast,scores,self.em,'protected')
        self.assertEqual(a[:2],[0,1]);self.assertEqual(len(set(a)),len(a))
        b,_=rank_with_scores(fast,fast,scores,self.em,'plain')
        self.assertEqual(b[0],4)
    def test_sourced_edge_trace_checks_exact_offsets(self):
        fast=[0,1,2,3,4];scores={i:0.5 for i in fast}
        _,edges=rank_with_scores(fast,fast,scores,self.em,'sourced')
        for edge in edges:
            self.assertTrue(edge['asserted'])
            d=next(d for d in self.docs if d['_id']==edge['source_id'])
            self.assertEqual(d['text'][edge['start']:edge['end']],edge['quote'])
    def test_easy_gate_never_assumes_answer_proved(self):
        fast=list(range(5))
        self.assertTrue(cheap_gate('Alpha Film',fast,self.em))
        self.assertFalse(cheap_gate('Which of Alpha Film and Beta Person was born earlier?',fast,self.em))
    def test_source_corruption_raises_verification_failure(self):
        c=next(c for c in self.em.claims.claims if c.source==0)
        self.assertTrue(self.em.claims.valid(c))
        self.docs[0]['text']='source changed'
        self.assertFalse(self.em.claims.valid(c))
if __name__=='__main__':unittest.main()