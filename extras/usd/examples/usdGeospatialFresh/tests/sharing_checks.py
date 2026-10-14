from pathlib import Path
import sys,json,numpy as np
from pxr import Usd,Sdf,UsdGeom,Gf
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tests'))
from scene import Reader,BINDING
from fixtures import wkt,stage
from profiles import declare,discover
from run_workflows import native,dump
lib=Usd.Stage.CreateNew(str(ROOT/'fixtures/crs-library.usda'));p=lib.DefinePrim('/CRS','CoordinateReferenceSystem');lib.SetDefaultPrim(p);p.GetAttribute('crs:wkt').Set(wkt(4979));declare(p,False,True);lib.GetRootLayer().Save()
s=stage(ROOT/'fixtures/sharing.usda');local=s.DefinePrim('/Defs','Scope');d=s.DefinePrim('/Defs/Geographic','CoordinateReferenceSystem');d.GetAttribute('crs:wkt').Set(wkt(4979));jobs=[]
for name,kind in [('Referenced','reference'),('Inherited','inherit')]:
 p=UsdGeom.Xform.Define(s,'/World/'+name).GetPrim();p.AddAppliedSchema(BINDING);p.GetAttribute('crs:position').Set((0,0,0))
 if kind=='reference':p.GetReferences().AddReference('crs-library.usda','/CRS')
 else:p.GetInherits().AddInherit('/Defs/Geographic')
 jobs.append({'kind':'model','stage':str(ROOT/'fixtures/sharing.usda'),'path':str(p.GetPath()),'points':[[0,0,0],[1,0,0]],'output_wkt':wkt(4978)})
declare(s.GetDefaultPrim(),True,True);s.GetRootLayer().Save();n=native(jobs,'sharing');answer=[]
for job,result in zip(jobs,n):
 py=Reader(s).coordinates(job['path'],job['points'],wkt(4978));oracle=[[6378137,0,0],[6378137,1,0]];assert result['success'];np.testing.assert_allclose(result['coordinates'],oracle,atol=1e-8,rtol=0);np.testing.assert_allclose(py['coordinates'],oracle,atol=1e-8,rtol=0)
 answer.append({'path':job['path'],'passed':True,'composed_wkt':str(s.GetPrimAtPath(job['path']).GetAttribute('crs:wkt').Get()),'max_difference_m':float(np.max(np.linalg.norm(np.array(py['coordinates'])-result['coordinates'],axis=1)))})
dump('sharing.json',{'passed':True,'bare_library_dependency':discover(lib)['state'],'bindings':answer});print('Reference and inherit sharing: both readers match the equatorial oracle; bare library known-none.')
