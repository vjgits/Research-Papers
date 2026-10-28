"""V8.8 natural-document relation proposal. No gold entities or relations used in extraction.
Known techniques: regex/NER, lexical predicates, local-context scoring and NLI gating.
Claims are textually *proposed* and cited, NOT independently proven facts.
"""
from collections import defaultdict
from dataclasses import dataclass,asdict
import hashlib,re,unicodedata

REL_CUES={
 'P19':(r'\bborn (?:in|at)\b',), 'P20':(r'\bdied (?:in|at)\b',),
 'P27':(r'\bcitizen of\b',r'\bcitizenship\b'),
 'P17':(r'\bcountry of\b',r'\bin the country of\b',r'\bpart of (?:the )?country\b'),
 'P131':(r'\blocated in\b',r'\bbased in\b',r'\blies in\b'),
 'P159':(r'\bheadquarters (?:are |is )?(?:in|at)\b',r'\bheadquartered in\b'),
 'P57':(r'\bdirected by\b',r'\bdirector of\b'),
 'P50':(r'\bwritten by\b',r'\bauthored by\b',r'\bwriter of\b'),
 'P26':(r'\bmarried to\b',r'\bspouse of\b'),
 'P36':(r'\bcapital of\b',),
 'P108':(r'\bworks? for\b',r'\bemployed by\b'),
 'P69':(r'\beducated at\b',r'\bstudied at\b'),
 'P40':(r'\bchildren? of\b',),
 'P22':(r'\bfather of\b',), 'P25':(r'\bmother of\b',),
 'P161':(r'\bstarr?ed in\b',r'\bcast (?:of|member)\b')}
COMPILED={k:tuple(re.compile(p,re.I) for p in vs) for k,vs in REL_CUES.items()}
# Deliberately simple baseline. spaCy en_core_web_sm is optional only for experimental comparator.
PROPER=re.compile(r"(?<![\w])(?:[A-Z][\wÀ-ÿ'’.-]*|[A-Z]{2,})(?:\s+(?:(?:of|the|and|de|von|van|la|di|da)\s+)?(?:[A-Z][\wÀ-ÿ'’.-]*|[A-Z]{2,})){0,4}")
BAD={'The','It','He','She','In','As','This','His','Her','On','After','Before','First','However','Later','There','They','A','An'}
NEG=re.compile(r'\b(?:not|never|denied|unconfirmed|rumou?red|allegedly)\b',re.I)

@dataclass(frozen=True)
class Mention:
    name:str
    sentence_id:int
    start:int
    end:int
    method:str

@dataclass(frozen=True)
class Triple:
    h:str
    r:str
    t:str
    sentence_id:int
    start:int
    end:int
    quote:str
    source_hash:str
    method:str
    confidence:float

def norm(s):
    s=unicodedata.normalize('NFKD',str(s)).casefold()
    return re.sub(r'\W+',' ',s).strip()

def valid_mention(m,sents):
    return 0<=m.sentence_id<len(sents) and sents[m.sentence_id][m.start:m.end]==m.name

def regex_mentions(sents):
    output=[]
    for j,text in enumerate(sents):
        for m in PROPER.finditer(text):
            phrase=m.group().strip(' .,-')
            if phrase in BAD or len(phrase)<3 or not any(x.isalpha() for x in phrase):continue
            idx=m.start();end=idx+len(phrase)
            z=Mention(phrase,j,idx,end,'regex')
            if valid_mention(z,sents):output.append(z)
    return sorted(set(output),key=lambda z:(z.sentence_id,z.start,z.end))

def spacy_mentions(sents,nlp):
    keep={'PERSON','ORG','GPE','LOC','FAC','NORP','WORK_OF_ART','EVENT','PRODUCT'}
    output=[]
    for j,doc in enumerate(nlp.pipe(sents,batch_size=16)):
        text=sents[j]
        for e in doc.ents:
            if e.label_ not in keep or len(e.text.strip())<3:continue
            # Do not use DocRED vertexSet for candidate creation or alignment.
            m=Mention(e.text,j,e.start_char,e.end_char,'spacy')
            if valid_mention(m,sents):output.append(m)
    return sorted(set(output),key=lambda z:(z.sentence_id,z.start,z.end))

def name_set(mentions):
    return {norm(m.name) for m in mentions}

def pair_candidates(mentions,sents,neighborhood=1,cap=300):
    """Entity-pair proposals derived from raw-source mention proximity ONLY.
    Distance based sort fixed before gold. Pair orientations both retained.
    """
    bysent=defaultdict(list)
    for m in mentions:bysent[m.sentence_id].append(m)
    pairs=[];seen=set()
    for i,ms in sorted(bysent.items()):
        right=[n for jj in range(i,min(len(sents),i+neighborhood+1)) for n in bysent.get(jj,())]
        for m in ms:
            for n in right:
                if m==n or norm(m.name)==norm(n.name):continue
                k=(norm(m.name),norm(n.name))
                if not all(k) or k in seen:continue
                seen.add(k)
                distance=abs(m.sentence_id-n.sentence_id)
                local=abs(m.start-n.start) if distance==0 else 200+distance*100
                pairs.append((distance,local,k,m,n))
    pairs.sort(key=lambda x:(x[0],x[1],x[2]))
    return [(m,n) for _,__,___,m,n in pairs[:cap]]

def relation_triples(mentions,sents,strict=True,cap=250):
    """A weak, conservative local cue proposal. No NLI or parsed dependency claim.
    Triple h/r/t orientation is based on surface order and local predicate cue.
    """
    bysent=defaultdict(list)
    for m in mentions:bysent[m.sentence_id].append(m)
    output=[];seen=set()
    for j,ms in sorted(bysent.items()):
        s=sents[j]
        ms=sorted(ms,key=lambda m:m.start)
        for k,patterns in COMPILED.items():
            for pat in patterns:
                for cue in pat.finditer(s):
                    left=[m for m in ms if m.end<=cue.start()]
                    right=[m for m in ms if m.start>=cue.end()]
                    if not left or not right:continue
                    h=min(left,key=lambda m:cue.start()-m.end)
                    # Shared passive subject across coordinated verbs (e.g. X directed by A and produced by B).
                    earlier_cue=any(p.search(s[:cue.start()]) for ps in COMPILED.values() for p in ps)
                    if earlier_cue and re.search(r'\band\s*$',s[max(0,cue.start()-15):cue.start()],re.I):
                        h=min(left,key=lambda m:m.start)
                    t=min(right,key=lambda m:m.start-cue.end())
                    if norm(h.name)==norm(t.name):continue
                    # Exclude clear local negation. This does NOT imply opposite triple is true.
                    segment=s[max(0,h.end):min(len(s),t.start)]
                    if strict and NEG.search(segment):continue
                    # Stop if a competing relation cue occurs between cue and object.
                    intervening=s[cue.end():t.start]
                    if strict and any(p.search(intervening) for rel,ps in COMPILED.items() if rel!=k for p in ps):continue
                    z=(norm(h.name),k,norm(t.name),j)
                    if z in seen:continue
                    seen.add(z)
                    q=Triple(h.name,k,t.name,j,0,len(s),s,hashlib.sha256(s.encode()).hexdigest(),h.method,1.0)
                    output.append(q)
    return output[:cap]

def verify_triple(tr,sents):
    return (0<=tr.sentence_id<len(sents) and sents[tr.sentence_id][tr.start:tr.end]==tr.quote
            and hashlib.sha256(tr.quote.encode()).hexdigest()==tr.source_hash)

def nli_filter(triples,predict,templates,cap=48,threshold=.70,margin=.10):
    """Fixed first cap triples, one NLI call per proposed triple, compare matched budget.
    NLI is not a truth oracle; its labels are contradiction/entailment/neutral.
    """
    selected=triples[:cap]
    pairs=[]
    for t in selected:
        template=templates.get(t.r)
        if not template:raise ValueError('Unknown relation '+t.r)
        pairs.append((t.quote,template.format(h=t.h,t=t.t)))
    logits=list(predict(pairs)) if pairs else []
    if len(logits)!=len(pairs):raise ValueError('Incorrect inference count')
    kept=[];statuses=[]
    import math
    for triple,vals in zip(selected,logits):
        if len(vals)!=3:raise ValueError('Invalid model output')
        m=max(vals);exp=[math.exp(float(x)-m) for x in vals];total=sum(exp);p=[v/total for v in exp]
        ok=p[1]>=threshold and p[1]-max(p[0],p[2])>=margin
        statuses.append({'entail':p[1],'contradict':p[0],'neutral':p[2],'accepted':ok})
        if ok:kept.append(triple)
    return kept,statuses,len(pairs)