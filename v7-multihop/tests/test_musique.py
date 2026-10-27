import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from benchmark_musique import id_of,pool_documents
class TestMuSiQue(unittest.TestCase):
 def test_id_stable(self):
  p={"title":"A","paragraph_text":"A describes B."}
  self.assertEqual(id_of(p),id_of(dict(p)))
 def test_text_changes_id(self):
  a={"title":"A","paragraph_text":"A describes B."}
  b={"title":"A","paragraph_text":"A describes C."}
  self.assertNotEqual(id_of(a),id_of(b))
 def test_gold_not_used_for_pool(self):
  a={"title":"A","paragraph_text":"A describes B.","is_supporting":True}
  b={"title":"B","paragraph_text":"B describes A.","is_supporting":False}
  rows=[{"paragraphs":[a,b]}]
  self.assertEqual(len(pool_documents(rows)),2)
  c=[dict(x,is_supporting=not x["is_supporting"]) for x in [a,b]]
  self.assertEqual(pool_documents(rows),pool_documents([{"paragraphs":c}]))
if __name__=="__main__":unittest.main()
