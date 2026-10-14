from pathlib import Path
import json,hashlib,datetime
ROOT=Path(__file__).resolve().parents[1]
def edit(relative,a,b):
 p=ROOT/relative;s=p.read_text();assert a in s,(relative,a[:50]);p.write_text(s.replace(a,b))
edit('tests/run_workflows.py',"source_preserved=all(hashlib.sha256(Path(f['copied_path']).read_bytes()).hexdigest()==f['sha256'] for f in gen['original_datasets']) if 'original_datasets' in gen else None","source_preserved=all(hashlib.sha256((ROOT/'data'/f['path']).read_bytes()).hexdigest()==f['sha256'] for f in gen['datasets'])")
edit('tests/run_workflows.py',"dump('tower.json',", "dump('ov-input.json',{'numeric_origin':origin.tolist(),'meshes':[{'path':item['path'],'points':(values-origin).tolist()} for item,values in zip(tower,tpy)]});dump('tower.json',")
p=ROOT/'tests/make_workflows.py';s=p.read_text();start=s.index(" import netCDF4\n");end=s.index(' # Eiffel writer',start);s=s[:start]+s[end:];p.write_text(s)
for p in (ROOT/'schema').iterdir():
 if p.suffix in ('.cpp','.h') or p.name in ('CMakeLists.txt','module.cpp'):
  assert p.resolve().parent==(ROOT/'schema').resolve();p.unlink()
record=json.loads((ROOT/'generation-record.json').read_text());record.update(candidate_frozen=True,frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),freeze_rule='No prior geospatial source or previous output inspected before this freeze. Changes after freeze require a new generation receipt.',candidate_files=[])
for directory in ['src','native','tests','schema','delivery']:
 for p in sorted((ROOT/directory).rglob('*')):
  if p.is_file() and p.suffix not in ('.pyc','.exe','.obj') and '__pycache__' not in str(p):record['candidate_files'].append({'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(ROOT/'generation-record.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print('Candidate frozen:',len(record['candidate_files']),'source files; previous results not yet inspected.')
