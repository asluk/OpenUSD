from pathlib import Path
import sys,json,numpy as np
from pxr import UsdGeom,Sdf
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'));sys.path.insert(0,str(ROOT/'src'))
from fixtures import stage,bind,wkt
from test_assembly import instance_scene
from scene import Reader
from run_workflows import native,dump

def run():
 jobs=[];oracles=[];names=[]
 def save(name,s,job,oracle):
  path=ROOT/'fixtures'/('control-'+name+'.usda');s.GetRootLayer().Export(str(path));job['stage']=str(path);jobs.append(job);oracles.append(oracle);names.append(name)
 for up,unit in [('Z',1),('Y',.01)]:
  s=stage(up=up,unit=unit);bind(s,'/World/A')
  save('axis-'+up,s,{'kind':'model','path':'/World/A','points':[[1,2,3]],'output_wkt':wkt(4978)},[[6378137+3,1,2]] if up=='Z' else [[6378137+.02,.01,-.03]])
 s=stage();bind(s,'/World',pos=(30,20,0));a=bind(s,'/World/A');UsdGeom.Xformable(s.GetDefaultPrim()).AddTranslateOp().Set((1000,0,0))
 save('nested-absolute',s,{'kind':'model','path':'/World/A','points':[[0,0,0]],'output_wkt':wkt(4978)},[[6378137,0,0]])
 s=stage();a=bind(s,'/World/A');UsdGeom.Xformable(a).AddTranslateOp().Set((100,0,0));c=UsdGeom.Xform.Define(s,'/World/A/Reset');c.SetResetXformStack(True);c.AddTranslateOp().Set((10,0,0))
 save('descendant-reset',s,{'kind':'model','path':'/World/A/Reset','points':[[0,0,0]],'output_wkt':wkt(4978)},[[6378137,10,0]])
 for h,name,code in [(90,'attitude',None),(180,'halfturn','ambiguous-half-turn'),(180-1e-7,'nearhalfturn',None),(360,'same-pose',None)]:
  s=stage();a=bind(s,'/World/A');a.GetAttribute('crs:orientation').Set((0,0,0),0);a.GetAttribute('crs:orientation').Set((h,0,0),2)
  point=[[0,1,0]];oracle=code or Reader(s).coordinates('/World/A',point,wkt(4978),1)['coordinates']
  save(name,s,{'kind':'model','path':'/World/A','points':point,'output_wkt':wkt(4978),'time':1},oracle)
 for independent,child in [(False,False),(True,False),(False,True)]:
  s,pi,mesh=instance_scene(independent,child_binding=child)
  save('instance-'+str(independent)+'-'+str(child),s,{'kind':'instance','path':str(pi.GetPath()),'prototype':str(mesh.GetPath()),'index':0,'points':[[0,0,0]],'output_wkt':wkt(4978)},[[6378137,10,0]])
 output=native(jobs,'native-controls');receipts=[]
 for name,expected,result in zip(names,oracles,output):
  if isinstance(expected,str):passed=not result['success'] and result['code']==expected;error=None
  else:error=float(np.max(np.linalg.norm(np.asarray(result.get('coordinates',[]))-expected,axis=1))) if result['success'] else None;passed=error is not None and error<1e-7
  receipts.append({'name':name,'passed':passed,'max_error_m':error,'expected_failure':expected if isinstance(expected,str) else None,'result':result})
 dump('native-controls.json',receipts);assert all(r['passed'] for r in receipts),[r for r in receipts if not r['passed']]
 print(json.dumps({'native_controls':len(receipts),'passed':True}))
if __name__=='__main__':run()
