from pathlib import Path
import json, subprocess, sys
ROOT=Path(__file__).resolve().parent
verifier=ROOT/'verification'/'kv5_verify.py'
completed=json.loads((ROOT/'output-completions.json').read_text())
directory=ROOT/'structure'; directory.mkdir(exist_ok=True)
logs=[]
for job,meta in completed.items():
    if not job.startswith('v5_'): continue
    q=job.split('_')[1]
    files=[ROOT/f for f in meta['files']]
    main=ROOT/'outputs'/(job+'.md')
    ordered=[main]+[f for f in files if f!=main]
    combined=directory/(job+'-combined.md')
    combined.write_text('\n\n'.join(p.read_text() for p in ordered))
    dest=directory/(job+'.json')
    p=subprocess.run([sys.executable,str(verifier),'run',str(combined),
                      '--source',str(ROOT/'blind'/'texts'/(q+'.txt')),'--json-out',str(dest)],capture_output=True,text=True)
    logs.append({'job':job,'raw_components':[str(p.relative_to(ROOT)) for p in ordered],
                 'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    # 明示された現在値は読者向け報告の最初のスコア・四面表、台帳は最初の完全表。
    # 自動選択の判定も残し、原出力は変更しない。
    selected=directory/(job+'-selected.json')
    sp=subprocess.run([sys.executable,str(verifier),'run',str(combined),
                       '--source',str(ROOT/'blind'/'texts'/(q+'.txt')),'--json-out',str(selected),
                       '--score','1','--ledger','1','--tally','1'],capture_output=True,text=True)
    logs[-1]['explicit_selection']={'score':1,'ledger':1,'tally':1,'exit_code':sp.returncode,
                                  'stdout':sp.stdout,'stderr':sp.stderr}
(directory/'execution-log.json').write_text(json.dumps(logs,ensure_ascii=False,indent=2))
print(json.dumps([{'job':r['job'],'exit_code':r['exit_code']} for r in logs]))
