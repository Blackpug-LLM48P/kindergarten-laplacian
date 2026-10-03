"""Validate copied annotations without altering raw agents' records."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
IDS=json.loads((ROOT/'plan.json').read_text())['selected']
def occurrences(text, quote):
    if not quote:return []
    result=[];start=0
    while True:
        at=text.find(quote,start)
        if at<0:return result
        result.append([at,at+len(quote)]);start=at+1
def main():
    reports=[];normalized=[]
    for name in ('A','B','C'):
        path=ROOT/'annotations'/f'{name}.json'
        if not path.exists():continue
        data=json.loads(path.read_text()); seen=[]; relations=set(); checks=[]
        assert data['role']=='llm' and data['annotator_id']==name
        for inp in data['inputs']:
            q=inp['input_id'];assert q in IDS;seen.append(q)
            assert inp['read_complete'] is True
            text=(ROOT/'blind'/'texts'/f'{q}.txt').read_text()
            for r in inp['relations']:
                rid=r['relation_id']; assert rid not in relations;relations.add(rid)
                assert r['polarity'] in ('problem','function','unresolved')
                x=dict(r,input_id=q,annotator_id=name)
                for side in ('a','b'):
                    quote=r.get(f'quote_{side}','');pos=occurrences(text,quote)
                    x[f'quote_{side}_positions']=pos
                    checks.append(dict(relation_id=rid,side=side,required=bool(quote),exact=bool(pos) if quote else None,occurrences=len(pos)))
                normalized.append(x)
        assert sorted(seen)==sorted(IDS) and len(seen)==len(IDS)
        reports.append(dict(annotator=name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),inputs=len(seen),relations=len(relations),quotes=checks))
    out=dict(status='complete' if len(reports)==3 else 'partial',reports=reports,normalized=normalized)
    (ROOT/'annotation-validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
    bad=[(r['annotator'],x['relation_id'],x['side']) for r in reports for x in r['quotes'] if x['required'] and not x['exact']]
    print(json.dumps(dict(annotators=len(reports),relations=len(normalized),invalid_quotes=bad),ensure_ascii=False))
if __name__=='__main__':main()
