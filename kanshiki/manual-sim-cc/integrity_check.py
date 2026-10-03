from pathlib import Path
import hashlib,json,datetime
ROOT=Path(__file__).resolve().parent
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
plan=json.loads((ROOT/'plan.json').read_text())
checks={}
for q,d in plan['source_ids_sha256'].items(): assert digest(ROOT/'blind/texts'/(q+'.txt'))==d,q
checks['frozen_inputs']=8
context=json.loads((ROOT/'execution-context.json').read_text())
for name,d in context['prompts_sha256'].items(): assert digest(ROOT/'prompts'/name)==d,name
checks['frozen_prompts']=2
af=json.loads((ROOT/'annotations-freeze.json').read_text())
for name,d in af['hashes'].items(): assert digest(ROOT/name)==d,name
checks['original_annotations_unchanged']=3
rf=json.loads((ROOT/'reference-freeze.json').read_text())
for name,d in rf['files'].items(): assert digest(ROOT/name)==d,name
checks['reference_and_rules_unchanged']=True
completed=json.loads((ROOT/'output-completions.json').read_text())
expected={c+'_'+q for c in ['v5','B2'] for q in plan['selected']}
assert set(completed)==expected
for job,record in completed.items():
 assert record['agent_reported_completed'] and record['attempts']==1
 for name,info in record['files'].items(): assert digest(ROOT/name)==info['sha256'],name
checks['original_completed_outputs_unchanged']=16
mapping=json.loads((ROOT/'operator-output-map.json').read_text())
for m in mapping:
 packet=ROOT/'audit-packets'/m['input_id']; main=ROOT/m['raw_file']
 for f in m['raw_files']:
  raw=ROOT/f; suffix=raw.stem[len(main.stem):]
  assert digest(raw)==digest(packet/(m['output_alias']+suffix+'.md'))
 assert digest(packet/'source.txt')==plan['source_ids_sha256'][m['input_id']]
ref=json.loads((ROOT/'reference.json').read_text())
for inp in ref['inputs']:
 assert json.loads((ROOT/'audit-packets'/inp['input_id']/'reference.json').read_text())==inp
checks['anonymous_audit_packets_exact']=8
summaries=json.loads((ROOT/'audit-validation-summary.json').read_text())
audit_completed=json.loads((ROOT/'audit-completions.json').read_text())
assert len(audit_completed)==10
assert set(audit_completed)=={'primary-'+q+'.json' for q in plan['selected']}|{'secondary-1.json','secondary-2.json'}
for name,info in audit_completed.items(): assert digest(ROOT/'audits'/name)==info['sha256'],name
assert len(summaries)==10
for s in summaries: assert s['sha256']==digest(ROOT/s['file']),s['file']
errors=[dict(e,file=s['file']) for s in summaries for e in s['errors']]  # cc: 完全一致エラーは停止せず記録（監査票は書き換えない）
checks['recorded_exact_match_errors']=errors
assert sum(len(s['outputs']) for s in summaries)==24
assert all(o['audit_complete'] for s in summaries for o in s['outputs'])
checks['validated_audit_files']=10
checks['validated_output_audits']=24
metrics=json.loads((ROOT/'metrics.json').read_text())
assert metrics['primary_complete'] and len(metrics['primary_rows'])==16
assert {(r['input_id'],r['condition']) for r in metrics['primary_rows']}=={(q,c) for q in plan['selected'] for c in ['v5','B2']}
assert len({(r['input_id'],r['condition']) for r in metrics['primary_rows']})==len(metrics['primary_rows'])
checks['primary_output_metrics']=16
comparison=json.loads((ROOT/'audit-comparison.json').read_text())
assert comparison['outputs_compared']==8
checks['secondary_audit_outputs']=8
assert len(list((ROOT/'structure').glob('v5_Q*-selected.json')))==8
checks['structural_checks_recorded']=8
checks['source_integrity']=json.loads((ROOT/'source-integrity.json').read_text())
checks['timestamp']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(ROOT/'final-integrity.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
print(json.dumps(checks,ensure_ascii=False))
