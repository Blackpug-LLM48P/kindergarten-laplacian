from pathlib import Path
import json,hashlib,zipfile
ROOT=Path(__file__).resolve().parent
assert (ROOT/'final-integrity.json').exists()
assert (ROOT/'REPORT.md').exists() and (ROOT/'METRIC-DETAILS.md').exists()
assert json.loads((ROOT/'metrics.json').read_text())['primary_complete']
def eligible(p):
 return p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and p.name!='SHA256SUMS.txt' and not p.name.startswith('build-')
files=sorted(p for p in ROOT.rglob('*') if eligible(p))
manifest='\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ROOT).as_posix() for p in files)+'\n'
(ROOT/'SHA256SUMS.txt').write_text(manifest)
files.append(ROOT/'SHA256SUMS.txt')
archive=ROOT.parent/'kanshiki-v5-manual-rehearsal-20261003.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in files: z.write(p,ROOT.name+'/'+p.relative_to(ROOT).as_posix())
with zipfile.ZipFile(archive) as z: assert z.testzip() is None
print(json.dumps({'path':str(archive),'files':len(files),'bytes':archive.stat().st_size,
                  'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}))
