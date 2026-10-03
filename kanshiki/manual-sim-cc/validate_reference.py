"""Integrity check for AI candidate reference and derivation of agreement."""
from pathlib import Path
import json,itertools,hashlib,datetime
ROOT=Path(__file__).resolve().parent
def main():
    ann=json.loads((ROOT/'annotation-validation.json').read_text())
    assert ann['status']=='complete'
    raw={r['relation_id']:r for r in ann['normalized']}
    ref=json.loads((ROOT/'reference.json').read_text());used=[];groups=[]
    for inp in ref['inputs']:
        q=inp['input_id'];text=(ROOT/'blind'/'texts'/f'{q}.txt').read_text()
        for g in inp['groups']:
            assert g['status'] in ('accepted','split','rejected','alignment_ambiguous')
            assert g['polarity'] in ('problem','function','unresolved')
            assert g['members']
            for rid in g['members']+g.get('duplicate_ids',[]):
                assert rid in raw and raw[rid]['input_id']==q;used.append(rid)
            agents=[raw[x]['annotator_id'] for x in g['members']]
            assert len(set(agents))==len(agents)
            for side in ('a','b'):
                quote=g.get('quote_'+side,'')
                if quote:assert quote in text,(g['ref_id'],side)
            if g['status']=='accepted':assert g['polarity'] in ('problem','function')
            groups.append(dict(g,input_id=q))
    assert len(set(used))==len(used), 'annotation reused across reference groups'
    assert set(used)==set(raw), ('unaccounted annotations',set(raw)-set(used))
    assert {i['input_id'] for i in ref['inputs']}==set(json.loads((ROOT/'plan.json').read_text())['selected'])
    pairs=[]
    for a,b in itertools.combinations('ABC',2):
        ns={a:0,b:0};m=0;pol=0;item=0;byq=[]
        for inp in ref['inputs']:
            qa=qb=qm=qpol=qitem=0
            for g in inp['groups']:
                if g['status']=='alignment_ambiguous':continue
                mem={raw[x]['annotator_id']:raw[x] for x in g['members']}
                qa+=a in mem;qb+=b in mem
                if a in mem and b in mem:
                    qm+=1;qpol+=mem[a]['polarity']==mem[b]['polarity'];qitem+=set(mem[a]['item_ids'])==set(mem[b]['item_ids'])
            ns[a]+=qa;ns[b]+=qb;m+=qm;pol+=qpol;item+=qitem
            byq.append(dict(input_id=inp['input_id'],n_a=qa,n_b=qb,matches=qm,dice=2*qm/(qa+qb) if qa+qb else None,jaccard=qm/(qa+qb-qm) if qa+qb-qm else None,polarity_agreement=qpol/qm if qm else None,item_set_agreement=qitem/qm if qm else None))
        pairs.append(dict(pair=a+b,n_a=ns[a],n_b=ns[b],matches=m,dice=2*m/(ns[a]+ns[b]) if ns[a]+ns[b] else None,jaccard=m/(ns[a]+ns[b]-m) if ns[a]+ns[b]-m else None,polarity_agreement=pol/m if m else None,item_set_agreement=item/m if m else None,by_input=byq))
    result=dict(pairs=pairs,raw_annotations=len(raw),duplicates=sum(len(g.get('duplicate_ids',[])) for g in groups),group_status_counts={s:sum(g['status']==s for g in groups) for s in ('accepted','split','rejected','alignment_ambiguous')},eligible_problem=sum(g['status']=='accepted' and g['polarity']=='problem' and not g['rule_excluded'] for g in groups),eligible_function=sum(g['status']=='accepted' and g['polarity']=='function' and not g['rule_excluded'] for g in groups))
    if (ROOT/'reference-freeze.json').exists():
        assert json.loads((ROOT/'agreement.json').read_text())==result
        freeze=json.loads((ROOT/'reference-freeze.json').read_text())
        for name,digest in freeze['files'].items():
            assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest, name
    else:
        assert not list((ROOT/'outputs').glob('*.md')), 'Cannot freeze reference after outputs'
        (ROOT/'agreement.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
        freeze=dict(timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),files={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('reference.json','annotation-validation.json','agreement.json','audit-rules-v1.md')},role='llm_candidate_reference_only',frozen_before_outputs=True)
        (ROOT/'reference-freeze.json').write_text(json.dumps(freeze,indent=2))
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
