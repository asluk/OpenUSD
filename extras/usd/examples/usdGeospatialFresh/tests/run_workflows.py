"""Frozen-candidate execution, with explicit independent expectation records."""
from pathlib import Path
import sys,json,csv,os,subprocess,hashlib,time
import numpy as np
from pxr import Usd,UsdGeom,Gf
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tests'))
from fixtures import wkt
from geodesy import Definition,Operations,configure_resources
from measurements import resolve,association,cf,geojson,geotiff
from scene import Reader
from profiles import discover,publisher_audit
from export import geometry_bake
from errors import ResolutionFailure
E=ROOT/'evidence';D=ROOT/'fixtures';configure_resources(ROOT.parent/'geospatial-model-resources')
def dump(name,value):
 (E/name).write_text(json.dumps(value,indent=2,default=lambda v:v.tolist() if isinstance(v,np.ndarray) else list(v)),encoding='utf-8')
def native(jobs,name):
 inp=E/(name+'-input.json');out=E/(name+'-output.json');inp.write_text(json.dumps(jobs),encoding='utf-8')
 env=os.environ.copy();env['PATH']=';'.join([str(ROOT.parent/'geospatial-proj-tiff/bin'),'C:/git/usd-geospatial-fresh/inst/bin','C:/git/usd-geospatial-fresh/inst/lib','C:/Users/aluk/AppData/Local/Programs/Python/Python310',env['PATH']]);env['PROJ_DATA']=str(ROOT.parent/'geospatial-proj-tiff/share/proj')
 result=subprocess.run([str(ROOT/'native-build/geospatial_fresh.exe'),str(inp),str(out),str(ROOT/'schema'),str(ROOT.parent/'geospatial-model-resources')],env=env,capture_output=True,text=True)
 (E/(name+'-stderr.log')).write_text(result.stderr,encoding='utf-8')
 if result.returncode:raise RuntimeError(result.stderr)
 return json.loads(out.read_text())
def read_csv(path):
 rows=list(csv.DictReader(path.open(encoding='utf-8-sig')));fields=list(rows[0])
 if 'Latitude' in fields[1] or any('Latitude' in f for f in fields):
  keys=[next(f for f in fields if 'Longitude' in f),next(f for f in fields if 'Latitude' in f),next(f for f in fields if 'Ellipsoidal height' in f)]
 elif any('Site easting' in f for f in fields):keys=[fields[1],fields[2],fields[3]]
 else:keys=fields[1:4]
 return [r[fields[0]] for r in rows],np.array([[float(r[k]) for k in keys] for r in rows]),keys
def run():
 started=time.time();checks=[];jobs=[];expected=[];cases=[]
 for region in ['France','Colorado']:
  paths=sorted((ROOT/'data'/region).glob('*Coordinates.csv'));defs={};points={};ids={}
  for path in paths:
   key=path.name[:2];text=path.with_name(path.name.replace('Coordinates.csv','WKT2.txt')).read_text()
   try:defs[key]=Definition(text)
   except ResolutionFailure as ex:
    checks.append({'kind':'deferred-dataset','region':region,'dataset':path.name,'code':ex.code});continue
   ids[key],points[key],_=read_csv(path)
  target='03' if region=='France' else '01';targetdef=defs[target]
  # The expected arrays are provider-authored counterparts, not another reader.
  for key in defs:
   if key==target:continue
   target_by_id=dict(zip(ids[target],points[target]));oracle=np.array([target_by_id[i] for i in ids[key]])
   jobs.append({'kind':'convert','source_wkt':defs[key].authored,'output_wkt':targetdef.authored,'points':points[key].tolist()});expected.append(oracle)
   py=Operations().convert(points[key],defs[key],targetdef)
   if region=='France':error=np.max(np.linalg.norm(py-oracle,axis=1))
   else:
    ec=Definition(targetdef.ecef.to_wkt());ops=Operations();error=np.max(np.linalg.norm(ops.convert(py,targetdef,ec)-ops.convert(oracle,targetdef,ec),axis=1))
   checks.append({'kind':'provider-control','region':region,'source':key,'points':len(py),'max_provider_error_m':float(error),'tolerance_m':.002,'passed':bool(error<=.002),'oracle':'Matched provider point IDs; independent rounded counterpart coordinates'})
   cases.append({'name':region+' '+key,'python':py,'coordinate_definition':targetdef})
 partner=native(jobs,'partner');pair=[]
 for c,n in zip(cases,partner):
  if not n['success']:pair.append({'name':c['name'],'failure':n});continue
  q=c['coordinate_definition'];a=np.array(n['coordinates']);b=c['python']
  if q.kind=='geographic':
   ec=Definition(q.ecef.to_wkt());ops=Operations();error=np.max(np.linalg.norm(ops.convert(a,q,ec)-ops.convert(b,q,ec),axis=1))
  else:error=np.max(np.linalg.norm((a-b)*q.semantic_units,axis=1))
  pair.append({'name':c['name'],'points':len(a),'max_reader_difference_m':float(error),'attributed_accuracy_m':[o['attributed_accuracy_m'] for o in n['operations']]})
 dump('provider-controls.json',checks);dump('provider-reader-comparison.json',pair)
 measurements=[];mjobs=[];mexpected=[]
 for name,path,out in [('railway','/World/Railway',wkt(2154)),('climate','/World/Climate',wkt(4978)),('city','/World/Heat',wkt(2154))]:
  stage=Usd.Stage.Open(str(D/(name+'.usda')));prim=stage.GetPrimAtPath(path);data=resolve(prim,out)
  asset,fmt,field,domain,definition=association(prim);decoder={'CF':cf,'GeoJSON':geojson,'GeoTIFF':geotiff}[fmt];raw=decoder(asset,field,domain,definition);valid=~raw['mask']
  mjobs.append({'kind':'measurement','stage':str(D/(name+'.usda')),'path':path,'points':raw['coordinates'][valid].tolist(),'output_wkt':out});mexpected.append(data['coordinates'][valid])
  np.savez(E/(name+'-resolved.npz'),coordinates=data['coordinates'],values=np.array(data['values']) if name!='railway' else np.zeros(len(data['coordinates'])),mask=data['mask'],indices=np.asarray(data['indices'],dtype=object))
  measurements.append({'name':name,'samples':len(raw['coordinates']),'masked':int(sum(raw['mask'])),'source_values_unchanged':np.array_equal(np.asarray(raw['values'])[valid],np.asarray(data['values'])[valid]),'operations':data['operations'],'domain':'2D horizontal only' if definition.dimension==2 else '3D with declared ellipsoidal height','source_coordinate_order':'Explicit metadata roles, mapped by named dimensions'})
 nm=native(mjobs,'measurement');
 for item,py,n in zip(measurements,mexpected,nm):
  if not n['success']:item['native_failure']=n
  else:item['max_reader_difference_native_units']=float(np.max(np.linalg.norm(np.asarray(n['coordinates'])-py,axis=1)))
 dump('measurements.json',measurements)
 # Original LandXML is a producer import, not a fourth schema data:format.
 survey=np.load(D/'landxml-domains.npz');definition=Definition((ROOT/'data/Colorado/03_Westminster_Site_Calibration_WKT2.txt').read_text());ec=Definition(definition.ecef.to_wkt());coords=Operations().convert(survey['coordinates'],definition,ec)
 np.savez(E/'survey-resolved.npz',coordinates=coords,starts=survey['starts']);n=native([{'kind':'convert','points':survey['coordinates'].tolist(),'source_wkt':definition.authored,'output_wkt':ec.normal}],'survey')[0]
 dump('survey.json',{'vertices':len(coords),'parts':len(survey['starts'])-1,'max_reader_difference_m':float(np.max(np.linalg.norm(np.asarray(n['coordinates'])-coords,axis=1))) if n['success'] else None,'native':{'success':n['success']},'meaning':'Producer-parsed absolute LandXML; no local-anchor reinterpretation'})
 s=Usd.Stage.Open(str(D/'tower-source.usda'));r=Reader(s);tower=[];tjobs=[];tpy=[];origin=np.array(r.coordinates('/World/Site/Tower',[(0,0,0)],wkt(4978))['coordinates'])[0]
 for p in s.Traverse():
  mesh=UsdGeom.Mesh(p)
  if mesh and mesh.GetPointsAttr().HasValue():
   points=np.asarray(mesh.GetPointsAttr().Get(),float);values=np.asarray(r.coordinates(str(p.GetPath()),points,wkt(4978))['coordinates']);tpy.append(values)
   tjobs.append({'kind':'model','stage':str(D/'tower-source.usda'),'path':str(p.GetPath()),'points':points.tolist(),'output_wkt':wkt(4978)})
   tower.append({'path':str(p.GetPath()),'vertices':len(points)})
 tn=native(tjobs,'tower');
 for item,values,n in zip(tower,tpy,tn):
  if not n['success']:item['failure']=n
  else:item['max_reader_difference_m']=float(np.max(np.linalg.norm(np.asarray(n['coordinates'])-values,axis=1)))
 bake=geometry_bake(s,D/'tower-baked.usda',wkt(4979),numeric_origin=origin)
 # This ordinary bake is used for unaware-USD/Storm; native coordinates replace
 # point payloads below the same double origin, preserving unrelated data.
 dst=Usd.Stage.Open(str(D/'tower-baked.usda'))
 for control,n in zip(bake['controls'],tn):
  if not n['success']:raise RuntimeError('Native tower evaluation failed')
  p=UsdGeom.Mesh(dst.GetPrimAtPath(control['export_path']));p.GetPointsAttr().Set(np.asarray(np.asarray(n['coordinates'])-origin,np.float32).tolist())
 dst.GetRootLayer().Save()
 np.savez(E/'tower-cartesian.npz',origin=origin,**{'mesh'+str(i):v for i,v in enumerate(tpy)})
 dump('ov-input.json',{'numeric_origin':origin.tolist(),'meshes':[{'path':item['path'],'points':(values-origin).tolist()} for item,values in zip(tower,tpy)]});dump('tower.json',{'meshes':tower,'vertices':sum(t['vertices'] for t in tower),'bake':bake,'render_path':'Native C++ points in ordinary USD bake; Storm is not a geospatial evaluation engine'})
 pj=[{'kind':'profiles','stage':str(D/(name+'.usda'))} for name in ['required','none','unknown','stale']]
 results=native(pj,'profiles');profile=[]
 for job,n in zip(pj,results):
  st=Usd.Stage.Open(job['stage'],Usd.Stage.LoadNone);py=discover(st)
  profile.append({'name':Path(job['stage']).stem,'python_state':py['state'],'native_state':n.get('state'),'payloads_loaded_python':len(py['payloads_loaded']),'payloads_loaded_native':n.get('payload_load_count'),'publisher_audit':publisher_audit(job['stage'])})
 dump('profiles.json',profile)
 # Source bytes and pinned proposal remain unchanged throughout resolution.
 gen=json.loads((ROOT/'generation-record.json').read_text());source_preserved=all(hashlib.sha256((ROOT/'data'/f['path']).read_bytes()).hexdigest()==f['sha256'] for f in gen['datasets'])
 summary={'elapsed_s':time.time()-started,'provider_controls':checks,'provider_reader_comparison':pair,'measurements':measurements,'tower_vertices':sum(t['vertices'] for t in tower),'source_preservation':source_preserved,'scope':'Finite point/sample queries and supported affine exports; continuous nonlinear domains not certified'}
 dump('workflow-summary.json',summary);print(json.dumps(summary,default=lambda v:v.tolist() if isinstance(v,np.ndarray) else str(v),indent=2))
if __name__=='__main__':run()
