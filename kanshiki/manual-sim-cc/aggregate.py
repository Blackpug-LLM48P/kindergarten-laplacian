"""Descriptive reference values only; no formal-kit mutations."""
from pathlib import Path
import json, statistics
from collections import Counter
ROOT=Path(__file__).resolve().parent
mapping=json.loads((ROOT/'operator-output-map.json').read_text())
lookup={(x['input_id'],x['output_alias']):x for x in mapping}
reference=json.loads((ROOT/'reference.json').read_text())
refs={i['input_id']:{r['ref_id']:r for r in i['groups']} for i in reference['inputs']}
metric_rows=[]
for path in sorted((ROOT/'audit-validation').glob('primary-*.json')):
    data=json.loads(path.read_text())
    for inp in data['inputs']:
        q=inp['input_id']
        for output in inp['outputs']:
            if not output['audit_complete']: continue
            meta=lookup[(q,output['output_alias'])]
            fixed={k:v for k,v in refs[q].items() if v['status']=='accepted' and not v['rule_excluded']}
            denominators={p:sum(r['polarity']==p for r in fixed.values()) for p in ['problem','function']}
            counts=Counter(e for c in output['correspondence'] if c['ref_id'] in fixed for e in set(c['events']))
            relations={'RP':denominators['problem'],'RF':denominators['function']}
            for event in ['DET','PEND','HOLD','MISS','FUN','FPEND','FHOLD','FMISS','FERR']:
                n=denominators['problem' if event in ['DET','PEND','HOLD','MISS'] else 'function']
                relations[event]={'n':counts[event],'denominator':n,'rate':counts[event]/n if n else None}
            coexisting=[{'ref_id':c['ref_id'],'events':c['events']} for c in output['correspondence']
                        if c['ref_id'] in fixed and len(set(c['events']))>1]
            coexistence={'any_multiple_events':len(coexisting),'relation_denominator':len(fixed),
                         'FUN_and_FERR':sum({'FUN','FERR'}<=set(c['events']) for c in coexisting),
                         'recognition_and_hold':sum(bool(set(c['events'])&{'DET','FUN'}) and
                                                    bool(set(c['events'])&{'PEND','HOLD','FPEND','FHOLD'}) for c in coexisting),
                         'relations':coexisting}
            parents=[p for p in output['parents'] if not p.get('duplicate_of')]
            doubtful=[p for p in parents if any(c['stance']=='P' for c in p['claims'])]
            flags=Counter()
            for parent in doubtful:
                labels={c['support'] for c in parent['claims']}
                flags['pure_SUP']+=labels=={'SUP'}
                flags['has_UNSUP']+='UNSUP' in labels
                flags['mixed']+= {'SUP','UNSUP'} <= labels
                flags['branch']+='SPLIT' in labels
                flags['unresolved']+='UNRESOLVED' in labels
            n=len(doubtful)
            flags={key:{'n':flags[key],'denominator':n,'rate':flags[key]/n if n else None}
                   for key in ['pure_SUP','has_UNSUP','mixed','branch','unresolved']}
            claims=Counter(c['stance']+'_'+c['support'] for p in parents for c in p['claims'])
            held=[r for r in output['correspondence'] if set(r['events'])&{'PEND','HOLD','FPEND','FHOLD'}]
            hold_counts={k:sum(bool(r['pend_checks'][k]) for r in held) for k in ['relation_and_quotes','specific_material','decision_branch']}
            hold_counts['all_three']=sum(all(r['pend_checks'][k] for k in ['relation_and_quotes','specific_material','decision_branch']) for r in held)
            metric_rows.append({'input_id':q,'condition':meta['condition'],'group':meta['group'],
              'acquisition_state':output['acquisition_state'],'audit_complete':output['audit_complete'],
              'relations':relations,'parents':{'total':len(parents),'doubtful':n,'duplicates_excluded':len(output['parents'])-len(parents),
                                              'flags':flags,'claims':dict(claims),'claims_total':sum(claims.values())},
              'hold_quality':{'denominator':len(held),'counts':hold_counts,
                              'rates':{k:v/len(held) if held else None for k,v in hold_counts.items()},
                              'scope':'held correspondence to fixed accepted references only'},
              'coexistence':coexistence,
              'condition_guess':output.get('condition_guess')})

def get_rate(row,key):
    if key in row['relations']: return row['relations'][key]['rate']
    return row['parents']['flags'][key]['rate']

keys=['DET','PEND','HOLD','MISS','FUN','FPEND','FHOLD','FMISS','FERR',
      'pure_SUP','has_UNSUP','mixed','branch','unresolved']
paired_by_input=[]
for q in json.loads((ROOT/'plan.json').read_text())['selected']:
    pair={r['condition']:r for r in metric_rows if r['input_id']==q}
    if set(pair)!={'v5','B2'}: continue
    paired_by_input.append({'input_id':q,'group':pair['v5']['group'],
                           'v5_minus_B2':{key:(get_rate(pair['v5'],key)-get_rate(pair['B2'],key))
                                          if get_rate(pair['v5'],key) is not None and get_rate(pair['B2'],key) is not None
                                          else None for key in keys}})
groups=[]
for group in sorted({r['group'] for r in metric_rows}):
    subset=[r for r in metric_rows if r['group']==group]
    value={'group':group,'metrics':{}}
    for key in keys:
        value['metrics'][key]={}
        for condition in ['v5','B2']:
            rows=[r for r in subset if r['condition']==condition]
            values=[get_rate(r,key) for r in rows if get_rate(r,key) is not None]
            value['metrics'][key][condition]={'mean':statistics.mean(values) if values else None,'valid_Q':len(values),'NA_Q':len(rows)-len(values)}
        byq={}
        for row in subset: byq.setdefault(row['input_id'],{})[row['condition']]=row
        diffs=[get_rate(pair['v5'],key)-get_rate(pair['B2'],key) for pair in byq.values()
               if set(pair)=={'v5','B2'} and get_rate(pair['v5'],key) is not None and get_rate(pair['B2'],key) is not None]
        value['metrics'][key]['paired_difference']={'mean':statistics.mean(diffs) if diffs else None,'valid_Q':len(diffs)}
    groups.append(value)
overall={}
for key in keys:
    overall[key]={}
    for label in ['v5','B2','paired_difference']:
        values=[g['metrics'][key][label]['mean'] for g in groups if g['metrics'][key][label]['mean'] is not None]
        overall[key][label]={'mean':statistics.mean(values) if values else None,'valid_groups':len(values),'NA_groups':len(groups)-len(values)}

pooled={}
for condition in ['v5','B2']:
    rows=[r for r in metric_rows if r['condition']==condition]
    pooled[condition]={'metric_order':'relation/parent equal-weight alternative, NOT work-group average',
                       'outputs':len(rows),'RF':sum(r['relations']['RF'] for r in rows),'RP':sum(r['relations']['RP'] for r in rows)}
    for key in keys:
        values=[r['relations'][key] if key in r['relations'] else r['parents']['flags'][key] for r in rows]
        n=sum(v['n'] for v in values); den=sum(v['denominator'] for v in values)
        pooled[condition][key]={'n':n,'denominator':den,'rate':n/den if den else None}
    pooled[condition]['doubtful_parents']=sum(r['parents']['doubtful'] for r in rows)
    pooled[condition]['zero_doubt_outputs']=sum(r['parents']['doubtful']==0 for r in rows)
    pooled[condition]['any_UNSUP_outputs']=sum(r['parents']['flags']['has_UNSUP']['n']>0 for r in rows)

expected_keys={(q,c) for q in json.loads((ROOT/'plan.json').read_text())['selected'] for c in ['v5','B2']}
observed_keys={(r['input_id'],r['condition']) for r in metric_rows}
assert len(observed_keys)==len(metric_rows), 'Duplicate primary output key'
result={'kind':'LLM rehearsal descriptive reference values', 'primary_rows':metric_rows,
        'coverage':{'expected_outputs':len(expected_keys),'completed_output_keys':sorted(observed_keys),
                    'missing_output_keys':sorted(expected_keys-observed_keys)},
        'paired_by_input':paired_by_input,
        'work_group_averages':groups,'group_equal_weight_overall':overall,'pooled_alternative':pooled,
        'primary_complete':observed_keys==expected_keys}
(ROOT/'metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({'outputs':len(metric_rows),'primary_complete':result['primary_complete'],'pooled':pooled},ensure_ascii=False))
