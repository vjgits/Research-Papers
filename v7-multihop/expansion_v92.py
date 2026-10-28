"""V9.2 bounded source-term expansion (prior-art-inspired control; no novelty claim)."""
import collections,math,re
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
WORDS=re.compile(r"[a-z][a-z0-9'-]+",re.I)
NAMES=re.compile(r"\b(?:[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?\s+){1,3}[A-Z][a-z]+\b")
SENT=re.compile(r'(?<=[.!?])\s+|\n+')
STOP=set(ENGLISH_STOP_WORDS)|{'said','also','many','one','two','three','first','early','known','called'}
def terms(s):
    return [t.lower() for t in WORDS.findall(s) if len(t)>2 and t.lower() not in STOP]
def propose(question,docs,base,idf,kind='names',seed_n=4,k=8):
    q=set(terms(question)); scored=[]
    for pos,i in enumerate(base[:seed_n]):
        text=docs[i].get('text','')[:1900]
        for sid,sent in enumerate(SENT.split(text)):
            if len(sent)<20:continue
            ts=terms(sent); overlap=sum(idf.get(t,0.) for t in set(ts)&q)
            if overlap<=0 and pos>1:continue
            names=[m.group().strip() for m in NAMES.finditer(sent)]
            candidates=names if kind=='names' else names+[t for t in ts if t not in q and 1.6<idf.get(t,0)<8.0]
            for term in candidates:
                parts=set(terms(term))
                if not parts or parts<=q:continue
                rarity=sum(idf.get(t,0.) for t in parts)
                if rarity<1:continue
                novelty=1-len(parts&q)/len(parts)
                score=(math.log1p(overlap)+.4)*rarity*novelty*(1.25 if len(parts)>1 else .55)/(1+.15*pos)
                scored.append((score,term,i,sid,sent[:350]))
    out=[];seen=set()
    for _,term,i,sid,quote in sorted(scored,key=lambda x:(-x[0],x[1].casefold())):
        if term.casefold() in seen:continue
        seen.add(term.casefold())
        out.append({'term':term,'witness_doc':int(i),'sentence_index':sid,'quote':quote})
        if len(out)>=k:break
    return out
def rank_fuse(fast,bm25,hits,mode='fuse',strength=.7,protect=2,cutoff=100):
    score=collections.defaultdict(float)
    for r,i in enumerate(fast[:100]):score[i]+=1/(25+r)
    for r,i in enumerate(bm25[:100]):score[i]+=.22/(25+r)
    for k,hit in enumerate(hits):
        scale=strength/(1+.12*k)
        for r,i in enumerate(hit):score[i]+=scale/(25+r)
    anchors=list(dict.fromkeys(fast[:protect]))
    if mode=='coverage':
        counts=collections.Counter(i for hit in hits for i in set(hit[:30]))
        for i,c in counts.items():score[i]+=.012*min(c,4)
    ordered=sorted(score,key=lambda x:(-score[x],x))
    if mode=='interleave':
        selection=list(anchors);seen=set(selection)
        for hit in hits:
            for i in hit[:8]:
                if i not in seen:selection.append(i);seen.add(i);break
        return (selection+[i for i in ordered if i not in seen])[:cutoff]
    return (anchors+[i for i in ordered if i not in anchors])[:cutoff]
def expand(question,docs,fast,bm,index,strategies=('names','mixed'),seed_n=4,query_limit=8):
    result=[]
    for kind in strategies:
        selected=propose(question,docs,fast,index.idfs,kind=kind,seed_n=seed_n,k=query_limit)
        hits=[];logs=[]
        for p in selected:
            rows=[i for i,_ in index.search(p['term'],'bm25',40)]
            if rows:
                hits.append(rows);logs.append({'query':p['term'],'witness_doc':p['witness_doc'],'sentence_index':p['sentence_index'],'quote':p['quote'],'returned':len(rows)})
        result.append((kind,hits,logs))
    return result
