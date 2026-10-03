from pathlib import Path
import json, hashlib, shutil, datetime

ROOT = Path(__file__).resolve().parent
refs = json.loads((ROOT / 'reference.json').read_text())
plan = json.loads((ROOT / 'plan.json').read_text())
completed=json.loads((ROOT/'output-completions.json').read_text()) if (ROOT/'output-completions.json').exists() else {}
operator_map = {'Q005':'W02-I01','Q008':'W01-I01','Q019':'W12-I01',
                'Q010':'W10-I01','Q012':'W10-I02','Q013':'W11-I02',
                'Q007':'W12-I04','Q017':'W12-I03'}
mapping = []
for q in plan['selected']:
    packet = ROOT / 'audit-packets' / q
    packet.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / 'blind' / 'texts' / (q+'.txt'), packet / 'source.txt')
    ref = next(x for x in refs['inputs'] if x['input_id'] == q)
    (packet / 'reference.json').write_text(json.dumps(ref, ensure_ascii=False, indent=2))
    conditions = ['v5','B2'] if int(hashlib.sha256(q.encode()).hexdigest(),16)%2 else ['B2','v5']
    for alias, condition in zip(['O1','O2'], conditions):
        raw = ROOT / 'outputs' / f'{condition}_{q}.md'
        mapping.append({'input_id':q,'work_input':operator_map[q],'group':operator_map[q].split('-')[0],
                        'output_alias':alias,'condition':condition,'raw_file':str(raw.relative_to(ROOT))})
        if raw.stem not in completed: continue
        target = packet / (alias+'.md')
        if target.exists():
            assert target.read_bytes() == raw.read_bytes(), 'Raw output changed after packet copy'
        else: shutil.copyfile(raw,target)
        for extra in sorted(raw.parent.glob(raw.stem+'_*.md')):
            dest = packet / (alias + extra.stem[len(raw.stem):] + '.md')
            if dest.exists(): assert dest.read_bytes() == extra.read_bytes()
            else: shutil.copyfile(extra,dest)
        mapping[-1]['raw_files'] = [str(p.relative_to(ROOT)) for p in sorted(raw.parent.glob(raw.stem+'*.md'))]
(ROOT / 'operator-output-map.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2))
print(json.dumps({'complete_pairs':[q for q in plan['selected'] if all((ROOT/'audit-packets'/q/(a+'.md')).exists() for a in ['O1','O2'])],
                  'outputs_observed':sum((ROOT/m['raw_file']).exists() for m in mapping)}))
