#!/usr/bin/env python3
"""V14A preregistration data-integrity audit of NEW external proof-tree source.

Official Dalvi et al EMNLP21 EntailmentBank data via CC-BY-4.0 mirror,
sxiong/entailmentbank revision 8c6c148f7a21c21ff037a42d9a22446c9d42debc.
No model evaluation, no answer generation, no test-label training.
Only audit proof leaves, depth and WorldTree exact fact identity.
"""
import argparse,collections,hashlib,json,pathlib,re,time,urllib.request
BASE="https://huggingface.co/datasets/sxiong/entailmentbank/resolve/8c6c148f7a21c21ff037a42d9a22446c9d42debc/"
FILES=["worldtree_corpus.jsonl"]+[
    "task1/"+s+".jsonl" for s in ("train","validation","test")]+[
    "task2/"+s+".jsonl" for s in ("train","validation","test")]
PROOF_SENT=re.compile(r"\bsent\d+\b")
def get(folder,path):
    p=folder/path
    p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():
        last=None
        for trial in range(3):
            try:
                req=urllib.request.Request(BASE+path,
                    headers={"User-Agent":"PGER-V14A-Independent-Proof-Source-Audit/1.0"})
                with urllib.request.urlopen(req,timeout=240) as f:content=f.read()
                if len(content)<1000:raise ValueError("Unexpected small file")
                tmp=p.with_name(p.name+".tmp");tmp.write_bytes(content);tmp.replace(p)
                break
            except Exception as ex:
                last=ex;time.sleep(2*(trial+1))
        if not p.exists():raise RuntimeError("download "+path+": "+str(last))
    b=p.read_bytes()
    rows=[json.loads(x) for x in b.decode().splitlines() if x.strip()]
    return rows,hashlib.sha256(b).hexdigest()

def canonical(s):
    return re.sub(r"\s+"," ",str(s).strip().casefold())
def audit(rows,textmap):
    report=collections.Counter();samples=[]
    for q in rows:
        meta=q.get("meta") or {}
        triples=meta.get("triples") or {}
        if not isinstance(triples,dict):
            report["bad_triples"]+=1;continue
        proof=q.get("proof") or ""
        leafs=set(PROOF_SENT.findall(proof))
        if not leafs:report["no_proof_leafs"]+=1;continue
        if not leafs<=set(triples):
            report["leaf_not_in_triples"]+=1;continue
        n=len(leafs); depth=int(q.get("depth_of_proof") or 0)
        steps=int(q.get("length_of_proof") or 0)
        report["eligible_proofs"]+=1
        report["leaf_count_"+str(n)]+=1
        report["depth_"+str(depth)]+=1
        report["steps_"+str(steps)]+=1
        report["four_plus_facts"]+=int(n>=4)
        report["four_plus_depth"]+=int(depth>=4)
        mapped=0;dupe=0
        for leaf in leafs:
            t=canonical(triples[leaf])
            matches=textmap.get(t,[])
            if len(matches)==1:mapped+=1
            elif len(matches)>1:dupe+=1
        report["total_required_leaves"]+=n
        report["exact_unique_worldtree_leaves"]+=mapped
        report["ambiguous_duplicate_worldtree_leaves"]+=dupe
        report["fully_mapped_questions"]+=int(mapped==n)
        if n>=4 and len(samples)<6:
            samples.append({"id":q["id"],"leaf_count":n,"depth":depth,
                            "steps":steps,"unique_leaf_matches":mapped,
                            "proof_prefix":proof[:240]})
    return dict(report),samples

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--root",type=pathlib.Path,default=pathlib.Path("data/entailmentbank_v14"))
    a.add_argument("--out",type=pathlib.Path,default=pathlib.Path("results-v14-audit"))
    z=a.parse_args()
    data={};hashes={}
    for filename in FILES:
        rows,sha=get(z.root,filename);data[filename]=rows;hashes[filename]=sha
        print("V14A_SOURCE",filename,len(rows),sha,flush=True)
    facts=data["worldtree_corpus.jsonl"]
    textmap=collections.defaultdict(list)
    for i,d in enumerate(facts):
        textmap[canonical(d["text"])].append(i)
    output={"stage":"V14A","source":"Dalvi et al, EMNLP 2021 EntailmentBank",
            "mirror":"sxiong/entailmentbank CC BY 4.0",
            "revision":"8c6c148f7a21c21ff037a42d9a22446c9d42debc",
            "sha256":hashes,
            "worldtree_facts":len(facts),
            "unique_exact_fact_texts":len(textmap),
            "notes":[
              "Human annotated proof trees, NOT a claim that PGER verifies entailment",
              "Number of proof leaf facts != logical inference depth",
              "Published test annotations audited only to set provenance/eligibility; algorithms cannot train/tune on these labels",
              "Exact text facts may have duplicates or local edits; failures explicitly counted",
              "This is a corpus integrity audit only, not a completed PGER accuracy experiment"
            ],"splits":{}}
    for task in ("task1","task2"):
        for split in ("train","validation","test"):
            filename=f"{task}/{split}.jsonl"
            stats,samples=audit(data[filename],textmap)
            output["splits"][f"{task}_{split}"]={"n":len(data[filename]),
                    "stats":stats,"four_plus_examples":samples}
            print("V14A_SPLIT",task,split,json.dumps(stats),flush=True)
    z.out.mkdir(parents=True,exist_ok=True)
    (z.out/"audit.json").write_text(json.dumps(output,indent=2))
    print("V14A_AUDIT_COMPLETE",json.dumps(output["splits"]["task1_test"]["stats"]),flush=True)
if __name__=="__main__":
    main()
