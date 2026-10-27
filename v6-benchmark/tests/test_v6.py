import unittest
import pathlib
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from benchmark_v6 import Retriever,measures,partition,proofgap,SETS

D=[{"_id":"a","title":"Climate","text":"Atmospheric temperatures are measured globally."},
   {"_id":"b","title":"Astronomy","text":"Stellar light reaches the earth from stars."},
   {"_id":"c","title":"Economics","text":"Fiscal revenue is measured in budgets."}]
class TestV6(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=Retriever(D)
    def test_deterministic_split(self):self.assertEqual(partition("scifact","id"),partition("scifact","id"))
    def test_two_partitions(self):self.assertEqual({partition("scifact",str(i)) for i in range(100)},{"dev","sealed"})
    def test_dataset_is_part_of_key(self):self.assertTrue(any(partition("scifact",str(i))!=partition("nfcorpus",str(i)) for i in range(100)))
    def test_bm25(self):self.assertEqual(self.r.search("fiscal revenue","bm25")[0][0],2)
    def test_tfidf(self):self.assertEqual(self.r.search("stellar light","tfidf")[0][0],1)
    def test_proofgap(self):
        got,calls=proofgap(self.r,"revenue budgets")
        self.assertEqual(got[0],2);self.assertIn(calls,(1,2))
    def test_ndcg(self):self.assertAlmostEqual(measures(["a"],{"a":2})["ndcg10"],1)
    def test_recall(self):self.assertAlmostEqual(measures(["a","b"],{"a":1,"b":1})["recall10"],1)
    def test_no_relevant(self):self.assertEqual(measures(["b"],{"a":1})["recall10"],0)
    def test_not_score_sealed(self):
        # Public runner accepts only smoke/dev, and main loop explicitly selects dev.
        source=(pathlib.Path(__file__).resolve().parents[1]/"benchmark_v6.py").read_text()
        self.assertIn('partition(name,q)=="dev"',source)
        self.assertNotIn('choices=["smoke","dev","sealed"]',source)
    def test_dataset_set(self):self.assertIn("scifact",SETS);self.assertIn("nfcorpus",SETS)

if __name__=="__main__":unittest.main()
