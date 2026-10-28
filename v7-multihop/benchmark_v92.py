#!/usr/bin/env python3
"""V9.2: bounded BM25 evidence expansion over the exact 1,000-question SAG2 release.
Public benchmark, predeclared eight arms, no paid inference. Not sealed testing.
"""
import argparse,json,pathlib,time,collections
import numpy as np
from benchmark_v71_sag2_corpus import download,official_records,SAG2_AUTHOR,RELEASE
from benchmark_v72 import SparseMethods
from benchmark_v71 import EvidenceLedger
from expansion_v92 import expand,rank_fuse
SEED=20261028
CONFIGS=[('v71_fast',None),('fuse_names_04',('names','fuse',.4,2)),
('fuse_names_08',('names','fuse',.8,2)),('fuse_mixed_04',('mixed','fuse',.4,2)),
('fuse_mixed_08',('mixed','fuse',.8,2)),('fuse_mixed_12',('mixed','fuse',1.2,2)),
('coverage_mixed',('mixed','coverage',.6,2)),('interleave_names',('names','interleave',0,2))]
def evaluate(name,datadir,out,start,n):
    hashes=download(name,datadir)
    unique,docs,questions=official_records(name,datadir)
    assert len(questions)==1000 and len(docs)==SAG2_AUTHOR[name]['corpus']
    assert 0<=start<start+n<=len(questions)
    exact=list(unique)
    t=time.perf_counter();ix=SparseMethods(docs);index_s=time.perf_counter()-t
    t=time.perf_counter();graph=EvidenceLedger(ix);graph_s=time.perf_counter()-t
    results=[];timings=collections.defaultdict(list)
    for row_ix,r in enumerate(questions[start:start+n]):
        q=r['question']
        t=time.perf_counter();bmraw=ix.index.search(q,'bm25',100)
        bm=[i for i,_ in bmraw] or list(range(min(len(docs),50)))
        bm_ms=(time.perf_counter()-t)*1000
        t=time.perf_counter();fast,_=graph.search(q,bm,mode='one-hop',bmraw=bmraw)
        fast_ms=(time.perf_counter()-t)*1000
        t=time.perf_counter();found=expand(q,docs,fast,bm,ix)
        expansion_ms=(time.perf_counter()-t)*1000
        groups={k:(hits,logs) for k,hits,logs in found}
        alternatives={'v71_fast':fast}
        for label,choice in CONFIGS[1:]:
            group,mode,w,protect=choice
            alternatives[label]=rank_fuse(fast,bm,groups[group][0],mode=mode,strength=w,protect=protect)
        gold=set(r['gold'])
        metrics={}
        for label,pred in alternatives.items():
            retrieved=[exact[i] for i in pred[:10]]
            metrics[label]={
             'ae5':int(gold<=set(retrieved[:5])),'ae10':int(gold<=set(retrieved[:10])),
             'r5':len(gold&set(retrieved[:5]))/max(len(gold),1),
             'r10':len(gold&set(retrieved[:10]))/max(len(gold),1)}
        for key,value in [('bm_ms',bm_ms),('graph_ms',fast_ms),('expansion_ms',expansion_ms)]:
            timings[key].append(value)
        results.append({'id':r['id'],'gold_count':len(gold),'metrics':metrics,
          'search_actions':{k:logs for k,(_,logs) in groups.items()},
          'top5_titles':{k:[docs[i]['title'] for i in p[:5]] for k,p in alternatives.items()}})
        if (row_ix+1)%50==0:print(name,start+row_ix+1,'/',start+n,flush=True)
    summary={}
    rng=np.random.default_rng(SEED)
    for label,_ in CONFIGS:
        rows=[r['metrics'][label] for r in results]
        stats={key:round(float(np.mean([r[key] for r in rows])),6) for key in ('ae5','ae10','r5','r10')}
        delta=np.array([r['metrics'][label]['ae5']-r['metrics']['v71_fast']['ae5'] for r in results])
        means=[float(np.mean(delta[rng.integers(0,len(delta),len(delta))])) for _ in range(2000)]
        stats.update(wins=int((delta>0).sum()),losses=int((delta<0).sum()),
          paired_ci95_pp=[round(100*x,2) for x in np.quantile(means,[.025,.975])])
        summary[label]=stats
    output={'dataset':name,'question_start':start,'n':n,'full_corpus_docs':len(docs),
     'source_sha256':hashes,'hipporag2_source_revision':RELEASE,
     'sag2_author_ae5_not_rerun':SAG2_AUTHOR[name]['ae5'],
     'index_seconds':{'bm25':round(index_s,3),'graph':round(graph_s,3)},
     'mean_cpu_query_stage_ms':{k:round(float(np.mean(v)),3) for k,v in timings.items()},
     'results':summary,'limitations':[
       'Public multi-use benchmark, not sealed generalization','SAG2 author reported, not rerun',
       'Many ablations, exploratory bootstrap only','Same SAG2 passage identity',
       'Source exact quotes only, not factual entailment or answer correctness']}
    out.mkdir(parents=True,exist_ok=True)
    (out/f'{name}_{start}_{start+n}_summary.json').write_text(json.dumps(output,indent=2))
    with (out/f'{name}_{start}_{start+n}_cases.jsonl').open('w') as f:
        for r in results:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    print('RESULT',name,start,json.dumps(summary),flush=True)
    return output
def main():
    p=argparse.ArgumentParser()
    p.add_argument('command',choices=['run','smoke'])
    p.add_argument('--datasets',nargs='+',default=['2wikimultihopqa','musique','hotpotqa'])
    p.add_argument('--start',type=int,default=0);p.add_argument('--limit',type=int,default=120)
    p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('results-v92'))
    p.add_argument('--data',type=pathlib.Path,default=pathlib.Path('data/sag2_pinned'))
    a=p.parse_args()
    if a.command=='smoke':
        from expansion_v92 import terms,propose
        assert 'john' in terms('John was an English physicist')
        assert isinstance(propose('Which city?', [{'title':'A','text':'A is in New York City.'}], [0],{'new':3,'york':3,'city':2}),list)
        print('V9.2 smoke PASS');return
    for name in a.datasets:evaluate(name,a.data,a.out,a.start,a.limit)
    print('V9.2 frozen benchmark complete',flush=True)
if __name__=='__main__':main()
