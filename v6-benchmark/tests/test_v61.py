import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from benchmark_v6 import Retriever
from benchmark_v61 import guarded,evidence_gap,SEARCH_THRESHOLD

DATA=[
 {"_id":"a","title":"economic production","text":"World production of steel increased in 2018."},
 {"_id":"b","title":"economic output","text":"Steel production increased in 2019 in selected countries."},
 {"_id":"c","title":"temperature monitoring","text":"Temperatures varied across the 2017 research experiment."},
 {"_id":"d","title":"medical measurements","text":"Medical evidence from experiment on nutrition and metabolism."},
 {"_id":"e","title":"unrelated","text":"The blue star was seen in a distant galaxy."}
]
class V61Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.model=Retriever(DATA)
 def test_short_query_no_search(self):
    q="steel production"
    rank=[i for i,_ in self.model.search(q,"bm25")]
    pred,diag=guarded(self.model,q)
    self.assertEqual(pred,rank)
    self.assertEqual(diag["calls"],1)
 def test_preserve_original_head(self):
    for q in ["steel output experiment","global nutrition metabolism","evidence temperature experiment 2017","economic steel and countries"]:
        base=[i for i,_ in self.model.search(q,"bm25")]
        pred,diag=guarded(self.model,q)
        self.assertEqual(pred[:2],base[:2])
 def test_no_duplications(self):
    for q in ["steel economic 2019 nutrition","metabolism increased production"]:
        pred,diag=guarded(self.model,q)
        self.assertEqual(len(pred),len(set(pred)))
 def test_gap_range(self):
    base=self.model.search("temperature steel study","bm25")
    gap,missing,present,margin=evidence_gap(self.model,"temperature steel study",base)
    self.assertTrue(0<=gap<=1.00001)
    self.assertTrue(0<=margin<=1.00001)
 def test_repeatable(self):
    q="steel production and experiment"
    p1,i1=guarded(self.model,q);p2,i2=guarded(self.model,q)
    self.assertEqual(p1,p2)
    self.assertEqual(i1,i2)
 def test_no_reference_labels(self):
    source=(pathlib.Path(__file__).resolve().parents[1]/"benchmark_v61.py").read_text()
    main=source.split("def guarded(",1)[1].split("def eval_dev(",1)[0]
    for forbidden in ["qrels","gold","relevance_judgments","reference_answer"]:
       self.assertNotIn(forbidden,main)
 def test_split_dev_only(self):
    source=(pathlib.Path(__file__).resolve().parents[1]/"benchmark_v61.py").read_text()
    self.assertIn('partition(name,qid)=="dev"',source)
    self.assertIn('choices=["smoke","dev"]',source)
if __name__=="__main__":unittest.main()
