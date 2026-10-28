import unittest
from set_workspace_v95 import Workspace

class SetTests(unittest.TestCase):
    def setUp(self):
        self.docs={
          'movie':'Kalank was directed by Abhishek Varman and produced by Karan Johar.',
          'director':'Abhishek Varman is a director born in Mumbai.',
          'country':'Mumbai is a city in Maharashtra, India.',
          'distractor':'The producer, Karan Johar, discussed the film director on television.',
        }
        self.w=Workspace(self.docs)
    def test_partition_exhaustive(self):
        p=self.w.partition('all',r'\bdirected by\b','direction',anchor_tokens=['director'])
        self.assertTrue(p.complement_checked)
        self.assertEqual((p.positive_count,p.negative_count),(1,3))
        self.assertTrue(self.w.get('direction_yes').isdisjoint(self.w.get('direction_no')))
    def test_complement_and_warning(self):
        p=self.w.partition('all','directed by','direction',anchor_tokens=['director'])
        self.assertGreaterEqual(p.rejected_anchor_count,1)
        self.assertIn('distractor',self.w.get(p.negative))
    def test_span_validity(self):
        p=self.w.partition('all','Abhishek Varman','names')
        self.assertTrue(self.w.verify_matches(p.positive))
    def test_no_factual_entailment_claim(self):
        p=self.w.partition('all','Karan Johar','names')
        self.assertIn('movie',self.w.get(p.positive))
        self.assertIn('distractor',self.w.get(p.positive))
        self.assertEqual(len(self.w.get(p.positive)),2)
    def test_set_intersection(self):
        a=self.w.partition('all','Varman','a')
        b=self.w.partition('all','Mumbai','b')
        result=self.w.combine(a.positive,b.positive,'and','intersection')
        self.assertEqual(result,{'director'})
    def test_set_difference(self):
        a=self.w.partition('all','director','a')
        b=self.w.partition('all','television','b')
        c=self.w.combine(a.positive,b.positive,'minus','difference')
        self.assertNotIn('distractor',c)
    def test_source_scope(self):
        a=self.w.partition('all','director','a')
        b=self.w.partition(a.positive,'born','born')
        self.assertEqual(self.w.get(b.positive),{'director'})
    def test_preview_is_nonmutating(self):
        a=set(self.w.sets);old=len(self.w.history)
        p=self.w.preview_partition('all','born')
        self.assertEqual(p['matches'],1)
        self.assertEqual(set(self.w.sets),a)
        self.assertEqual(len(self.w.history),old)
    def test_invalid_operation(self):
        with self.assertRaises(ValueError):self.w.combine('all','all','X','bad')
    def test_immutable_set_name(self):
        with self.assertRaises(ValueError):self.w.partition('all','film','all')

if __name__=='__main__':unittest.main()