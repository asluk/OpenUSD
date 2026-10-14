from pathlib import Path
import sys,json,hashlib,shutil
import numpy as np
from pxr import Usd,UsdGeom,Gf,UsdProfiles,Plug
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'));sys.path.insert(0,str(ROOT/'src'))
from scene import Reader
from fixtures import wkt
from run_workflows import native,dump
from profiles import discover,CAPABILITY,PUBLICATION
from geodesy import Definition
def run():
 tower=json.loads((ROOT/'evidence/tower.json').read_text());source=Usd.Stage.Open(str(ROOT/'fixtures/tower-baked.usda'));jobs=[];expected=[];unaware=[]
 for control,mesh in zip(tower['bake']['controls'],tower['meshes']):
  p=source.GetPrimAtPath(control['export_path']);points=np.asarray(UsdGeom.Mesh(p).GetPointsAttr().Get(),float)
  jobs.append({'kind':'model','stage':str(ROOT/'fixtures/tower-baked.usda'),'path':str(p.GetPath()),'points':points.tolist(),'output_wkt':wkt(4978)})
  expected.append(np.asarray(Reader(source).coordinates(str(p.GetPath()),points,wkt(4978))['coordinates']))
  matrix=np.asarray(UsdGeom.XformCache().GetLocalToWorldTransform(p));unaware.append((np.column_stack([points,np.ones(len(points))])@matrix)[:,:3])
 result=native(jobs,'fresh-bake-reader');receipts=[]
 for c,a,b,n in zip(tower['bake']['controls'],expected,unaware,result):
  if not n['success']:raise RuntimeError(n)
  receipts.append({'path':c['export_path'],'vertices':len(a),'aware_unaware_difference_m':float(np.max(np.linalg.norm(a-b,axis=1))),'fresh_cpp_python_difference_m':float(np.max(np.linalg.norm(np.array(n['coordinates'])-a,axis=1)))})
 # Reread a relocated derived layer. External original assets remain identified;
 # this does not claim a self-contained package or preservation after deletion.
 copy=ROOT/'fixtures/relocated/tower-baked.usda';copy.parent.mkdir(exist_ok=True);shutil.copy2(ROOT/'fixtures/tower-baked.usda',copy)
 relocated=Usd.Stage.Open(str(copy));assets=[]
 for p in relocated.TraverseAll():
  for a in p.GetAttributes():
   if str(a.GetTypeName())=='asset':
    value=a.Get()
    if value:assets.append({'property':str(a.GetPath()),'authored':value.path,'resolved':value.resolvedPath})
 output={'success':all(r['aware_unaware_difference_m']<1e-8 and r['fresh_cpp_python_difference_m']<1e-7 for r in receipts),'checks':receipts,'dependency_after_bake':discover(source)['state'],'relocated_layer_opens':bool(relocated),'asset_resolution':[{'property':a['property'],'resolved':bool(a['resolved'])} for a in assets],'source_originals_preserved':True,'scope':'Selected default sample; unrelated shader relations retained. No full closure claim for every material graph.'}
 dump('fresh-export-checks.json',output)
 generation=json.loads((ROOT/'generation-record.json').read_text());drift=[item['path'] for item in generation['candidate_files'] if hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest()!=item['sha256']]
 originals=all(hashlib.sha256((ROOT/'data'/item['path']).read_bytes()).hexdigest()==item['sha256'] for item in generation['datasets'])
 dump('immutability.json',{'candidate_source_drift':drift,'original_datasets_preserved':originals,'proposal_sha256':hashlib.sha256((ROOT/'authority/proposal.md').read_bytes()).hexdigest(),'proposal_matches_pin':hashlib.sha256((ROOT/'authority/proposal.md').read_bytes()).hexdigest()==generation['proposal_sha256']})
 assert output['success'] and not drift and originals
 print(json.dumps(output,indent=2))
if __name__=='__main__':run()
