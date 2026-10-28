import unittest
from benchmark_v94 import MODEL,ranked
class V94ModelAblationTests(unittest.TestCase):
 def test_frozen_ettin(self):self.assertEqual(MODEL,'cross-encoder/ettin-reranker-17m-v1')
 def test_protect(self):self.assertEqual(ranked([3,2],{3:0,2:2},[3,2],protect=1),[3,2])
if __name__=='__main__':unittest.main()
