import json
d=json.load(open('secondary-2.json'))
bad=[]
for inp in d['inputs']:
    q=inp['input_id']; src=open(f'{q}/source.txt').read()
    ref=json.load(open(f'{q}/reference.json'))
    acc={g['ref_id'] for g in ref['groups'] if g['status']=='accepted'}
    for o in inp['outputs']:
        rd=lambda f: open(f'{q}/{f}').read()
        got={c['ref_id'] for c in o['correspondence']}
        if got!=acc: bad.append((q,o['output_alias'],'refs',got,acc))
        for c in o['correspondence']:
            for s in c['evidence_spans']:
                if s['text'] not in rd(s['file']): bad.append((q,o['output_alias'],c['ref_id'],'span',s['text']))
        for m in o['other_reference_mentions']:
            for s in m['evidence_spans']:
                if s['text'] not in rd(s['file']): bad.append((q,o['output_alias'],m['ref_id'],'orm-span',s['text']))
        np=0;npd=0
        for p in o['parents']:
            if p['text'] not in rd(p['file']): bad.append((p['parent_id'],'parent'))
            for c in p['claims']:
                if c['text'] not in p['text']: bad.append((c['claim_id'],'claim',c['text']))
                for sq in c['source_quotes']:
                    if sq not in src: bad.append((c['claim_id'],'srcq',sq))
            if p['duplicate_of'] is None:
                np+=1
                if any(c['stance']=='P' for c in p['claims']): npd+=1
        print(q,o['output_alias'],'parents',np,'(+dup',len(o['parents'])-np,') P-parents',npd,[ (c['ref_id'],c['events']) for c in o['correspondence']])
print('ISSUES',bad)
