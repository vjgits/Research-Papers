import json,pathlib
from pger_v86_relation import RELATIONS
# Author-generated semantic challenge. NOT independent human annotations.
rels=['directed_by','produced_by','written_by','born_in','located_in']
verbs={k:RELATIONS[k] for k in rels}
records=[]
for k,pred in enumerate(rels):
 for t in range(6):
  sub=(f'Aster Film {t+1}' if pred in ('directed_by','produced_by') else f'Aster Novel {t+1}' if pred=='written_by' else f'Mira Person {t+1}' if pred=='born_in' else f'Luna Village {t+1}')
  obj=(f'Bela Person {t+1}' if pred in ('directed_by','produced_by','written_by') else f'Bela Town {t+1}' if pred=='born_in' else f'Bela County {t+1}')
  other=(f'Carlo Person {t+1}' if pred in ('directed_by','produced_by','written_by') else f'Carlo Town {t+1}' if pred=='born_in' else f'Carlo County {t+1}')
  verb=verbs[pred]
  ent=[f'{sub} {verb} {obj}.',f'{sub} {verb} {obj} and reviewed by {other}.',f'In 1999, {sub} {verb} {obj}; the announcement mentioned {other}.']
  neutral=[f'{sub} {verb} {other} and produced by {obj}.' if pred=='directed_by' else f'{sub} {verb} {other}; a separate article discussed {obj}.',
   f'{sub} was discussed with {obj} in an interview, and {other} wrote a review.',
   f'{sub} {verb} {other}, while {obj} only discussed the project.']
  negverb=verb[4:] if verb.startswith('was ') else verb[3:] if verb.startswith('is ') else verb
  be='is' if verb.startswith('is ') else 'was'
  contra=[f'{sub} {be} not {negverb} {obj}.',f'{sub} {be} never {negverb} {obj}.',
   f'{sub} {verb} {other}, and explicitly {be} not {negverb} {obj}.']
  for label,variants in [('entailment',ent),('neutral',neutral),('contradiction',contra)]:
   for v,sentence in enumerate(variants):
    records.append(dict(id=f'{pred}_{t}_{label}_{v}',premise=sentence,hypothesis=f'{sub} {verb} {obj}.',expected=label,relation=pred,subject=sub,object=obj,origin='authored_template'))
records.extend([
 dict(id='kalank_director_false',premise='Kalank was directed by Abhishek Varman and produced by Karan Johar.',hypothesis='Kalank was directed by Karan Johar.',expected='neutral',relation='directed_by',subject='Kalank',object='Karan Johar',origin='v85_observed_error'),
 dict(id='kalank_producer_true',premise='Kalank was directed by Abhishek Varman and produced by Karan Johar.',hypothesis='Kalank was produced by Karan Johar.',expected='entailment',relation='produced_by',subject='Kalank',object='Karan Johar',origin='v85_observed_error')])
out=pathlib.Path(__file__).with_name('contrastive_relation_cases_v86.json')
out.write_text(json.dumps({'description':'Deterministic author-generated contrastive tests, not human-independent benchmark; explicit relation distinctions and negation', 'cases':records},indent=2))
print(len(records),out)
