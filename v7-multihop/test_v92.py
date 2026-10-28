import unittest
from expansion_v92 import terms,propose,rank_fuse
class SourceExpansionTests(unittest.TestCase):
 def test_words(self):self.assertIn('river',terms('Where is River Valley?'))
 def test_quote_is_a_real_source_span(self):
  docs=[{'title':'Saint M','text':'Saint M was born in New Haven City in 1920.'}]
  got=propose('When was Saint M born?',docs,[0],{'new':2,'haven':2,'city':2,'born':2,'saint':3},k=4)
  self.assertTrue(all(x['quote'] in docs[x['witness_doc']]['text'] for x in got))
 def test_rank_protects_previous_evidence(self):
  rank=rank_fuse([9,1,3],[9,1,3],[[3,4,9,4]],protect=2)
  self.assertEqual(rank[:2],[9,1]);self.assertEqual(len(rank),len(set(rank)))
 def test_interleave(self):
  rank=rank_fuse([9,1,3],[9,1,3],[[3,4]],mode='interleave',protect=2)
  self.assertEqual(rank[:2],[9,1])
if __name__=='__main__':unittest.main()
