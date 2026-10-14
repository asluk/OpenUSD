from pathlib import Path
import json,sys
import numpy as np
from pxr import Gf,Sdf,Usd,UsdGeom
from pyproj import CRS

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from wkt import normalize
from scene import BINDING

def wkt(code):return normalize(CRS.from_epsg(code).to_wkt())

def stage(path=None,up='Z',unit=1):
    s=Usd.Stage.CreateNew(str(path)) if path else Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(s,up);UsdGeom.SetStageMetersPerUnit(s,unit)
    root=UsdGeom.Xform.Define(s,'/World').GetPrim();s.SetDefaultPrim(root)
    return s

def bind(s,path,crs=None,pos=(0,0,0),orientation=None):
    p=UsdGeom.Xform.Define(s,path).GetPrim()
    p.AddAppliedSchema(BINDING)
    p.CreateAttribute('crs:wkt',Sdf.ValueTypeNames.Token,custom=False,variability=Sdf.VariabilityUniform).Set(crs or wkt(4979))
    if pos is not None:p.CreateAttribute('crs:position',Sdf.ValueTypeNames.Double3,custom=False).Set(Gf.Vec3d(*pos))
    if orientation is not None:p.GetAttribute('crs:orientation').Set(Gf.Vec3d(*orientation))
    return p

def points(p,values):
    s=p.GetStage();m=UsdGeom.Mesh.Define(s,str(p.GetPath())+'/Mesh')
    m.GetPointsAttr().Set([Gf.Vec3f(*v) for v in values])
    return m.GetPrim()

def measurement(s,path,asset,fmt,field,domain,crs):
    p=s.DefinePrim(path,'GeospatialDataSource');p.AddAppliedSchema(BINDING)
    for name,t,val in [('crs:wkt',Sdf.ValueTypeNames.Token,crs),('data:asset',Sdf.ValueTypeNames.Asset,Sdf.AssetPath(str(asset))),('data:format',Sdf.ValueTypeNames.Token,fmt),('data:field',Sdf.ValueTypeNames.String,field),('data:coordinateDomain',Sdf.ValueTypeNames.String,domain)]:
        p.CreateAttribute(name,t,custom=False,variability=Sdf.VariabilityUniform).Set(val)
    return p

def cf_dataset(path):
    import netCDF4
    with netCDF4.Dataset(path,'w') as ds:
        ds.Conventions='CF-1.12'
        for name,size in [('time',2),('north',7),('east',11)]:ds.createDimension(name,size)
        mapping=ds.createVariable('earth','i4');mapping.crs_wkt=CRS.from_epsg(4979).to_wkt()
        lon=ds.createVariable('longitude','f8',('east','north'));lon.standard_name='longitude';lon.units='degrees_east'
        lat=ds.createVariable('latitude','f8',('north','east'));lat.standard_name='latitude';lat.units='degrees_north'
        height=ds.createVariable('elevation','f8',());height.standard_name='height_above_reference_ellipsoid';height.units='m';height.assignValue(80.)
        t=ds.createVariable('time','f8',('time',));t.standard_name='time';t.units='hours since 2026-10-14 00:00:00';t.calendar='standard';t[:]=[0,6]
        y,x=np.indices((7,11));lon[:]=(-150+x*30+y*.1).T;lat[:]=-60+y*20+x*.05
        field=ds.createVariable('temperature','f8',('time','north','east'),fill_value=-9999)
        field.units='K';field.grid_mapping='earth';field.coordinates='longitude latitude elevation time'
        values=270+np.arange(2)[:,None,None]*4+y[None]*2+x[None]*.1
        field[:]=values;field[1,3,4]=-9999

def publish_fixture(name,required=False,complete=True,variant=False):
    from profiles import declare
    payload_path=ROOT/'fixtures'/f'{name}-payload.usda'
    payload=stage(payload_path)
    if required:bind(payload,'/World/Model')
    if variant:
        vs=payload.GetDefaultPrim().GetVariantSets().AddVariantSet('content')
        for choice in ['ordinary','located']:
            vs.AddVariant(choice);vs.SetVariantSelection(choice)
            with vs.GetVariantEditContext():
                if choice=='located':bind(payload,'/World/Alternative')
        vs.SetVariantSelection('ordinary')
    payload.GetRootLayer().Save()
    path=ROOT/'fixtures'/f'{name}.usda';s=stage(path)
    s.GetDefaultPrim().GetPayloads().AddPayload(str(payload_path),'/World')
    declare(s.GetDefaultPrim(),required,complete)
    s.GetRootLayer().Save()
    return path

def make_all():
    d=ROOT/'fixtures';d.mkdir(exist_ok=True)
    cf_dataset(d/'global-native.nc')
    s=stage(d/'analytic.usda');p=bind(s,'/World/Anchor');points(p,[(0,0,0),(1,0,0),(0,1,0),(0,0,1)])
    s.GetRootLayer().Save()
    s=stage(d/'france.usda');p=bind(s,'/World/Model',wkt(4979),(2.2945,48.8584,80),(30,0,0));points(p,[(0,0,0),(10,0,0),(0,10,0),(0,0,300)])
    s.GetRootLayer().Save()
    for name,required,complete,variant in [('required',True,True,False),('none',False,True,False),('unknown',False,False,False),('stale',False,True,True)]:
        publish_fixture(name,required,complete,variant)
    s=stage(d/'measurements.usda');measurement(s,'/World/Climate',d/'global-native.nc','CF','temperature','earth',wkt(4979));s.GetRootLayer().Save()

if __name__=='__main__':make_all();print('Fresh fixtures authored from the pinned contract.')
