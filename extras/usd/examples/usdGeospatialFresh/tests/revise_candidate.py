from pathlib import Path
import json,hashlib,datetime
ROOT=Path(__file__).resolve().parents[1]
previous=json.loads((ROOT/'generation-record.json').read_text());(ROOT/'evidence/generation-v1.json').write_text(json.dumps(previous,indent=2))
p=ROOT/'native/reader.cpp';s=p.read_text()
def change(a,b):
 global s
 assert s.count(a)==1,(a[:80],s.count(a));s=s.replace(a,b)
change('double unit;bool yup;','double unit;bool yup;std::unique_ptr<CRS>workECEF,workGeo;Vec workOrigin,workLL;')
change('if(!identity(a))originW=convert(e,position,source,working);','if(!identity(a)){originW=convert(e,position,source,working);if(working.kind=="geographic"){workECEF=std::make_unique<CRS>(e,working.geocentric());workGeo=std::make_unique<CRS>(e,working.geographic());workOrigin=convert(e,originW,working,*workECEF);workLL=convert(e,originW,working,*workGeo);}}')
change('CRS we(e,working.geocentric()),wg(e,working.geographic());auto o=convert(e,originW,working,we),ll=convert(e,originW,working,wg);auto ec=convert(e,w,working,we);return enuStage(unembed(ec-o,ll,&wg));','auto ec=convert(e,w,working,*workECEF);return enuStage(unembed(ec-workOrigin,workLL,workGeo.get()));')
change('CRS we(e,working.geocentric()),wg(e,working.geographic());auto o=convert(e,originW,working,we),ll=convert(e,originW,working,wg);return convert(e,o+embed(enu,ll,&wg),we,working);','return convert(e,workOrigin+embed(enu,workLL,workGeo.get()),*workECEF,working);')
p.write_text(s)
for name in ['run_workflows.py','native_preflight.py']:
 p=ROOT/'tests'/name;s=p.read_text()
 if name=='run_workflows.py':s=s.replace("['C:/git/usd-geospatial-fresh/inst/bin','C:/git/usd-geospatial-fresh/inst/lib','C:/Users/aluk/AppData/Local/Programs/Python/Python310',str(ROOT.parent/'geospatial-proj-tiff/bin'),env['PATH']]", "[str(ROOT.parent/'geospatial-proj-tiff/bin'),'C:/git/usd-geospatial-fresh/inst/bin','C:/git/usd-geospatial-fresh/inst/lib','C:/Users/aluk/AppData/Local/Programs/Python/Python310',env['PATH']]")
 else:s=s.replace("['C:/git/usd-geospatial-fresh/inst/bin'", "['C:/Users/aluk/Documents/Codex/2026-09-21/have/work/geospatial-proj-tiff/bin','C:/git/usd-geospatial-fresh/inst/bin'")
 p.write_text(s)
previous.update(candidate_generation=2,frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),candidate_files=[],revision_reason='v1 exposed loader collision with the SDK PROJ DLL and redundant per-vertex CRS parsing. Repair loader order and cache equivalent working charts; no proposal/model change. v1 receipt preserved.')
for directory in ['src','native','tests','schema','delivery']:
 for p in sorted((ROOT/directory).rglob('*')):
  if p.is_file() and p.suffix not in ('.pyc','.exe','.obj') and '__pycache__' not in str(p):previous['candidate_files'].append({'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(ROOT/'generation-record.json').write_text(json.dumps(previous,indent=2));print('Re-frozen candidate generation 2; proposal unchanged.')
