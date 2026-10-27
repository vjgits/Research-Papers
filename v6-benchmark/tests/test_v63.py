import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from benchmark_v6 import Retriever,partition
from benchmark_v62 import inner_part
from benchmark_v63 import context_review, sigmoid, stable_rank, load_dev_only, weighted_coverage

D=[{"_id":"a","title":"Climatology","text":"Atmospheric studies test temperature and humidity."},
   {"_id":"b","title":"Agronomy","text":"Plants use carbon through photosynthesis."},
   {"_id":"c","title":"Economics","text":"Revenue and annual spending indicate profit."}]
class V63Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.idx=Retriever(D)
 def test_context_score_nonnegative(self):
  q="atmospheric temperature humidity"
  ids=[x for x,_ in self.idx.search(q,"bm25")]
  d=context_review(self.idx,q,ids,ids[0])
  self.assertTrue(all(v>=0 for v in d.values()))
 def test_context_keys(self):
  q="photosynthesis and humidity"
  ids=[x for x,_ in self.idx.search(q,"bm25")]
  self.assertEqual(set(context_review(self.idx,q,ids,ids[0])),{"gap","coverage","fills","novelty","support"})
 def test_logits(self):
  self.assertLess(sigmoid(-7),sigmoid(0));self.assertLess(sigmoid(0),sigmoid(7))
 def test_rank(self):
  self.assertEqual(stable_rank([0.1,0.4,0.2],["a","b","c"])[0],1)
 def test_no_benchmark_answers_for_reviewers(self):
  import ast
  source=(pathlib.Path(__file__).resolve().parents[1]/"benchmark_v63.py").read_text()
  tree=ast.parse(source)
  check=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and
         n.name in ("context_review","evaluate_one")]
  self.assertEqual(len(check),2)
  for fn in check:
   refs={n.id for n in ast.walk(fn) if isinstance(n,ast.Name)}
   for forbidden in ["qrels","reference_answer","measures","gold","ground_truth"]:
    self.assertNotIn(forbidden,refs)
 def test_qrels_filter(self):
  source=(pathlib.Path(__file__).resolve().parents[1]/"benchmark_v63.py").read_text()
  self.assertIn('partition(dataset,q["_id"])=="dev"',source)
  self.assertIn("if qid in queries and int(grade)>0",source)
 def test_inner_validation_filter(self):
  source=(pathlib.Path(__file__).resolve().parents[1]/"benchmark_v63.py").read_text()
  self.assertIn('inner_part(name,qid)=="validate"',source)
 def test_zero_api_budget(self):
  source=(pathlib.Path(__file__).resolve().parents[1]/"benchmark_v63.py").read_text()
  self.assertNotIn("OPENAI_API_KEY",source)
  self.assertNotIn("ANTHROPIC_API_KEY",source)
if __name__=="__main__":unittest.main()
