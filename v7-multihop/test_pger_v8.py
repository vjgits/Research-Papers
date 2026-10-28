import unittest
from pger_v8_core import EvidenceMap,build_candidate_rescue,rank_candidates,route_cost

class V8Tests(unittest.TestCase):
    def setUp(self):
        self.docs=[{'_id':f'n{i}','title':f'Node Number {i}',
             'text':f'Node Number {i} is located in Node Number {i+1}.' if i<8 else 'Node Number 8 is very remote.'}
             for i in range(9)]
        self.graph=EvidenceMap(self.docs)

    def test_eight_source_dependency_chain(self):
        paths=self.graph.chain(0,set(range(9)),max_edges=8,beam=16)
        long=[p for p in paths if len(p)==8]
        self.assertTrue(long,'Eight evidence transitions should be representable')
        self.assertTrue(all(self.graph.source_valid(e) for e in long[0]))
        self.assertEqual([e.parent_edge for e in long[0]], [None]+list(range(7)))

    def test_no_hallucinated_ninth_hop(self):
        self.assertLessEqual(max(map(len,self.graph.chain(0,set(range(9)),max_edges=8))),8)

    def test_candidate_pool_no_gold_access_and_exact_two_searches(self):
        calls=[]
        def search(q,n):calls.append(q);return [3,4,5]
        pool,log,_=build_candidate_rescue('Where is the city of Node Number 0?',list(range(9)),list(range(9)),self.graph,search,budget=2)
        self.assertEqual(len(calls),2)
        self.assertEqual(len(log),2)
        self.assertTrue({3,4,5}<=pool)

    def test_same_rank_candidates_modes(self):
        pool=set(range(9))
        x=[]
        for mode in ('rescue','joint','proofgap'):
            order,meta=rank_candidates('Where is Node Number 0 located?',list(range(9)),list(range(9)),self.graph,pool,mode)
            self.assertEqual(set(order),pool)
            self.assertEqual(len(order),len(set(order)))
            x.append(order)

    def test_easy_path(self):
        self.assertEqual(route_cost('Node Number 0',list(range(9)),self.graph),'fast')
        self.assertEqual(route_cost('Which city is earlier or later than Node Number 0?',list(range(9)),self.graph),'investigate')

    def test_invalid_provenance_does_not_pass(self):
        first=self.graph.chain(0,set(range(9)),max_edges=1)[0][0]
        self.docs[0]['text']='made up'
        self.assertFalse(self.graph.source_valid(first))

if __name__=='__main__':unittest.main()
