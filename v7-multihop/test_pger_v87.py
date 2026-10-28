import unittest
from pger_v87_core import *
class Tests(unittest.TestCase):
 def setUp(self):
  self.doc=normalize_doc({'title':'Film','sents':[['Film','was','directed','by','Ana','.'],['Film','was','produced','by','Bob','.']], 'vertexSet':[[{'name':'Film','sent_id':0},{'name':'Film','sent_id':1}],[{'name':'Ana','sent_id':0}],[{'name':'Bob','sent_id':1}]], 'labels':[{'h':0,'t':1,'r':'P57','evidence':[0]}]})
 def test_schema(self):
  self.assertEqual(self.doc['labels'][0]['r'],'P57'); self.assertEqual(len(self.doc['sents']),2)
 def test_dict_label_format(self):
  doc=normalize_doc({'sents':[[]],'vertexSet':[],'labels':{'head':[0],'tail':[1],'relation_id':['P57'],'evidence':[[0]]}})
  self.assertEqual(doc['labels'][0]['r'],'P57')
 def test_source_offsets(self):
  a=evidence_windows(self.doc,0,1);self.assertEqual(a[0]['sentence_ids'],[0]);self.assertEqual(a[0]['premise'],self.doc['sents'][0])
 def test_no_evidence_label_used(self):
  a=evidence_windows(self.doc,0,1)
  self.doc['labels'][0]['evidence']=[1]
  b=evidence_windows(self.doc,0,1)
  self.assertEqual(a,b)
 def test_no_relation_leakage(self):
  def fake(ps):return [[0.,2.,0.]]*len(ps)
  a=evaluate_one(self.doc,0,1,fake)
  self.doc['labels'][0]['r']='P20'
  b=evaluate_one(self.doc,0,1,fake)
  self.assertEqual(a,b)
 def test_abstention(self):
  ws=[{'premise':'text','sentence_ids':[0]}]
  x=predict_nli([('P57',0,[2.,0.,0.])],ws)
  self.assertIsNone(x['predicted'])
if __name__=='__main__':unittest.main()