from pathlib import Path
import json, hashlib, datetime, sys
root=Path(__file__).resolve().parent
p=root/'output-completions.json'
data=json.loads(p.read_text()) if p.exists() else {}
for job in sys.argv[1:]:
    if job in data: continue
    files=sorted((root/'outputs').glob(job+'*.md'))
    assert (root/'outputs'/(job+'.md')) in files
    data[job]={'agent_reported_completed':True,'full_source_and_prompt_read_reported':True,
               'completion_observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'attempts':1,'fork':'none','files':{
                 str(x.relative_to(root)):{'sha256':hashlib.sha256(x.read_bytes()).hexdigest(),
                                          'characters':len(x.read_text()),'bytes':x.stat().st_size}
                 for x in files}}
p.write_text(json.dumps(data,ensure_ascii=False,indent=2))
print(len(data))
