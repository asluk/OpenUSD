from pathlib import Path
import json,os,subprocess,hashlib
import numpy as np
from pxr import Usd,UsdGeom
from pyproj import CRS,Geod,proj_version_str
from .runtime import Runtime,ContractError,dependency,factors
from .datasets import resolved

def execute_python(job,stage=None):
    stage=stage or Usd.Stage.Open(job['stage']);stage.SetInterpolationType(Usd.InterpolationTypeHeld if job['interpolation']=='held' else Usd.InterpolationTypeLinear)
    runtime=Runtime(stage,job['output_wkt'],job['time']);before=runtime.snapshot();claim=dependency(stage)
    queries=[{'prim':q['prim'],'coordinates':runtime.placement(stage.GetPrimAtPath(q['prim']),q['points']).tolist()} for q in job['queries']]
    geometry=runtime.geometry() if job.get('geometry') else {}
    record={'queries':queries,'geometry':geometry,'operations':runtime.operations,'source_unchanged':runtime.snapshot()==before,'dependency':claim,'engine_version':proj_version_str}
    if geometry:record['geometry_sources']=runtime.geometry_sources
    if job.get('frames'):record['frames']={p:runtime.frame(stage.GetPrimAtPath(p)) for p in job['frames']}
    if geometry:
        points=np.concatenate([np.array(v) for v in geometry.values()])
        record['polygonal_bounds']={'min':points.min(axis=0).tolist(),'max':points.max(axis=0).tolist(),'domain':'resolved vertices and straight polygonal faces; no continuous source-face certificate'}
    if job.get('relative'):
        request=job['relative'];a=stage.GetPrimAtPath(request['from']);b=stage.GetPrimAtPath(request['to'])
        record['relative_position']=runtime.inverse_placement(b,runtime.placement(a,[[0,0,0]])).tolist()
    if job.get('dataset'):
        source,coords=resolved(stage.GetPrimAtPath(job['dataset']),runtime)
        record['dataset_coordinates']=coords.tolist()
        record['association']={k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in source.items() if k not in ['crs','coordinates','values']}
        record['measurement_values']=source['values'].tolist() if isinstance(source['values'],np.ndarray) else source['values']
        record['measurement_sha256']=hashlib.sha256(json.dumps(record['measurement_values'],allow_nan=True).encode()).hexdigest()
        record['source_coordinates_sha256']=hashlib.sha256(np.asarray(source['coordinates']).tobytes()).hexdigest()
    if not record['source_unchanged']: raise AssertionError('Source changed during execution')
    return record

def compare(a,b,wkt):
    output=CRS.from_wkt(wkt);maximum=0;count=0
    def check(x,y):
        nonlocal maximum,count
        x,y=np.array(x),np.array(y)
        if x.shape!=y.shape: raise AssertionError('Coordinate/value-domain shape mismatch')
        if not x.size:return
        if output.is_geographic:
            f=factors(output);geod=Geod(a=output.ellipsoid.semi_major_metre,b=output.ellipsoid.semi_minor_metre)
            distance=np.abs(geod.inv(x[:,0]*f[0]*180/np.pi,x[:,1]*f[1]*180/np.pi,y[:,0]*f[0]*180/np.pi,y[:,1]*f[1]*180/np.pi)[2])
            if x.shape[1]==3:distance=np.hypot(distance,(x[:,2]-y[:,2])*f[2])
        else:distance=np.linalg.norm((x-y)*factors(output),axis=1)
        err=float(np.max(distance));maximum=max(maximum,err);count+=len(x)
        if err>0.001: raise AssertionError(f'Comparable coordinate results exceed 1mm: {err}')
    if [q['prim'] for q in a['queries']]!=[q['prim'] for q in b['queries']]:raise AssertionError('Query association mismatch')
    for x,y in zip(a['queries'],b['queries']):check(x['coordinates'],y['coordinates'])
    if set(a['geometry'])!=set(b['geometry']):raise AssertionError('Geometry association mismatch')
    for path in a['geometry']:check(a['geometry'][path],b['geometry'][path])
    if 'dataset_coordinates' in a:check(a['dataset_coordinates'],b['dataset_coordinates'])
    if 'relative_position' in a:
        if np.max(abs(np.array(a['relative_position'])-b['relative_position']))>1e-8:raise AssertionError('Relative placement mismatch')
    if 'frames' in a:
        if set(a['frames'])!=set(b['frames']):raise AssertionError('Frame association mismatch')
        for path,frame in a['frames'].items():
            check([frame['origin']],[b['frames'][path]['origin']])
            error=np.max(abs((np.array(frame['jacobian'])-b['frames'][path]['jacobian'])*factors(output)))
            if error>1e-6:raise AssertionError('Frame derivative agreement exceeds 1 micrometre per stage unit')
    if a['geometry']:
        for key in ['min','max']:check([a['polygonal_bounds'][key]],[b['polygonal_bounds'][key]])
    return {'coordinate_count':count,'max_distance_metres':maximum,'acceptance_metres':0.001,'distance_measure':'ellipsoidal geodesic plus height' if output.is_geographic else 'metric Euclidean'}

def native_job(job,out,native,resources,env):
    from .datasets import read_source
    request={**job,'resources':resources,'schema_directory':str(Path(__file__).parents[1]/'schema/generated/plugInfo.json')}
    if job.get('dataset'):
        stage=Usd.Stage.Open(job['stage']);source=read_source(stage.GetPrimAtPath(job['dataset']))
        request['dataset_coordinates']=source['coordinates'].tolist()
    request_path=out/(job['name']+'.native-job.json');result_path=out/(job['name']+'.native.json')
    request_path.write_text(json.dumps(request),encoding='utf-8')
    run=subprocess.run([str(native),str(request_path),str(result_path)],env=env,capture_output=True,text=True,timeout=600)
    (out/(job['name']+'.native.log')).write_text(run.stdout+run.stderr,encoding='utf-8')
    if run.returncode:raise RuntimeError(run.stderr)
    return json.loads(result_path.read_text(encoding='utf-8'))
