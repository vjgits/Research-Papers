#!/usr/bin/env python3
"""V17 initial HoVer official data and SAG2 backend feasibility audit, NO scoring."""
import json,urllib.request,hashlib,pathlib,collections,os,time
u="https://raw.githubusercontent.com/hover-nlp/hover/main/data/hover/hover_dev_release_v1.1.json"
out=pathlib.Path("results-v17-hover-probe");out.mkdir(exist_ok=True)
req=urllib.request.Request(u,headers={"User-Agent":"PGER-new-dataset-provenance-audit"})
data=urllib.request.urlopen(req,timeout=100).read()
rows=json.loads(data)
count=collections.Counter()
titles=set()
samples=[]
for row in rows:
    k=int(row.get("num_hops",0));count[k]+=1
    sf=row.get("supporting_facts") or []
    for fact in sf:
        title=fact.get("key") if isinstance(fact,dict) else fact[0]
        if title:titles.add(str(title))
    if len(samples)<3:samples.append(row)
urls={
 "official_hover_wiki_db":"https://nlp.cs.unc.edu/data/hover/wiki_wo_links.db",
 "official_hover_dev_tfidf":"https://nlp.cs.unc.edu/data/hover/dev_tfidf_doc_retrieval_results.json",
 "huggingface_hover_parquet":"https://huggingface.co/datasets/nielsgl/hover/resolve/main/data/validation-00000-of-00001.parquet",
 "wikipedia_api":"https://en.wikipedia.org/w/api.php?action=query&format=json&titles=Tivoli%20Gardens"
}
heads={}
for key,url in urls.items():
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"PGER-V17/1.0 (research; no credentials)"},method="HEAD")
        with urllib.request.urlopen(req,timeout=15) as x:
            heads[key]={"status":x.status,"length":x.headers.get("Content-Length"),"type":x.headers.get("Content-Type"),"final":x.url[:180]}
    except Exception as e:heads[key]={"error":str(e)[:270]}
report={"dataset":"HoVer original annotated development set (not blind official test)",
  "n":len(rows),"sha256_dev":hashlib.sha256(data).hexdigest(),
  "hop_counts":dict(count),"unique_annotated_article_titles":len(titles),
  "source_license":"CC-BY-SA-4.0",
  "first_samples":samples,"source_access":heads,
  "warning":"Gold title annotations identify source documents; document retrieval requires original published Wikipedia corpus. Claim-only records alone are insufficient for fair open-world evaluation."}
(out/"probe.json").write_text(json.dumps(report,indent=2,ensure_ascii=False))
print("V17_HOVER_PROBE",json.dumps({
    k:v for k,v in report.items() if k not in ("first_samples",)
}),flush=True)
print("V17_HOVER_SAMPLE",json.dumps(samples[0])[:1500],flush=True)
