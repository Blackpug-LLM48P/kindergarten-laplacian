from pathlib import Path
import json, hashlib, datetime
from collections import Counter

ROOT=Path(__file__).resolve().parent

def positions(text,fragment):
    out=[]; offset=0
    if not fragment: return []
    while (p:=text.find(fragment,offset))>=0:
        out.append([p,p+len(fragment)]); offset=p+1
    return out

def validate(path):
    data=json.loads(path.read_text())
    assert data['role']=='llm'
    report={'file':str(path.relative_to(ROOT)), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'outputs':[], 'errors':[]}
    for inp in data['inputs']:
        q=inp['input_id']; packet=ROOT/'audit-packets'/q
        source=(packet/'source.txt').read_text()
        ref=json.loads((packet/'reference.json').read_text())
        expected={r['ref_id']:r for r in ref['groups'] if r['status']=='accepted'}
        for output in inp['outputs']:
            alias=output['output_alias']
            files={p.name:p.read_text() for p in packet.glob(alias+'*.md')}
            def check_span(span):
                name=Path(span['file']).name
                text=span['text']
                hits=positions(files.get(name,''),text)
                if not hits: report['errors'].append({'input':q,'output':alias,'span_file':name,'text':text})
                return {'file':name,'positions':hits,'text':text}
            cs=output['correspondence']
            ids=[r['ref_id'] for r in cs]
            assert set(ids)==set(expected) and len(ids)==len(set(ids)), (q,alias,ids)
            for row in cs:
                row['validated_spans']=[check_span(s) for s in row['evidence_spans']]
                problem=expected[row['ref_id']]['polarity']=='problem'
                allowed={'DET','PEND','HOLD','MISS'} if problem else {'FUN','FPEND','FHOLD','FMISS','FERR'}
                assert row['events'] and set(row['events'])<=allowed
                if set(row['events']) & {'PEND','FPEND'}:
                    assert all(row['pend_checks'][k] for k in ['relation_and_quotes','specific_material','decision_branch'])
                if set(row['events']) & {'MISS','FMISS'}:
                    assert len(row['events'])==1
            parent_ids=[p['parent_id'] for p in output['parents']]
            assert len(parent_ids)==len(set(parent_ids))
            for parent in output['parents']:
                parent['validated_span']=check_span(parent)
                assert parent['claims'] or parent.get('duplicate_of')  # cc: 重複親のみ claims 空を許容（集計は重複親を除外）
                for claim in parent['claims']:
                    hits=positions(parent['text'],claim['text'])
                    if not hits: report['errors'].append({'input':q,'output':alias,'claim_id':claim['claim_id'],'text':claim['text']})
                    claim['positions_within_parent']=hits
                    assert claim['stance'] in ['P','K','U']
                    assert claim['support'] in ['SUP','UNSUP','SPLIT','UNRESOLVED']
                    for quote in claim.get('source_quotes',[]):
                        if isinstance(quote,dict): quote=quote.get('text',quote.get('quote',''))
                        if not positions(source,quote): report['errors'].append({'input':q,'output':alias,'claim_id':claim['claim_id'],'source_quote':quote})
                    for rid in claim.get('ref_ids',[]):
                        assert rid in {r['ref_id'] for r in ref['groups']}
            report['outputs'].append({'input_id':q,'alias':alias,'parents':len(output['parents']),
                                      'claims':sum(len(p['claims']) for p in output['parents']),
                                      'references':len(cs),'audit_complete':output['audit_complete']})
    return report,data

reports=[]
(ROOT/'audit-validation').mkdir(exist_ok=True)
for path in sorted((ROOT/'audits').glob('*.json')):
    if path.stem.endswith('-corrections'): continue
    report,data=validate(path)
    reports.append(report)
    (ROOT/'audit-validation'/(path.stem+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2))
(ROOT/'audit-validation-summary.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2))
print(json.dumps({'audit_files':len(reports),'outputs':sum(len(r['outputs']) for r in reports),
                  'errors':sum(len(r['errors']) for r in reports)},ensure_ascii=False))
