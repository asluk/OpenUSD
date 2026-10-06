"""Writer-side fixtures and independent expected controls, specified before execution."""
from pathlib import Path
import json, hashlib
import numpy as np
from pxr import Gf,Sdf,Usd,UsdGeom,UsdProfiles,Vt
from pyproj import CRS
from review.wkt_profile import normalize

def mark(p,name):
    op=p.GetMetadata('apiSchemas');items=list(op.GetAppliedItems()) if op else []
    if name not in items:items.append(name)
    p.SetMetadata('apiSchemas',Sdf.TokenListOp.CreateExplicit(items))

def claim(stage):
    p=stage.GetDefaultPrim();UsdProfiles.ClaimsAPI.Apply(p)
    d=p.GetCustomData();d.setdefault('profilesInfo',{})['capabilityUsages']={'geospatial:crsResolution':'hard'}
    p.SetCustomData(d)

def attr(p,name,typ,value,uniform=False):
    p.CreateAttribute(name,typ,custom=False,variability=Sdf.VariabilityUniform if uniform else Sdf.VariabilityVarying).Set(value)

def bind(p,wkt,library):
    key=hashlib.sha256(wkt.encode()).hexdigest()[:16]
    lib=Usd.Stage.Open(str(library));q=lib.GetPrimAtPath('/Definitions/C'+key)
    if not q:
        q=lib.DefinePrim('/Definitions/C'+key,'CoordinateReferenceSystem');attr(q,'crs:wkt',Sdf.ValueTypeNames.Token,wkt,True);lib.GetRootLayer().Save()
    mark(p,'GeospatialCRSBindingAPI');p.GetReferences().AddReference(Sdf.ComputeAssetPathRelativeToLayer(p.GetStage().GetRootLayer(),str(library)),str(q.GetPath()))

def build(root,directory):
    directory=Path(directory);directory.mkdir(exist_ok=True,parents=True)
    library=directory/'crs-library.usda';library_stage=Usd.Stage.CreateNew(str(library));library_stage.GetRootLayer().Save()
    targets={k:normalize(v) for k,v in json.loads((root/'targets.json').read_text()).items()}
    for key,code in [('geo2','OGC:CRS84'),('utm32_2',32632),('geo3',4979),('ecef3',4978)]:targets[key]=normalize(CRS.from_user_input(code).to_wkt())
    jobs=[]
    def make(name,axis='Z',unit=1):
        s=Usd.Stage.CreateNew(str(directory/(name+'.usda')));p=UsdGeom.Xform.Define(s,'/World').GetPrim();s.SetDefaultPrim(p)
        UsdGeom.SetStageUpAxis(s,axis);UsdGeom.SetStageMetersPerUnit(s,unit);s.SetTimeCodesPerSecond(48);claim(s)
        return s,p
    def anchor(s,path,wkt,pos):
        p=UsdGeom.Xform.Define(s,path).GetPrim();bind(p,wkt,library);attr(p,'crs:position',Sdf.ValueTypeNames.Double3,Gf.Vec3d(*pos));return p
    def save(name,s,target,queries,expected=None,time=0,interpolation='linear'):
        s.GetRootLayer().Save();jobs.append({'name':name,'stage':str(directory/(name+'.usda')),'output_wkt':targets[target] if target else '',
            'queries':queries,'expected':expected,'time':time,'interpolation':interpolation})

    for axis,unit in [('Z',1),('Y',1),('Y',.01)]:
        name=f'basis-{axis}-{unit}';s,p=make(name,axis,unit);a=anchor(s,'/World/Model',targets['ecef3'],[6378137,0,0]);
        attr(a,'crs:scale',Sdf.ValueTypeNames.Double3,Gf.Vec3d(2,3,4))
        attr(a,'crs:orientation',Sdf.ValueTypeNames.Quatd,Gf.Rotation(Gf.Vec3d(0,0,1),90).GetQuat())
        v=[[1,0,0],[0,1,0],[0,0,1]]
        # Independent expected formula: axis convention, scale, quarter-turn.
        ordered=np.array(v) if axis=='Z' else np.array([[1,0,0],[0,0,1],[0,-1,0]])
        scaled=ordered*unit*[2,3,4];expected=np.c_[-scaled[:,1],scaled[:,0],scaled[:,2]]+[6378137,0,0]
        save(name,s,'ecef3',[{'prim':str(a.GetPath()),'points':v}],expected.tolist())
        jobs[-1]['frames']=[str(a.GetPath())]

    s,p=make('working-adjustment');anchor(s,'/World',targets['utm31'],[448251,5411932,0]);UsdGeom.Xformable(p).AddTranslateOp().Set((100000,0,0))
    a=anchor(s,'/World/Asset',targets['geo3'],[2.2945,48.8584,35]);UsdGeom.Xformable(a).AddTranslateOp().Set((10,0,0))
    attr(a,'crs:orientation',Sdf.ValueTypeNames.Quatd,Gf.Rotation(Gf.Vec3d(0,0,1),90).GetQuat())
    c=UsdGeom.Xform.Define(s,'/World/Asset/Child');c.AddTranslateOp().Set((3,0,0))
    reset=UsdGeom.Xform.Define(s,'/World/Asset/Reset');reset.SetResetXformStack(True);reset.AddTranslateOp().Set((3,0,0))
    save('working-adjustment',s,'utm31',[{'prim':str(a.GetPath()),'points':[[0,0,0],[1,0,0]]},{'prim':str(c.GetPath()),'points':[[0,0,0]]},{'prim':str(reset.GetPath()),'points':[[0,0,0]]}])
    jobs.append({**jobs[-1],'name':'working-adjustment-ecef','output_wkt':targets['ecef3']})
    jobs[-1]['frames']=['/World/Asset']
    s,p=make('geographic-working');anchor(s,'/World',targets['geo3'],[2.29,48.85,20]);a=anchor(s,'/World/Asset',targets['geo3'],[2.2945,48.8584,35]);UsdGeom.Xformable(a).AddTranslateOp().Set((12,4,3));save('geographic-working',s,'ecef3',[{'prim':str(a.GetPath()),'points':[[0,0,0],[1,0,0]]}])
    s,p=make('pivot-order');a=anchor(s,'/World/Model',targets['ecef3'],[100,200,300]);x=UsdGeom.Xformable(a)
    x.AddTranslateOp(opSuffix='pivot').Set((100,200,300));x.AddRotateZOp().Set(90);x.AddTranslateOp(opSuffix='pivot',isInverseOp=True)
    save('pivot-order',s,'ecef3',[{'prim':str(a.GetPath()),'points':[[1,0,0],[0,2,0]]}],[[100,201,300],[98,200,300]])
    s,p=make('time-source');a=anchor(s,'/World/Model',targets['geo3'],[0,0,0]);a.GetAttribute('crs:position').Clear();a.GetAttribute('crs:position').Set((0,0,0),0);a.GetAttribute('crs:position').Set((2,0,0),10)
    point=UsdGeom.Points.Define(s,'/World/Model/Sample');point.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(0),Gf.Vec3f(1,0,0)]));point.CreateWidthsAttr(Vt.FloatArray([.01]))
    save('time-source',s,'ecef3',[{'prim':str(a.GetPath()),'points':[[0,0,0]]}],[[6378137*np.cos(np.pi/180),6378137*np.sin(np.pi/180),0]],5)
    jobs[-1]['geometry']=True
    jobs.append({**jobs[-1],'name':'time-source-held','interpolation':'held','expected':[[6378137,0,0]]})
    jobs.append({**jobs[-2],'name':'time-source-t0','time':0,'expected':[[6378137,0,0]]})
    jobs.append({**jobs[-3],'name':'time-source-t10','time':10,'expected':[[6378137*np.cos(2*np.pi/180),6378137*np.sin(2*np.pi/180),0]]})

    s,p=make('relative-position');a=anchor(s,'/World/A',targets['ecef3'],[6378137,0,0]);b=anchor(s,'/World/B',targets['ecef3'],[6378137,10,0])
    attr(b,'crs:orientation',Sdf.ValueTypeNames.Quatd,Gf.Rotation(Gf.Vec3d(0,0,1),90).GetQuat());attr(b,'crs:scale',Sdf.ValueTypeNames.Double3,Gf.Vec3d(2,3,1))
    save('relative-position',s,'ecef3',[{'prim':str(a.GetPath()),'points':[[0,0,0]]}]);jobs[-1]['relative']={'from':'/World/A','to':'/World/B','expected_local':[-5,0,0]}

    # Original geometry is retained; old experimental role markers are writer-side intake only and are removed.
    migrations=[]
    for name in ['tower','terrain','composition','instances']:
        src=Usd.Stage.Open(str(root/'scenes'/(name+'.usda')));dst=Usd.Stage.Open(src.Flatten())
        for prim in dst.Traverse():
            schemas=prim.GetMetadata('apiSchemas')
            if schemas:prim.SetMetadata('apiSchemas',Sdf.TokenListOp.CreateExplicit([n for n in schemas.GetAppliedItems() if n!='GeospatialBindingAPI']))
            if prim.GetAttribute('crs:wkt').HasAuthoredValue():prim.GetAttribute('crs:wkt').Set(normalize(prim.GetAttribute('crs:wkt').Get()))
            rel=prim.GetRelationship('crs:binding')
            if rel and rel.HasAuthoredTargets():
                cp=dst.GetPrimAtPath(rel.GetTargets()[0]);wkt=normalize(cp.GetAttribute('crs:wkt').Get());prim.RemoveProperty('crs:binding');bind(prim,wkt,library)
            if prim.HasRelationship('crs:coordinateProperties'):prim.RemoveProperty('crs:coordinateProperties')
        dst.GetRootLayer().customLayerData={}
        if not dst.GetDefaultPrim(): dst.SetDefaultPrim(next(iter(dst.GetPseudoRoot().GetChildren())))
        claim(dst);dst.GetRootLayer().Export(str(directory/(name+'.usda')))
        dest='France_02' if name=='tower' else 'Colorado_03' if name=='terrain' else 'utm31'
        jobs.append({'name':name,'stage':str(directory/(name+'.usda')),'output_wkt':targets[dest],'queries':[],'expected':None,'time':0,'interpolation':'linear','geometry':True})
        migrations.append({'scene':name,'original_scene_sha256':hashlib.sha256((root/'scenes'/(name+'.usda')).read_bytes()).hexdigest(),'binding_migration':'reference + applied schema; private relationships removed','source_geometry':'unchanged'})
        if name=='instances':
            mask_stage=Usd.Stage.Open(str(directory/(name+'.usda')))
            inst=next(UsdGeom.PointInstancer(p) for p in mask_stage.Traverse() if p.IsA(UsdGeom.PointInstancer))
            inst.CreateIdsAttr(Vt.Int64Array([101,102,103]));inst.CreateInvisibleIdsAttr(Vt.Int64Array([102]));mask_stage.GetRootLayer().Export(str(directory/'instances-masked.usda'))
            jobs.append({**jobs[-1],'name':'instances-masked','stage':str(directory/'instances-masked.usda')})
            negative=Usd.Stage.Open(str(directory/(name+'.usda')))
            inst=next(UsdGeom.PointInstancer(p) for p in negative.Traverse() if p.IsA(UsdGeom.PointInstancer))
            proto=negative.GetPrimAtPath(inst.GetPrototypesRel().GetTargets()[0]);bind(proto,targets['utm31'],library);attr(proto,'crs:position',Sdf.ValueTypeNames.Double3,Gf.Vec3d(0))
            negative.GetRootLayer().Export(str(directory/'instances-independent-prototype.usda'))
            jobs.append({**jobs[-1],'name':'instances-independent-prototype','stage':str(directory/'instances-independent-prototype.usda'),'expect_failure':True,'expect_error_tokens':['Independently CRS-bound point-instancer prototype']})
    # Partner point controls in both directions, all three source coordinates retained.
    controls=json.loads((root/'data/partner-controls.json').read_text())
    # Use original committed fixture positions, not rounded CSV as numerical truth.
    for group in ['France_01','France_02','Colorado_01','Colorado_02','Colorado_03']:
        src=Usd.Stage.Open(str(root/'scenes'/(group+'.usda')));dst,parent=make(group)
        # These are individual point-query test anchors, not a proposed per-sample measurement carrier.
        source_coordinates=src.GetPrimAtPath('/Controls').GetAttribute('data:coordinates').Get()
        qs=[]
        for i,position in enumerate(source_coordinates):
            p=anchor(dst,f'/World/Control{i}',targets[group],position)
            qs.append({'prim':str(p.GetPath()),'points':[[0,0,0]]})
        dst.GetRootLayer().Save()
        target='France_02' if group=='France_01' else 'France_01' if group=='France_02' else 'Colorado_03' if group!='Colorado_03' else 'Colorado_02'
        jobs.append({'name':group,'stage':str(directory/(group+'.usda')),'output_wkt':targets[target],'queries':qs,'time':0,'interpolation':'linear','expected':None})

    def dataset(name,profile,asset,field,domain,crskey,target):
        s,p=make(name);d=s.DefinePrim('/World/Data','GeospatialDataSource');bind(d,targets[crskey],library)
        for n,t,v in [('asset',Sdf.ValueTypeNames.Asset,Sdf.AssetPath(str(asset))),('format',Sdf.ValueTypeNames.Token,profile),('field',Sdf.ValueTypeNames.String,field),('coordinateDomain',Sdf.ValueTypeNames.String,domain)]:attr(d,'data:'+n,t,v,True)
        save(name,s,target,[]);jobs[-1]['dataset']='/World/Data';return s,d
    from netCDF4 import Dataset
    cf=directory/'global-cf.nc'
    with Dataset(root/'data/gfs_t2m.nc') as original:
        original_description={n:{'shape':list(v.shape),'attributes':{k:str(v.getncattr(k)) for k in v.ncattrs()}} for n,v in original.variables.items()}
        arrays={n:np.array(v[:]) for n,v in original.variables.items()}
    (directory/'original-netcdf-intake.json').write_text(json.dumps(original_description,indent=2))
    candidates=[(n,v) for n,v in arrays.items() if v.ndim==2];field,values=max(candidates,key=lambda x:x[1].size)
    lat=next((v for n,v in arrays.items() if 'lat' in n.lower()),None);lon=next((v for n,v in arrays.items() if 'lon' in n.lower()),None)
    if lat is None or lon is None: raise ValueError('Original grid coordinates not located; do not invent')
    with Dataset(cf,'w') as nc:
        nc.createDimension('latitude',len(lat));nc.createDimension('longitude',len(lon));nc.Conventions='CF-1.12'
        for n,v,units in [('latitude',lat,'degrees_north'),('longitude',lon,'degrees_east')]:
            a=nc.createVariable(n,'f8',(n,));a[:]=v;a.standard_name=n;a.units=units
        gm=nc.createVariable('crs','i4');gm.setncatts(CRS.from_wkt(targets['geo2']).to_cf())
        a=nc.createVariable('original_scalar','f8',('latitude','longitude'));a[:]=values;a.grid_mapping='crs';a.coordinates='longitude latitude'
        nc.comment='Illustrative CF association of original coordinate/value arrays; original physical value units were not supplied. No height or observation time is invented.'
    dataset('climate','CF',cf,'original_scalar','crs','geo2','geo2')
    jobs.append({**jobs[-1],'name':'climate-no-height','output_wkt':targets['ecef3'],'expect_failure':'dimensional'})
    from rasterio import open as rio_open
    from rasterio.transform import from_origin
    tif=directory/'city.tif';yy,xx=np.indices((64,64));image=.2+.3*np.sin(xx/7)*np.cos(yy/9)
    with rio_open(tif,'w',driver='GTiff',width=64,height=64,count=1,dtype='float64',crs='EPSG:32632',transform=from_origin(500000,5500000,10,10)) as ds:ds.write(image,1)
    dataset('city','GeoTIFF',tif,'1','0','utm32_2','geo2')
    point_tif=directory/'city-point.tif'
    with rio_open(point_tif,'w',driver='GTiff',width=64,height=64,count=1,dtype='float64',crs='EPSG:32632',transform=from_origin(500000,5500000,10,10)) as ds:
        ds.write(image,1);ds.update_tags(AREA_OR_POINT='Point')
    dataset('city-point','GeoTIFF',point_tif,'1','0','utm32_2','geo2')
    multi=directory/'multi-domain.nc';lat2=np.array([48.,49.]);lon2=np.array([8.,9.,10.]);lo,la=np.meshgrid(lon2,lat2)
    from pyproj import Transformer
    xx2,yy2=Transformer.from_crs('OGC:CRS84',32632,always_xy=True).transform(lo,la)
    with Dataset(multi,'w') as nc:
        nc.Conventions='CF-1.12';nc.createDimension('time',2);nc.createDimension('row',2);nc.createDimension('column',3)
        t=nc.createVariable('time','f8',('time',));t[:]=[0,3600];t.standard_name='time';t.units='seconds since 2026-10-05 00:00:00';t.calendar='standard'
        for n,v,role,units in [('longitude',lo,'longitude','degrees_east'),('latitude',la,'latitude','degrees_north'),('easting',xx2,'projection_x_coordinate','m'),('northing',yy2,'projection_y_coordinate','m')]:
            a=nc.createVariable(n,'f8',('row','column'));a[:]=v;a.standard_name=role;a.units=units
        for name,key in [('geographic','geo2'),('projected','utm32_2')]:gm=nc.createVariable(name,'i4');gm.setncatts(CRS.from_wkt(targets[key]).to_cf())
        values=nc.createVariable('measurement','f8',('time','row','column'),fill_value=-9999);values[:]=np.arange(12).reshape(2,2,3);values[1,1,2]=-9999;values.units='1';values.coordinates='longitude latitude time';values.grid_mapping='geographic: longitude latitude projected: easting northing'
    dataset('multi-geographic','CF',multi,'measurement','geographic','geo2','geo2')
    dataset('multi-projected','CF',multi,'measurement','projected','utm32_2','geo2')
    source=json.loads((root/'data/railway.geojson').read_text())
    # Horizontal-only illustrative copy; original heights remain untouched and explicitly uninterpreted.
    source.pop('crs',None)
    def horizontal(a):
        if a and isinstance(a[0],(int,float)):return a[:2]
        return [horizontal(x) for x in a]
    for f in source['features']:f['geometry']['coordinates']=horizontal(f['geometry']['coordinates'])
    rail=directory/'rail-horizontal.geojson';rail.write_text(json.dumps(source),encoding='utf-8')
    dataset('railway','GeoJSON',rail,'','geometry','geo2','utm32_2')
    (directory/'writer-intake.json').write_text(json.dumps({'migrations':migrations,'global_cf':'Illustrative explicit horizontal association; original coordinates and scalar values retained; no invented height or physical units','railway':'Explicit horizontal-only copy; original third-component meaning remains unavailable','city':'Synthetic GeoTIFF band, 10m pixels, known projected CRS'},indent=2))
    return jobs,targets
