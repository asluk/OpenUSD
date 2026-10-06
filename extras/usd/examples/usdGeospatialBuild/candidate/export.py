"""New output-CRS assets, independently reread; no private resolved marker."""
from pathlib import Path
import numpy as np
from pxr import Sdf,Usd,UsdGeom,Gf,Vt
from .runtime import Runtime,factors
from .fixtures import attr,mark,claim
from .execution import coordinate_error

def geometry_export(job,record,path):
    source=Usd.Stage.Open(job['stage']);r=Runtime(source,job['output_wkt'],job['time'])
    output=r.scene_crs
    flattened=Usd.Stage.Open(source.Flatten())
    while True:
        instances=[p for p in flattened.Traverse() if p.IsInstance()]
        if not instances:break
        for p in instances:p.SetInstanceable(False)
    copy_layer=flattened.Flatten()
    dst=Usd.Stage.CreateNew(str(path));root=dst.DefinePrim('/Resolved','CoordinateReferenceSystem');dst.SetDefaultPrim(root)
    UsdGeom.SetStageMetersPerUnit(dst,r.unit);UsdGeom.SetStageUpAxis(dst,UsdGeom.GetStageUpAxis(source));dst.SetTimeCodesPerSecond(source.GetTimeCodesPerSecond())
    from review.wkt_profile import normalize
    attr(root,'crs:wkt',Sdf.ValueTypeNames.Token,normalize(output.to_wkt()),True)
    quantization=0.;source_paths={}
    for i,(old_path,coordinates) in enumerate(record['geometry'].items()):
        src=source.GetPrimAtPath(record.get('geometry_sources',{}).get(old_path,old_path));new_path=f'/Resolved/Part{i}'
        Sdf.CopySpec(copy_layer,src.GetPath(),dst.GetRootLayer(),Sdf.Path(new_path));p=dst.GetPrimAtPath(new_path)
        if p.IsInstance():p.SetInstanceable(False)
        for prop in list(p.GetProperties()):
            if prop.GetName().startswith(('crs:','xformOp:')) or prop.GetName()=='xformOpOrder':p.RemoveProperty(prop.GetName())
        p.SetMetadata('apiSchemas',Sdf.TokenListOp.CreateExplicit([]))
        center=np.array(coordinates[0]);local=r.stage_coordinates(coordinates,center);stored=local.astype(np.float32)
        point_attr=p.GetAttribute('points');point_attr.Clear()
        exported_points=Vt.Vec3fArray([Gf.Vec3f(*map(float,x)) for x in stored])
        point_attr.Set(exported_points);point_attr.Set(exported_points,Usd.TimeCode(job['time']))
        # Preserve the source shading input, transported by the complete map.
        normal=record.get('geometry_normals',{}).get(old_path)
        if normal:
            a=p.GetAttribute('normals');a.Clear();a.Set(Vt.Vec3fArray([Gf.Vec3f(*map(float,n)) for n in normal['values']]))
            UsdGeom.Mesh(p).SetNormalsInterpolation(normal['interpolation'])
        elif p.HasAttribute('normals'):p.RemoveProperty('normals')
        p.GetAttribute('extent').Clear() if p.HasAttribute('extent') else None
        UsdGeom.Xformable(p).AddTranslateOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Vec3d(*map(float,(r.convert(r.output,output,center)*factors(output))@r.B.T/r.unit)))
        error=float(np.max(np.linalg.norm((stored.astype(float)-local)*r.unit,axis=1)));quantization=max(quantization,error)
        source_paths[new_path]=old_path
    dst.GetRootLayer().Save()
    fresh=Usd.Stage.Open(str(path));reader=Runtime(fresh,job['output_wkt'],job['time']);actual=reader.geometry();maximum=0.
    for new_path,old_path in source_paths.items():
        maximum=max(maximum,coordinate_error(actual[new_path],record['geometry'][old_path],r.output))
    if maximum>.001:raise AssertionError('Fresh export reader exceeds 1mm or reapplies placement')
    return {'path':str(path),'fresh_reader_max_error_metres':maximum,'quantization_metres':quantization,'parts':len(source_paths),'vertices':sum(len(x) for x in actual.values()),'timeSamples':[job['time']],'timeCodesPerSecond':fresh.GetTimeCodesPerSecond(),'dependency':'No CRS-resolution claim needed for fully baked ordinary geometry; Cartesian WKT context retained','source_paths':source_paths,'shading':'Authored shading normals transported with the complete map; geometric fallback only where source normals are absent','normal_arrays':len(record.get('geometry_normals',{}))}

def sampled_geometry_export(jobs,records,path):
    """Explicitly scheduled geometry samples, with no between-sample claim."""
    if len(jobs)!=len(records):raise ValueError('Sampling association mismatch')
    receipt=geometry_export(jobs[0],records[0],path)
    dst=Usd.Stage.Open(str(path));times=[];maximum=receipt['fresh_reader_max_error_metres']
    for job,record in zip(jobs,records):
        source=Usd.Stage.Open(job['stage']);r=Runtime(source,job['output_wkt'],job['time']);output=r.scene_crs;times.append(job['time'])
        if set(record['geometry'])!=set(receipt['source_paths'].values()):raise ValueError('Changing topology/identity not supported by this sampled exporter')
        for new_path,old_path in receipt['source_paths'].items():
            coordinates=np.array(record['geometry'][old_path]);center=coordinates[0]
            local=r.stage_coordinates(coordinates,center).astype(np.float32)
            p=dst.GetPrimAtPath(new_path)
            p.GetAttribute('points').Set(Vt.Vec3fArray([Gf.Vec3f(*map(float,x)) for x in local]),job['time'])
            normal=record.get('geometry_normals',{}).get(old_path)
            if normal:p.GetAttribute('normals').Set(Vt.Vec3fArray([Gf.Vec3f(*map(float,n)) for n in normal['values']]),job['time'])
            p.GetAttribute('xformOp:translate').Set(Gf.Vec3d(*map(float,(r.convert(r.output,output,center)*factors(output))@r.B.T/r.unit)),job['time'])
        dst.GetRootLayer().Save()
        fresh=Usd.Stage.Open(str(path));actual=Runtime(fresh,job['output_wkt'],job['time']).geometry()
        for new_path,old_path in receipt['source_paths'].items():
            error=coordinate_error(actual[new_path],record['geometry'][old_path],r.output)
            maximum=max(maximum,error)
            if error>.001:raise AssertionError('Scheduled export sample exceeds 1mm')
    for new_path in receipt['source_paths']:
        assert dst.GetPrimAtPath(new_path).GetAttribute('points').GetTimeSamples()==sorted(times)
        assert dst.GetPrimAtPath(new_path).GetAttribute('xformOp:translate').GetTimeSamples()==sorted(times)
    receipt.update(timeSamples=sorted(times),fresh_reader_max_error_metres=maximum,
        trajectory_between_samples='No original-trajectory guarantee claimed; Core interpolates exported output samples')
    return receipt

def cf_export(job,path):
    from netCDF4 import Dataset
    from .datasets import resolved
    source=Usd.Stage.Open(job['stage']);r=Runtime(source,job['output_wkt'],job['time']);record,points=resolved(source.GetPrimAtPath(job['dataset']),r)
    if record['profile']!='CF':raise ValueError('This explicit measurement export writes the selected CF domain')
    if points.shape[1] not in [2,3] or (points.shape[1]==3 and not r.output.is_geographic):raise ValueError('This CF export supports 2D or ellipsoidal geographic 3D; no coordinate is discarded')
    shape=record['shape'];ncpath=Path(path).with_suffix('.nc')
    original_asset=source.GetPrimAtPath(job['dataset']).GetAttribute('data:asset').Get().resolvedPath
    ncpath.write_bytes(Path(original_asset).read_bytes())
    with Dataset(ncpath,'a') as nc:
        field=nc[record['field']];dims=field.dimensions
        names=['resolved_longitude','resolved_latitude'] if r.output.is_geographic else ['resolved_x','resolved_y']
        standards=['longitude','latitude'] if r.output.is_geographic else ['projection_x_coordinate','projection_y_coordinate']
        if points.shape[1]==3:names+=['resolved_height'];standards+=['height_above_reference_ellipsoid']
        field.grid_mapping='resolved_crs';field.coordinates=' '.join(names+list(record['times']))
        gm=nc.createVariable('resolved_crs','i4');gm.setncatts(r.output.to_cf())
        for i,name in enumerate(names):
            unit_factor=np.pi/180 if r.output.is_geographic and i<2 else 1.
            a=nc.createVariable(name,'f8',dims);a[:]=(points[:,i]*factors(r.output)[i]/unit_factor).reshape(shape);a.standard_name=standards[i];a.units=['degrees_east','degrees_north','m'][i] if r.output.is_geographic else 'm'
        nc.comment=str(getattr(nc,'comment',''))+' Explicit export of the selected coordinate domain, retaining original values, masks and observation times.'
    # Build the USD association to this new native dataset. Original field/time metadata remain intact.
    dst=Usd.Stage.CreateNew(str(path));p=dst.DefinePrim('/Data','GeospatialDataSource');dst.SetDefaultPrim(p);mark(p,'GeospatialCRSBindingAPI');attr(p,'crs:wkt',Sdf.ValueTypeNames.Token,job['output_wkt'],True);claim(dst);dst.SetTimeCodesPerSecond(source.GetTimeCodesPerSecond())
    for name,typ,value in [('asset',Sdf.ValueTypeNames.Asset,Sdf.AssetPath('./'+ncpath.name)),('format',Sdf.ValueTypeNames.Token,'CF'),('field',Sdf.ValueTypeNames.String,record['field']),('coordinateDomain',Sdf.ValueTypeNames.String,'resolved_crs')]:attr(p,'data:'+name,typ,value,True)
    dst.GetRootLayer().Save();fresh=Usd.Stage.Open(str(path));new,coords=resolved(fresh.GetDefaultPrim(),Runtime(fresh,job['output_wkt'],job['time']))
    if not np.array_equal(new['values'],record['values'],equal_nan=True) or not np.array_equal(new['mask'],record['mask']) or new['times']!=record['times']:raise AssertionError('Measurement export changed values, masks or times')
    if not np.allclose(coords,points,rtol=0,atol=1e-13):raise AssertionError('Measurement export repeated coordinate transformation')
    return {'path':str(path),'samples':len(points),'values_and_masks_preserved':True,'observation_times_preserved':True,'coordinates_preserved':True,'fresh_reader_verified':True,'dependency':'Profiles hard claim retained for absolute measurement coordinates'}
