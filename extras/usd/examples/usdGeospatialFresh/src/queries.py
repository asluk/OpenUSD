import numpy as np
from errors import ResolutionFailure
from geodesy import Definition,Operations
from scene import Reader

def relative_frame(stage,source_path,target_path,output,time=None):
    reader=Reader(stage);q=reader.selected_output(output)
    chart=q if q.kind!='geographic' else Definition(q.ecef.to_wkt())
    a=np.asarray(reader.coordinates(source_path,(0,0,0),chart,time)['coordinates'])
    b=np.asarray(reader.coordinates(target_path,(0,0,0),chart,time)['coordinates'])
    ja=reader.derivative(source_path,chart,time);jb=reader.derivative(target_path,chart,time)
    try:inverse=np.linalg.inv(jb)
    except np.linalg.LinAlgError as e:raise ResolutionFailure('singular-required-inverse','Relative target frame is singular') from e
    return {'linear_from_to':(inverse@ja).tolist(),'translation_from_to':(inverse@(a-b)).tolist(),'scene_chart_wkt':chart.normal,'coverage':'Certified affine maps only; no nonlinear global relative-frame claim'}

def relative_position(stage,source_path,target_path,output,time=None):
    reader=Reader(stage);q=reader.selected_output(output)
    a=np.asarray(reader.coordinates(source_path,(0,0,0),q,time)['coordinates'])
    b=np.asarray(reader.coordinates(target_path,(0,0,0),q,time)['coordinates'])
    return {'from':a.tolist(),'to':b.tolist(),'from_minus_to':(a-b).tolist(),'units':q.unit_names,'meaning':'angular/height component difference' if q.kind=='geographic' else 'Cartesian component difference'}

def physical_distance(stage,source_path,target_path,output,time=None):
    reader=Reader(stage);q=reader.selected_output(output)
    if q.dimension!=3:raise ResolutionFailure('missing-height','Physical 3D distance requires height')
    chart=Definition(q.ecef.to_wkt())
    a=np.asarray(reader.coordinates(source_path,(0,0,0),chart,time)['coordinates'])
    b=np.asarray(reader.coordinates(target_path,(0,0,0),chart,time)['coordinates'])
    return {'distance_metres':float(np.linalg.norm(a-b)),'measure':'associated-geocentric Euclidean 3D separation'}

def bounds(stage,path,points,output,time=None,numeric_origin=(0,0,0),continuous=False):
    if continuous:raise ResolutionFailure('uncertified-continuous-domain','This prototype does not certify nonlinear images of continuous surfaces or time intervals')
    result=Reader(stage).scene_points(path,points,output,time,numeric_origin)
    p=np.asarray(result['scene_points'])
    return {'minimum':p.min(axis=0).tolist(),'maximum':p.max(axis=0).tolist(),'scene_chart_wkt':result['scene_chart_wkt'],'numeric_origin':result['numeric_origin'],'coverage':'Queried finite points; straight polygonal faces only when these are all vertices'}
