#!/usr/bin/env python3
"""HoVer official first-stage retrieval dataset schema and wiki DB format probe."""
import json,hashlib,urllib.request,pathlib,collections,sqlite3
from urllib.error import HTTPError
base=pathlib.Path("results-v17-hover-probe");base.mkdir(exist_ok=True)
url="https://nlp.cs.unc.edu/data/hover/dev_tfidf_doc_retrieval_results.json"
p=base/"dev_tfidf.json"
if not p.exists():
    req=urllib.request.Request(url,headers={"User-Agent":"PGER-V17-original-HoVer/1.0"})
    with urllib.request.urlopen(req,timeout=300) as r:p.write_bytes(r.read())
obj=json.loads(p.read_text())
first=obj[0] if isinstance(obj,list) else next(iter(obj.items()))
print("V17_HOVER_TFIDF_SCHEMA",json.dumps({"root_type":type(obj).__name__,"root_length":len(obj),"first_type":type(first).__name__,"first":str(first)[:1000],"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}),flush=True)
dburl="https://nlp.cs.unc.edu/data/hover/wiki_wo_links.db"
try:
    req=urllib.request.Request(dburl,headers={"Range":"bytes=0-131071","User-Agent":"PGER-V17/1.0"})
    with urllib.request.urlopen(req,timeout=30) as r:
        z=r.read(131072)
        print("V17_HOVER_DB_HEADER",json.dumps({"http":r.status,"header":z[:16].hex(),"first_100":repr(z[:100])}),flush=True)
except Exception as e:print("V17_HOVER_DB_PROBE_ERROR",str(e)[:400],flush=True)
