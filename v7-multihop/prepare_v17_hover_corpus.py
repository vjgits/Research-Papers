#!/usr/bin/env python3
"""V17A fresh independent HoVer corpus, built WITHOUT evaluation gold labels.

Original HoVer dev claims and official DRQA top-100 titles; original HoVer
Hotpot 2017 Wikipedia SQLite. Source titles sampled ONLY from published
claim->TFIDF candidate lists, not gold evidence titles, and extra background
from unrelated query lists. Gold consulted AFTER frozen corpus selection, to
measure absolute source availability, NEVER to add missing evidence.

This is a shared *transductive pooled first-stage-candidate corpus*, NOT
official full-Wikipedia HoVer or blinded/independent deployment evaluation.
Both PGER and author SAG2 use exact same corpus/query IDs.
"""
import hashlib,json,pathlib,sqlite3,urllib.request,unicodedata,re,sys,time
from collections import Counter
ROOT=pathlib.Path("v17-hover-data")
RAW=ROOT/"raw"
OUT=ROOT/"prepared"
DEV_URL="https://raw.githubusercontent.com/hover-nlp/hover/main/data/hover/hover_dev_release_v1.1.json"
TF_URL="https://nlp.cs.unc.edu/data/hover/dev_tfidf_doc_retrieval_results.json"
WIKI_URL="https://nlp.cs.unc.edu/data/hover/wiki_wo_links.db"
SAMPLE_PER_HOP=40
TF_PER_CLAIM=100
EXTRA_QUESTIONS=240
EXTRA_PER_CLAIM=25
MAX_DOC_CHARS=5000

def download(url,path,expected=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and (expected is None or path.stat().st_size==expected):return
    if path.exists():path.unlink()
    req=urllib.request.Request(url,headers={"User-Agent":"PGER-V17-HoVer-PublicResearch/1.0"})
    start=time.time()
    with urllib.request.urlopen(req,timeout=180) as r,open(path,"wb") as f:
        size=int(r.headers.get("Content-Length") or 0)
        total=0
        while True:
            b=r.read(8*1024*1024)
            if not b:break
            f.write(b);total+=len(b)
            if total//(128*1024*1024)>(total-len(b))//(128*1024*1024):
                print("V17_DOWNLOAD_PROGRESS",path.name,total,"of",size,flush=True)
    if expected and total!=expected:raise RuntimeError(f"Bad size {path}: {total} != {expected}")
    print("V17_DOWNLOADED",path.name,total,"seconds",round(time.time()-start,1),flush=True)

def normalized(t):return unicodedata.normalize("NFD",str(t))
def visible_text(raw):
    if raw is None:return ""
    if isinstance(raw,(bytes,bytearray)):
        try:raw=raw.decode()
        except:raw=raw.decode("utf8","replace")
    if not isinstance(raw,str):return str(raw)
    try:v=json.loads(raw)
    except:return raw
    if isinstance(v,list):
        def txt(row):
            if isinstance(row,str):return row
            if isinstance(row,dict):return str(row.get("text") or row.get("sentence") or "")
            if isinstance(row,(list,tuple)):return str(row[-1])
            return str(row)
        return " ".join(map(txt,v))
    if isinstance(v,dict):return " ".join(str(y) for y in v.values())
    return str(v)

def main():
    download(DEV_URL,RAW/"hover_dev.json")
    download(TF_URL,RAW/"hover_dev_tfidf.json",19247010)
    rows=json.loads((RAW/"hover_dev.json").read_text())
    tf=json.loads((RAW/"hover_dev_tfidf.json").read_text())
    lookup={x["id"]:x for x in tf}
    groups={h:[] for h in (2,3,4)}
    for r in rows:
        h=int(r.get("num_hops") or 0)
        if h in groups and r["uid"] in lookup:groups[h].append(r)
    def hkey(r):return hashlib.sha256(("PGER-17A-20261028:"+r["uid"]).encode()).hexdigest()
    selected=[r for h in (2,3,4) for r in sorted(groups[h],key=hkey)[:SAMPLE_PER_HOP]]
    selected_ids={r["uid"] for r in selected}
    background=sorted((r for r in rows if r["uid"] not in selected_ids and r["uid"] in lookup),key=hkey)[:EXTRA_QUESTIONS]
    assert len(selected)==120
    titles=set()
    def titles_for(row,n):
        x=lookup[row["uid"]]["doc_retrieval_results"]
        t=x[0][0]
        assert isinstance(t,list)
        return [str(s) for s in t[:n]]
    for r in selected:titles.update(titles_for(r,TF_PER_CLAIM))
    for r in background:titles.update(titles_for(r,EXTRA_PER_CLAIM))
    # Freeze without any use of supporting_facts. Gold checked later.
    frozen_titles=sorted(titles)
    frozen_hash=hashlib.sha256(json.dumps(frozen_titles,ensure_ascii=False).encode()).hexdigest()
    print("V17_TITLES_FROZEN",len(frozen_titles),frozen_hash,flush=True)
    download(WIKI_URL,RAW/"wiki_wo_links.db",2156273664)
    con=sqlite3.connect("file:"+str((RAW/"wiki_wo_links.db").absolute())+"?mode=ro",uri=True)
    schema=con.execute("SELECT name,sql FROM sqlite_master WHERE type='table'").fetchall()
    print("V17_WIKI_SCHEMA",json.dumps(schema)[:1000],flush=True)
    assert any(name=="documents" for name,sql in schema)
    docs=[];missing=[];seen=set()
    for j,title in enumerate(frozen_titles):
        ids=[normalized(title),title]
        row=None
        for key in ids:
            row=con.execute("SELECT * FROM documents WHERE id=?",(key,)).fetchone()
            if row is not None:break
        if row is None:
            missing.append(title);continue
        # Official HoVer schema has id and text; preserve full text before
        # truncation in hashes; no synthetic annotations/source augmentation.
        text=visible_text(row[1] if len(row)>1 else "")
        if not text.strip():
            missing.append(title);continue
        if normalized(title) in seen:continue
        seen.add(normalized(title))
        docs.append({"_id":title,"idx":str(j),"title":title,
                     "text":text[:MAX_DOC_CHARS],"source":"original HoVer 2017 Wikipedia"})
        if len(docs)%3000==0:print("V17_EXTRACTED",len(docs),flush=True)
    con.close()
    (OUT).mkdir(parents=True,exist_ok=True)
    usable={normalized(d["title"]) for d in docs}
    qq=[]
    stats=Counter()
    for row in selected:
        gold=sorted(set(str(x[0] if isinstance(x,list) else x["key"]) for x in row["supporting_facts"]))
        matches=[x for x in gold if normalized(x) in usable]
        h=int(row["num_hops"])
        stats[f"n_{h}hop"]+=1
        stats[f"fully_available_{h}hop"]+=int(len(matches)==len(gold))
        qq.append({"uid":row["uid"],"question":row["claim"],
                   "gold_titles":gold,"label":row.get("label"),
                   "hops":h,"gold_n":len(gold),"available_gold_n":len(matches)})
    (OUT/"corpus.json").write_text(json.dumps(docs,ensure_ascii=False))
    (OUT/"questions.json").write_text(json.dumps(qq,ensure_ascii=False))
    manifest={"name":"HoVer official dev, 120 hash-selected balanced claims",
      "source_type":"Original HoVer Wikipedia SQLite, 2017 release",
      "eval_mode":"Transductive corpus pooled from labeled claims' UNLABELED DRQA candidate titles and unrelated candidate titles; never full Wikipedia open-world",
      "selected_claims":len(selected),"all_original_dev":len(rows),
      "n_candidate_titles_before_source_fetch":len(frozen_titles),
      "n_actual_corpus_docs":len(docs),"titles_missing_original_db":len(missing),
      "full_gold_corpus_coverage":dict(stats),
      "max_chars_per_doc":MAX_DOC_CHARS,"source_titles_sha256":frozen_hash,
      "dataset_sha256":hashlib.sha256((RAW/"hover_dev.json").read_bytes()).hexdigest(),
      "tfidf_sha256":hashlib.sha256((RAW/"hover_dev_tfidf.json").read_bytes()).hexdigest(),
      "wiki_db_bytes":2156273664,
      "gold_used_in_corpus_construction":False,
      "notes":[
        "Original TFIDF per-claim candidate titles used as source pool: transductive, NOT unbiased wiki search",
        "Gold source labels only offline measured after corpus title selection frozen",
        "Full wiki not indexed; source missing -> zero complete evidence score",
        "Wiki document truncated 5000 Python characters for both retrievers",
        "No claim verdict or supporting sentence selection by either system",
        "No official HoVer leaderboard score is computed from title-only metrics"]}
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2))
    print("V17_CORPUS_PREPARED",json.dumps(manifest),flush=True)

if __name__=="__main__":main()
