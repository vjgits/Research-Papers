import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from benchmark_v7 import rrf,chain_scores,make_corpus,DATA_URL,SEED
class TestV7(unittest.TestCase):
 def test_complete(self):
  x,y=chain_scores([0,1,2],{"a","b"},["a","b","c"])
  self.assertEqual(x["chain_at_2"],1)
 def test_partial(self):
  x,y=chain_scores([0,2,1],{"a","b"},["a","b","c"])
  self.assertEqual(x["chain_at_2"],0)
  self.assertEqual(y["evidence_recall_at_2"],0.5)
 def test_rrf_contains(self):
  x=rrf([0,1],[1,2],["a","b","c"])
  self.assertEqual(set(x),{0,1,2})
 def test_docs_gold_independent(self):
  r=[{"context":{"title":["A","B"],"sentences":[["A is a country."],["B is a lake."]]},
      "supporting_facts":{"title":["A"],"sent_id":[0]}}]
  d=make_corpus(r)
  self.assertEqual(len(d),2)
  self.assertEqual({x["_id"] for x in d},{"a","b"})
 def test_dataset_exact(self):
  self.assertIn("2WikiMultihopQA",DATA_URL)
 def test_no_reference_in_ranker(self):
  import ast
  src=(pathlib.Path(__file__).resolve().parents[1]/"benchmark_v7.py").read_text()
  tree=ast.parse(src)
  cls=[x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=="Methods"][0]
  for fn in cls.body:
   if isinstance(fn,ast.FunctionDef):
    refs={x.id for x in ast.walk(fn) if isinstance(x,ast.Name)}
    self.assertNotIn("gold",refs);self.assertNotIn("supporting_facts",refs)
 def test_not_ircot_replication(self):
  s=(pathlib.Path(__file__).resolve().parents[1]/"benchmark_v7.py").read_text()
  self.assertIn('"no_ircot_or_hipporag2_replication":True',s)
if __name__=="__main__":unittest.main()
