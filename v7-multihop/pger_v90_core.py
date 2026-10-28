"""PGER V9.0 inexpensive relation-generation sentence selection.

Greedy coverage and lexical cue selection are standard optimization heuristics;
these are controls for a future counterfactual proof-gap scheduler, NOT novel claims.
No gold labels or evaluation annotations enter this module.
"""
import re
from collections import Counter

# Deliberately frozen generic surface cues (not gold relation labels).
CUES = re.compile(r'\b(born|died|country|located|capital|headquarter|directed|written|author|married|spouse|father|mother|child|citizen|worked|employed|educated|university|member|team|administrative|border)\b', re.I)
NAME = re.compile(r'\b(?:[A-Z][a-zÀ-ÿ\'-]{2,}|[A-Z]{2,})(?:\s+(?:(?:of|the|and|de|van|von)\s+)?[A-Z][a-zÀ-ÿ\'-]{2,}){0,3}\b')
WORD = re.compile(r'[a-z]{3,}')

def named_strings(sentence):
    return set(m.group(0).casefold() for m in NAME.finditer(sentence))

def select_fixed_first(sentences, budget=2):
    return [sid for sid, _ in sentences[:budget]]

def select_lexical(sentences, budget=2):
    scored=[]
    for sid,text in sentences:
        n=len(named_strings(text))
        score=3*len(CUES.findall(text))+min(n*(n-1)//2, 12)+min(len(text),240)/1000
        scored.append((-score,sid))
    return [sid for _,sid in sorted(scored)[:budget]]

def select_coverage(sentences, budget=2):
    """Greedy marginal pair coverage + novel entities + relation cues per sentence.

    This is an established set-coverage pattern, not proof/entailment or an original primitive.
    The pair set approximates possible, not validated, relationships.
    """
    scored={}; pairs={}; entities={}
    for sid,text in sentences:
        ents=sorted(named_strings(text));entities[sid]=set(ents)
        pairs[sid]={(ents[i],ents[j]) for i in range(len(ents)) for j in range(i+1,len(ents))}
        scored[sid]=(text,len(CUES.findall(text)))
    chosen=[];seen_ents=set();seen_pairs=set()
    for _ in range(min(budget,len(sentences))):
        pool=[]
        for sid,text in sentences:
            if sid in chosen:continue
            newpairs=len(pairs[sid]-seen_pairs)
            newents=len(entities[sid]-seen_ents)
            cue_count=scored[sid][1]
            # Candidate-relation utility proxy; no gold labels or answer data.
            utility=2*min(newpairs,20)+1.25*min(newents,12)+1.5*min(cue_count,5)+min(len(text),300)/500
            pool.append((-utility,sid))
        if not pool:break
        sid=min(pool)[1];chosen.append(sid)
        seen_ents|=entities[sid];seen_pairs|=pairs[sid]
    return chosen

def selected_ids(sentences,method):
    if method=='first2':return select_fixed_first(sentences,2)
    if method=='lexical2':return select_lexical(sentences,2)
    if method=='coverage2':return select_coverage(sentences,2)
    if method=='coverage3':return select_coverage(sentences,3)
    if method=='full6':return [sid for sid,_ in sentences]
    raise ValueError('unknown method '+str(method))