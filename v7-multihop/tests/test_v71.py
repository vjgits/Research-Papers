import ast, pathlib, sys, unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from benchmark_v71 import EvidenceLedger, phrases, load_2wiki_second_sample, HOPS, BEAM, FANOUT
from benchmark_v6 import Retriever

DOCS=[
 {"_id":"a","title":"Alpha University","text":"Alpha University lists Beta College as partner."},
 {"_id":"b","title":"Beta College","text":"Beta College is associated with Gamma Institute."},
 {"_id":"c","title":"Gamma Institute","text":"Gamma Institute mentions Delta Museum."},
 {"_id":"d","title":"Delta Museum","text":"Delta Museum preserves old records."},
 {"_id":"e","title":"Extra Database","text":"Unrelated inventory and postal codes."},
 {"_id":"f","title":"Other Location","text":"This other location is a place."},
]
class FakeMethods:
 def __init__(self):
  self.docs=DOCS
  self.index=Retriever(DOCS)
  self.ids=self.index.ids

class TestLedger(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.m=FakeMethods()
  cls.g=EvidenceLedger(cls.m)
 def test_aho_graph_links(self):
  adj,details=phrases(self.m.index,DOCS)
  self.assertIn(1,adj[0])
  self.assertIn(2,adj[1])
  self.assertIn(3,adj[2])
 def test_aho_boundary(self):
  fake=[{"_id":"x","title":"Delta Museum","text":"nothing"},
        {"_id":"y","title":"Archive","text":"The Delta Museums are not the same exact title."}]
  idx=Retriever(fake)
  edges,_=phrases(idx,fake)
  self.assertNotIn(0,edges[1])
 def test_ledger_vs_reset_same_base(self):
  query="alpha university gamma institute old records"
  base=[i for i,_ in self.m.index.search(query,"bm25",100)]
  for mode in ["ledger","reset"]:
   pred,cost=self.g.search(query,base,mode)
   self.assertEqual(pred[0],base[0])
   self.assertEqual(len(pred),len(set(pred)))
   self.assertLessEqual(cost["depth"],HOPS)
   self.assertGreaterEqual(cost["expanded"],0)
 def test_onehop_maxdepth(self):
  base=list(range(len(DOCS)))
  pred,meta=self.g.search("alpha university gamma institute",base,mode="one-hop")
  self.assertLessEqual(meta["depth"],1)
 def test_no_ground_truth_decision(self):
  text=(pathlib.Path(__file__).resolve().parents[1]/"benchmark_v71.py").read_text()
  tree=ast.parse(text)
  f=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=="EvidenceLedger")
  for node in f.body:
   if isinstance(node,ast.FunctionDef):
    symbols={x.id for x in ast.walk(node) if isinstance(x,ast.Name)}
    for name in ["gold","qrels","supporting_facts","is_supporting"]:
     self.assertNotIn(name,symbols)
 def test_no_reviewer_apis(self):
  text=(pathlib.Path(__file__).resolve().parents[1]/"benchmark_v71.py").read_text()
  self.assertNotIn("CrossEncoder",text)
  self.assertNotIn("OPENAI_API_KEY",text)
 def test_same_beam_fanout(self):
  self.assertEqual(BEAM,8)
  self.assertEqual(FANOUT,8)
if __name__=="__main__":unittest.main()
