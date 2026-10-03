from pathlib import Path
import json
from collections import Counter
ROOT=Path(__file__).resolve().parent
mapping=json.loads((ROOT/'operator-output-map.json').read_text())
lookup={(m['input_id'],m['output_alias']):m['condition'] for m in mapping}
primary={}
for path in (ROOT/'audit-validation').glob('primary-*.json'):
    for inp in json.loads(path.read_text())['inputs']:
        for output in inp['outputs']: primary[(inp['input_id'],output['output_alias'])]=output
comparisons=[]
for path in (ROOT/'audit-validation').glob('secondary-*.json'):
    for inp in json.loads(path.read_text())['inputs']:
        for secondary in inp['outputs']:
            key=(inp['input_id'],secondary['output_alias'])
            if key not in primary: continue
            first=primary[key]
            pc={r['ref_id']:r for r in first['correspondence']}
            sc={r['ref_id']:r for r in secondary['correspondence']}
            ids=sorted(set(pc)&set(sc))
            disagreements=[{'ref_id':i,'primary_events':pc[i]['events'],'secondary_events':sc[i]['events'],
                            'primary_reason':pc[i]['reason'],'secondary_reason':sc[i]['reason']}
                           for i in ids if set(pc[i]['events'])!=set(sc[i]['events'])]
            def support_counts(output):
                parents=[p for p in output['parents'] if not p.get('duplicate_of')]
                doubtful=[p for p in parents if any(c['stance']=='P' for c in p['claims'])]
                return {'doubtful_parents':len(doubtful),
                        'has_UNSUP':sum(any(c['support']=='UNSUP' for c in p['claims']) for p in doubtful),
                        'branch':sum(any(c['support']=='SPLIT' for c in p['claims']) for p in doubtful),
                        'unresolved':sum(any(c['support']=='UNRESOLVED' for c in p['claims']) for p in doubtful),
                        'claims':sum(len(p['claims']) for p in parents)}
            # 一意の原出力位置・親境界・主張境界のみ。反復同文を辞書で縮約しない。
            def exact_claims(output):
                coordinates=Counter(); labels=Counter(); ambiguous=0
                for parent in output['parents']:
                    if parent.get('duplicate_of'): continue
                    pp=parent['validated_span']['positions']
                    for claim in parent['claims']:
                        cp=claim['positions_within_parent']
                        if len(pp)!=1 or len(cp)!=1:
                            ambiguous+=1; continue
                        coord=(parent['file'],pp[0][0],pp[0][1],pp[0][0]+cp[0][0],pp[0][0]+cp[0][1])
                        coordinates[coord]+=1
                        labels[(coord,claim['stance'],claim['support'])]+=1
                return coordinates,labels,ambiguous
            pcoords,plabels,pamb=exact_claims(first)
            scoords,slabels,samb=exact_claims(secondary)
            shared_count=sum((pcoords&scoords).values())
            shared_label_agreement=sum((plabels&slabels).values())
            comparisons.append({'input_id':key[0],'alias':key[1],'condition':lookup[key],
                                'relation_votes_compared':len(ids),'event_set_agreement_count':len(ids)-len(disagreements),
                                'disagreements':disagreements,
                                'primary_support':support_counts(first),'secondary_support':support_counts(secondary),
                                'exact_same_claim_and_parent_spans':shared_count,
                                'exact_same_claim_label_agreement':shared_label_agreement,
                                'ambiguous_claim_positions_excluded':{'primary':pamb,'secondary':samb},
                                'exact_span_only_note':'subset selected by extraction boundary equality; not overall support agreement'})
n=sum(x['relation_votes_compared'] for x in comparisons); a=sum(x['event_set_agreement_count'] for x in comparisons)
out={'outputs_compared':len(comparisons),'relation_votes':n,'event_set_agreement':a,
     'event_set_agreement_rate':a/n if n else None,'comparisons':comparisons,
     'interpretation':'Primary scores retained. Secondary disagreements are sensitivity evidence, not corrected truths.'}
(ROOT/'audit-comparison.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in out.items() if k!='comparisons'},ensure_ascii=False))
