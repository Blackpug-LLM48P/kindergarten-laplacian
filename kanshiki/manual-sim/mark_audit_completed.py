from pathlib import Path
import json,hashlib,datetime,sys
ROOT=Path(__file__).resolve().parent
p=ROOT/'audit-completions.json'
data=json.loads(p.read_text()) if p.exists() else {}
for filename in sys.argv[1:]:
 if filename in data: continue
 path=ROOT/'audits'/filename
 assert path.exists()
 data[filename]={'agent_reported_completed':True,
                 'completion_observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
p.write_text(json.dumps(data,ensure_ascii=False,indent=2))
print(len(data))
