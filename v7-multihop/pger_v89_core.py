"""PGER V8.9 REBEL generator adapter, standard published methods, not original.
Raw generated triples and strictly sourced subset are separate; offsets are not entailment.
"""
import hashlib, re, unicodedata

def norm(s):
    return re.sub(r"\W+", " ", unicodedata.normalize("NFKD", str(s)).casefold()).strip()

# Explicit locked conservative REBEL text -> DocRED Wikidata property map.
RELATION_MAP = {
    'place of birth':'P19','place of death':'P20',
    'country of citizenship':'P27','country':'P17',
    'located in the administrative territorial entity':'P131',
    'headquarters location':'P159','director':'P57','author':'P50',
    'spouse':'P26','capital':'P36','employer':'P108',
    'educated at':'P69','child':'P40','father':'P22','mother':'P25',
    'cast member':'P161'
}

def parse_rebel(text):
    """Documented REBEL special-token representation; no inference of unsupported fields."""
    triples=[];head=tail=rel=''; mode=None
    for tok in text.replace('<s>',' ').replace('</s>',' ').replace('<pad>',' ').split():
        if tok=='<triplet>':
            if head.strip() and tail.strip() and rel.strip():triples.append((head.strip(),rel.strip(),tail.strip()))
            head=tail=rel='';mode='h'
        elif tok=='<subj>':
            if head.strip() and tail.strip() and rel.strip():triples.append((head.strip(),rel.strip(),tail.strip()))
            tail='';rel='';mode='t'
        elif tok=='<obj>':mode='r';rel=''
        elif mode=='h':head+=' '+tok
        elif mode=='t':tail+=' '+tok
        elif mode=='r':rel+=' '+tok
    if head.strip() and tail.strip() and rel.strip():triples.append((head.strip(),rel.strip(),tail.strip()))
    return triples

def anchored(text,head,tail):
    """Hard exact case-folded surface string anchoring, not truth verification."""
    x=text.casefold()
    for ent in (head,tail):
        ent=ent.casefold().strip()
        if not ent or not re.search(r'(?<!\w)'+re.escape(ent)+r'(?!\w)',x):return False
    return True

def classify_output(output,sentence,sentence_id,model='Babelscape/rebel-large'):
    """Returns all generated parsed triples with classification and exact quote integrity."""
    raw=[]
    for h,relation,t in parse_rebel(output):
        mapped=RELATION_MAP.get(relation.casefold())
        raw.append({'h':h,'r_text':relation,'r':mapped,'t':t,'sentence_id':sentence_id,
                    'surface_anchored':anchored(sentence,h,t),
                    'quote':sentence,'source_sha256':hashlib.sha256(sentence.encode()).hexdigest(),
                    'model':model})
    return raw

def accepted(raw):
    return [x for x in raw if x['r'] and x['surface_anchored']]

def verify_quote(t,sents):
    i=t['sentence_id'];return 0<=i<len(sents) and sents[i]==t['quote'] and hashlib.sha256(sents[i].encode()).hexdigest()==t['source_sha256']

def gold_matches(triples,doc):
    """Read doc gold only AFTER all candidates were generated. Strict alias-directed positive-gold recall."""
    found=0;with_evidence=0;examples=[]
    for lab in doc['labels']:
        if lab['r'] not in RELATION_MAP.values():continue
        h,t=lab['h'],lab['t']
        ha={norm(z['name']) for z in doc['vertexSet'][h]};ta={norm(z['name']) for z in doc['vertexSet'][t]}
        matches=[x for x in triples if x['r']==lab['r'] and norm(x['h']) in ha and norm(x['t']) in ta]
        if matches:
            found+=1;with_evidence+=int(any(x['sentence_id'] in set(lab.get('evidence',[])) for x in matches))
            examples.append({'h':h,'t':t,'r':lab['r'],'prediction':matches[0]})
    return found,with_evidence,examples