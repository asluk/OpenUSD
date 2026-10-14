from pathlib import Path
import sys,numpy as np,json
from pxr import Sdf
from pyproj import CRS
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from fixtures import stage,bind,wkt
from test_assembly import instance_scene
from run_workflows import native,dump
jobs=[]
def save(s,name,job):
 p=ROOT/'fixtures'/('control-final-'+name+'.usda');s.GetRootLayer().Export(str(p));job['stage']=str(p);jobs.append(job)
s=stage();bind(s,'/World/A',CRS.from_proj4('+proj=longlat +ellps=clrk66 +towgs84=100,200,300 +no_defs').to_3d().to_wkt())
save(s,'bound',{'kind':'model','path':'/World/A','points':[[0,0,0],[1,0,0],[0,1,0]],'output_wkt':wkt(4978)})
s=stage();p=s.DefinePrim('/World/Invalid','Scope');p.AddAppliedSchema('GeospatialCRSBindingAPI');p.CreateAttribute('crs:wkt',Sdf.ValueTypeNames.Token,variability=Sdf.VariabilityUniform).Set(wkt(4979));bind(s,'/World/Invalid/Model')
save(s,'role',{'kind':'model','path':'/World/Invalid/Model','points':[[0,0,0]],'output_wkt':wkt(4978)})
s,inst,mesh=instance_scene()
save(s,'id',{'kind':'instance','path':str(inst.GetPath()),'prototype':str(mesh.GetPath()),'index':0,'points':[[0,0,0]],'output_wkt':wkt(4978)})
jobs.append({'kind':'convert','source_wkt':wkt(7789),'output_wkt':wkt(9988),'points':[[6378137,100,100]]})
r=native(jobs,'focused-final');np.testing.assert_allclose(r[0]['coordinates'],[[6378306.4,200,300],[6378306.4,201,300],[6378306.4,200,301]],atol=1e-7,rtol=0)
assert r[1].get('code')=='invalid-binding-role',r[1]
identity=r[2]['instance_identity'];assert identity['id']==1234 and identity['index']==0 and identity['prototype_relative_path']=='Mesh',r[2]
assert not r[3]['success'] and 'epoch' in r[3]['code'],r[3]
dump('focused-native-checks.json',{'passed':True,'checks':4,'results':r})
print('4 focused native checks passed: authored BOUNDCRS, enclosing binding role, instance ID, deferred epoch operation.')
