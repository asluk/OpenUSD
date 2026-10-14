from pathlib import Path
import json,hashlib,datetime
ROOT=Path(__file__).resolve().parents[1]
for name in ['generation-record.json','evidence/provider-reader-comparison.json','evidence/workflow-summary.json']:
 p=ROOT/name
 if p.exists():(ROOT/'evidence'/('v2-'+p.name)).write_bytes(p.read_bytes())
p=ROOT/'native/reader.cpp';s=p.read_text();a='auto out=proj_trans(operation,PJ_FWD,in);';assert s.count(a)==1;s=s.replace(a,'proj_errno_reset(operation);auto out=proj_trans(operation,PJ_FWD,in);');p.write_text(s)
record=json.loads((ROOT/'generation-record.json').read_text());record.update(candidate_generation=3,frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),revision_reason='PROJ selected and applied the available Colorado grid, but the caller read a stale operation error from probing unavailable alternative grids. Clear errno immediately before the actual transform. This is an implementation fix; proposal unchanged.',candidate_files=[])
for directory in ['src','native','tests','schema','delivery']:
 for p in sorted((ROOT/directory).rglob('*')):
  if p.is_file() and p.suffix not in ('.pyc','.exe','.obj') and '__pycache__' not in str(p):record['candidate_files'].append({'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(ROOT/'generation-record.json').write_text(json.dumps(record,indent=2))
