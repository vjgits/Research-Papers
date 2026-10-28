import unittest
from pger_v90_core import select_fixed_first,select_lexical,select_coverage,selected_ids
from pger_v89_core import classify_output,accepted,verify_quote
class SelectionTests(unittest.TestCase):
 def setUp(self):
  self.sent=[(0,'A simple ordinary sentence about values and items.'),
   (1,'Kalank was directed by Abhishek Varman and produced by Karan Johar.'),
   (2,'A different generic sentence without names.'),
   (3,'Aster Film was written by Bobby Stone.')]
 def test_first(self):self.assertEqual(select_fixed_first(self.sent,2),[0,1])
 def test_no_gold_label_inputs(self):
  self.assertEqual(len(select_coverage(self.sent,3)),3)
  self.assertEqual(len(set(select_coverage(self.sent,3))),3)
 def test_determinism(self):
  self.assertEqual(select_coverage(self.sent,2),select_coverage(self.sent,2))
 def test_enumeration(self):
  for key in ('first2','lexical2','coverage2','coverage3','full6'):
   k=selected_ids(self.sent,key);self.assertEqual(len(k),6 if False else (3 if key=='coverage3' else 4 if key=='full6' else 2))
 def test_no_unsupported_method(self):
  with self.assertRaises(ValueError):selected_ids(self.sent,'magic')
 def test_source_integrity(self):
  text=self.sent[1][1];x=classify_output('<triplet> Kalank <subj> Karan Johar <obj> director',text,1)
  self.assertTrue(verify_quote(x[0],[self.sent[0][1],text]))
 def test_anchoring_not_truth(self):
  text=self.sent[1][1];x=classify_output('<triplet> Kalank <subj> Karan Johar <obj> director',text,1)
  # Both strings appear, but the director relation is false: anchoring cannot verify semantic truth.
  self.assertEqual(len(accepted(x)),1)
if __name__=='__main__':unittest.main()