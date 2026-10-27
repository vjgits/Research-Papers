import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from benchmark_v6 import Retriever,partition
from benchmark_v62 import Controller,inner_part,question_features,scores,candidate_actions,proposed_followup

DATA=[
{"_id":"climate","title":"Climate measurements","text":"Global climate measurements involve temperature and atmospheric carbon."},
{"_id":"soil","title":"Soil and plants","text":"Agricultural soil quality affects plants and yield."},
{"_id":"astronomy","title":"Stellar radiance","text":"Stellar radiance is measured in astronomy."},
{"_id":"history","title":"Historical archive","text":"The archival documents include dates and records."},
{"_id":"medicine","title":"Nutrition health","text":"Clinical studies measure health and medical nutrition."},
{"_id":"finance","title":"Financial figures","text":"Financial annual returns depend on investment rate."}
]
class TestsV62(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.idx=Retriever(DATA)
 def test_partition_determinism(self):self.assertEqual(inner_part("scifact","x"),inner_part("scifact","x"))
 def test_two_inner_splits(self):self.assertEqual(set(inner_part("scifact",str(i)) for i in range(100)),{"fit","validate"})
 def test_not_sealed(self):
  source=(pathlib.Path(__file__).resolve().parents[1]/"benchmark_v62.py").read_text()
  self.assertIn('partition(name,q)=="dev"',source)
  self.assertIn('inner_part(name,q)=="fit"',source)
  self.assertIn('inner_part(name,q)=="validate"',source)
 def test_action_feature_shape(self):
  q="climate carbon atmospheric temperature";base=self.idx.search(q,"bm25")
  self.assertEqual(len(question_features(self.idx,q,base)),11)
 def test_controller_fallback_without_training(self):
  c=Controller()
  q="clinical studies nutrition medical"
  expected=[i for i,_ in self.idx.search(q,"bm25")]
  got,info=c.run(self.idx,q)
  self.assertEqual(expected,got);self.assertEqual(info["calls"],1)
 def test_no_answer_labels_in_decision(self):
  s=(pathlib.Path(__file__).resolve().parents[1]/"benchmark_v62.py").read_text()
  ctrl=s.split("class Controller:",1)[1].split("def evaluate(",1)[0]
  decision=ctrl.split("def run(",1)[1]
  for forbidden in ["qrels","reference_answer","measures(","ground_truth","gold"]:
    self.assertNotIn(forbidden,decision)
 def test_repeatable_followup(self):
  q="global climate and agricultural yield"
  b=self.idx.search(q,"bm25")
  self.assertEqual(proposed_followup(self.idx,q,b),proposed_followup(self.idx,q,b))
 def test_candidates_preserve_top1(self):
  q="climate temperature yield"
  b=self.idx.search(q,"bm25")
  second=self.idx.search("yield agricultural soil","bm25")
  for action in candidate_actions(self.idx,q,b,second):
   self.assertEqual(action["proposal"][0],b[0][0])
   self.assertEqual(len(action["proposal"]),len(set(action["proposal"])))
if __name__=="__main__":unittest.main()
