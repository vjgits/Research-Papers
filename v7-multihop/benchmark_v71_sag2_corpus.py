"""Compatibility shim for the already-published exact SAG2 corpus adapter."""
from benchmark_v71_sag2_official import get as download,load,REF,REV
RELEASE=REV
SAG2_AUTHOR={k:{'corpus':v[0],'r5':v[1],'r10':v[2],'ae5':v[3],'ae10':v[4]} for k,v in REF.items()}
def official_records(name,root):
    unique,records=load(name,root)
    return unique,list(unique.values()),[{'id':r['id'],'question':r['q'],'gold':r['gold']} for r in records]
