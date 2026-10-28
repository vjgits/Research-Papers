import unittest
from pger_v89_core import parse_rebel, classify_output, accepted,verify_quote,RELATION_MAP,anchored
class TestREBELAdapter(unittest.TestCase):
 def test_parser(self):
  s='<s> <triplet> Kalank <subj> Abhishek Varman <obj> director </s>'
  self.assertEqual(parse_rebel(s),[('Kalank','director','Abhishek Varman')])
 def test_multiple(self):
  s='<triplet> Paris <subj> France <obj> country <triplet> Ana <subj> Bob <obj> spouse'
  self.assertEqual(len(parse_rebel(s)),2)
 def test_empty(self):self.assertEqual(parse_rebel('<s></s>'),[])
 def test_invalid_relation_not_mapped(self):
  self.assertIsNone(classify_output('<triplet> A <subj> B <obj> unknown','A and B',0)[0]['r'])
 def test_surface_anchor(self):
  self.assertFalse(anchored('Kalank was produced by Karan Johar.','Kalank','Abhishek Varman'))
  self.assertTrue(anchored('Kalank was directed by Abhishek Varman.','Kalank','Abhishek Varman'))
 def test_source_hash(self):
  x=classify_output('<triplet> Kalank <subj> Abhishek Varman <obj> director','Kalank was directed by Abhishek Varman.',3)[0]
  sents=['x']*3+['Kalank was directed by Abhishek Varman.']
  self.assertTrue(verify_quote(x,sents));self.assertFalse(verify_quote(x,sents[:-1]+['different']))
  self.assertEqual(len(accepted([x])),1)
if __name__=='__main__':unittest.main()