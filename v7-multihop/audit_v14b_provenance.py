#!/usr/bin/env python3
"""V14B provenance audit: count source statements with exact/UUID identity.

Only benchmark schema data audited; no ranked retrieval or label training.
"""
import argparse,collections,json,pathlib,re
from audit_v14_entailmentbank import get,canonical,PROOF_SENT
UUID_FIELDS=("uuid","worldtree_uuid","id")
def uids(v):
    if isinstance(v,str):return [v]
    if isinstance(v,dict):
        for field in UUID_FIELDS:
            if v.get(field):return uids(v[field])
        if v.get("provenance"):return uids(v["provenance"])
    if isinstance(v,list):
        out=[]
        for t in v:out.extend(uids(t))
        return out
    return []
def provenance(value,leaf):
    if isinstance(value,dict):
        v=value.get(leaf)
        if v is None:v=value.get(str(leaf))
        if v is None:return []
        return uids(v)
    return []
def audit(questions,txt_ids,uuid_idx,corpus):
    out=collections.Counter();samples=[]
    for q in questions:
        m=q.get("meta") or {}
        triples=m.get("triples") or {}
        p=m.get("worldtree_provenance") or {}
        leafs=set(PROOF_SENT.findall(q.get("proof") or ""))
        missing=[];uuid_map=[];exact=0;uuid=0;diff=0;dup=0
        for leaf in leafs:
            t=canonical(triples.get(leaf,""))
            opts=txt_ids.get(t,[])
            if opts:
                exact+=1;dup+=int(len(opts)>1);continue
            pos=[]
            for uid in provenance(p,leaf):
                if uid in uuid_idx:pos.append(uuid_idx[uid])
            if pos:
                uuid+=1
                if all(canonical(corpus[i]["text"])!=t for i in pos):
                    diff+=1
                    if len(samples)<8:samples.append({
                       "id":q["id"],"leaf":leaf,
                       "fact":triples.get(leaf),"uuid":provenance(p,leaf),
                       "canonical_text":corpus[pos[0]]["text"],
                       "provenance_raw":p.get(leaf)})
            else:
                missing.append(leaf)
                if len(samples)<8:samples.append({
                    "id":q["id"],"leaf":leaf,"fact":triples.get(leaf),
                    "provenance_raw":p.get(leaf) if isinstance(p,dict) else str(p)[:300]})
        out["questions"]+=1
        out["unique_source_complete"]+=int(not missing and not diff)
        out["provenance_candidate_complete"]+=int(not missing)
        out["questions_with_unmappable"]+=int(bool(missing))
        out["questions_with_rewritten_provenance"]+=int(bool(diff))
        out["number_of_gold_leafs"]+=len(leafs)
        out["exact_matched_leaves"]+=exact
        out["duplicate_text_leaves"]+=dup
        out["uuid_resolved_leaves"]+=uuid
        out["uuid_rewritten_leaves"]+=diff
        out["missing_leaves"]+=len(missing)
    return dict(out),samples
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data",type=pathlib.Path,default=pathlib.Path("data/entailmentbank_v14"))
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v14-provenance"))
    a=p.parse_args()
    corpus,_=get(a.data,"worldtree_corpus.jsonl")
    txt_ids=collections.defaultdict(list);uid={}
    for i,entry in enumerate(corpus):
        txt_ids[canonical(entry["text"])].append(i)
        uid[str(entry["uuid"])]=i
    result={"source_corpus":len(corpus),"canonical_unique_count":len(txt_ids),"splits":{}}
    for split in ("train","validation","test"):
        qs,_=get(a.data,f"task1/{split}.jsonl")
        stats,samples=audit(qs,txt_ids,uid,corpus)
        result["splits"][split]={"stats":stats,"examples":samples}
        print("V14B_PROVENANCE",split,json.dumps(stats),flush=True)
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/"provenance_audit.json").write_text(json.dumps(result,indent=2))
if __name__=="__main__":main()
