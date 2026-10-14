from pathlib import Path
import json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tests'))
from fixtures import wkt
from scene import Reader
from pxr import Usd
jobs=[{'kind':'model','stage':str(ROOT/'fixtures'/name),'path':path,'points':[[0,0,0],[1,0,0],[0,1,0],[0,0,1]],'output_wkt':wkt(4978)} for name,path in [('analytic.usda','/World/Anchor'),('france.usda','/World/Model')]]
(ROOT/'evidence/native-preflight-input.json').write_text(json.dumps(jobs),encoding='utf-8')
env=os.environ.copy();env['PATH']=';'.join(['C:/Users/aluk/Documents/Codex/2026-09-21/have/work/geospatial-proj-tiff/bin','C:/git/usd-geospatial-fresh/inst/bin','C:/git/usd-geospatial-fresh/inst/lib','C:/Users/aluk/AppData/Local/Programs/Python/Python310','C:/Users/aluk/Documents/Codex/2026-09-21/have/work/geospatial-proj-tiff/bin',env['PATH']]);env['PROJ_DATA']='C:/Users/aluk/Documents/Codex/2026-09-21/have/work/geospatial-proj-tiff/share/proj'
result=subprocess.run([str(ROOT/'native-build/geospatial_fresh.exe'),str(ROOT/'evidence/native-preflight-input.json'),str(ROOT/'evidence/native-preflight-output.json'),str(ROOT/'schema'),str(ROOT.parent/'geospatial-model-resources')],env=env,capture_output=True,text=True)
print('exit',result.returncode);print(result.stderr[:3000])
if result.returncode:raise SystemExit(result.returncode)
native=json.loads((ROOT/'evidence/native-preflight-output.json').read_text())
for job,n in zip(jobs,native):
    p=Reader(Usd.Stage.Open(job['stage'])).coordinates(job['path'],job['points'],job['output_wkt'])
    print(json.dumps({'stage':Path(job['stage']).name,'native':n,'python':p['coordinates']},ensure_ascii=False))
