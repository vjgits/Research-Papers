import pathlib,sys,unittest
import numpy as np
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from benchmark_v6 import Retriever
from benchmark_v63 import EvidenceSystem
class Encoder:
 def encode(self,items,**kwargs):
  return np.asarray([[1.,0.,0.] for _ in items],dtype=np.float32)
class Critic:
 def predict(self,pairs,**kwargs):
  return np.asarray([0.1]*len(pairs),dtype=np.float32)
class ZeroLexicalTest(unittest.TestCase):
 def test_no_bm25_hit_and_dense_available(self):
  d=[{"_id":"a","title":"alpha research","text":"alpha research background"},
     {"_id":"b","title":"gamma project","text":"gamma project results"},
     {"_id":"c","title":"biology cells","text":"biology cells adapt"}]
  s=EvidenceSystem.__new__(EvidenceSystem)
  s.docs=d
  s.docs_by_id=[x["title"]+" "+x["text"] for x in d]
  s.bm=Retriever(d)
  s.embedder=Encoder()
  s.crossencoder=Critic()
  s.dense=np.asarray([[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]],dtype=np.float32)
  result,diag=s.evaluate_one("xyznotincorpus")
  self.assertEqual(result["bm25"],[])
  self.assertTrue(len(result["dense"])>0)
  self.assertTrue(len(result["union_blind"])>0)
if __name__=="__main__": unittest.main()
