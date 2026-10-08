"""Counterexamples for clarified contracts; expected values come from simple domains."""
import numpy as np
import pytest
from pxr import Usd,UsdGeom,Sdf,Gf,Vt,Plug
from pyproj import CRS
from review.wkt_profile import normalize
from candidate.fixtures import attr,mark,claim
from candidate.runtime import Runtime,ContractError
from candidate.execution import execute_python,compare
from candidate.export import geometry_export
from candidate.datasets import read_source
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ECEF=normalize(CRS.from_epsg(4978).to_wkt())

def simple(tmp_path,name):
    Plug.Registry().RegisterPlugins(str(ROOT/'schema/generated/plugInfo.json'))
    s=Usd.Stage.CreateNew(str(tmp_path/(name+'.usda')))
    root=UsdGeom.Xform.Define(s,'/World').GetPrim();s.SetDefaultPrim(root);claim(s)
    UsdGeom.SetStageUpAxis(s,'Z');UsdGeom.SetStageMetersPerUnit(s,1)
    a=UsdGeom.Xform.Define(s,'/World/Model').GetPrim()
    mark(a,'GeospatialCRSBindingAPI');attr(a,'crs:wkt',Sdf.ValueTypeNames.Token,ECEF,True)
    attr(a,'crs:position',Sdf.ValueTypeNames.Double3,Gf.Vec3d(6378137,0,0))
    return s

def triangle(s,path):
    m=UsdGeom.Mesh.Define(s,path);m.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(0),Gf.Vec3f(1,0,0),Gf.Vec3f(0,1,0)]))
    m.CreateFaceVertexCountsAttr(Vt.IntArray([3]));m.CreateFaceVertexIndicesAttr(Vt.IntArray([0,1,2]))
    m.CreateSubdivisionSchemeAttr('none');return m

def job(s):
    s.GetRootLayer().Save()
    return dict(stage=s.GetRootLayer().identifier,output_wkt=ECEF,time=0,interpolation='linear',queries=[],geometry=True)

def test_unbound_prototype_uses_instancer_without_library_binding(tmp_path):
    s=simple(tmp_path,'prototype')
    triangle(s,'/Library/Proto')
    i=UsdGeom.PointInstancer.Define(s,'/World/Model/Instances')
    i.GetPrototypesRel().SetTargets([Sdf.Path('/Library/Proto')])
    i.CreateProtoIndicesAttr(Vt.IntArray([0]));i.CreatePositionsAttr(Vt.Vec3fArray([Gf.Vec3f(10,0,0)]))
    actual=list(execute_python(job(s))['geometry'].values())
    assert len(actual)==1
    # At (longitude,latitude)=(0,0), east=ECEF Y, north=ECEF Z, up=ECEF X.
    np.testing.assert_allclose(actual[0],[[6378137,10,0],[6378137,11,0],[6378137,10,1]],atol=1e-7,rtol=0)

def test_bake_inventory_origin_and_unrelated_schema(tmp_path):
    s=simple(tmp_path,'nested')
    m=triangle(s,'/World/Model/Parent');triangle(s,'/World/Model/Parent/Child')
    UsdGeom.MotionAPI.Apply(m.GetPrim()).CreateVelocityScaleAttr(2)
    j=job(s);record=execute_python(j);out=tmp_path/'baked.usda';receipt=geometry_export(j,record,out)
    fresh=Usd.Stage.Open(str(out));geometry=Runtime(fresh,ECEF).geometry()
    assert len(geometry)==2 and set(geometry)==set(receipt['source_paths'])
    origin=fresh.GetPrimAtPath(receipt['export_origin']['prim'])
    ops=UsdGeom.Xformable(origin).GetOrderedXformOps()
    assert len(ops)==1 and ops[0].GetPrecision()==UsdGeom.XformOp.PrecisionDouble
    np.testing.assert_allclose(ops[0].Get(),[6378137,0,0],atol=1e-7,rtol=0)
    parent=next(p for p,source in receipt['source_paths'].items() if source.endswith('/Parent'))
    p=fresh.GetPrimAtPath(parent)
    assert 'MotionAPI' in p.GetAppliedSchemas()
    assert UsdGeom.MotionAPI(p).GetVelocityScaleAttr().Get()==2
    np.testing.assert_allclose(geometry[parent],[[6378137,0,0],[6378137,1,0],[6378137,0,1]],atol=1e-7,rtol=0)

@pytest.mark.parametrize('blocked',[False,True])
def test_invalid_descendant_placement_rejects_value_and_block(tmp_path,blocked):
    s=simple(tmp_path,'invalid')
    m=triangle(s,'/World/Model/Mesh')
    a=m.GetPrim().CreateAttribute('crs:position',Sdf.ValueTypeNames.Double3)
    a.Set(Sdf.ValueBlock() if blocked else Gf.Vec3d(7,8,9))
    with pytest.raises(ContractError,match='inherited-only descendant'):
        Runtime(s,ECEF).placement(m.GetPrim(),[[0,0,0]])

def test_cf_coordinates_follow_dimension_names_not_memory_order(tmp_path):
    from netCDF4 import Dataset
    crs=CRS.from_user_input('OGC:CRS84');wkt=normalize(crs.to_wkt());path=tmp_path/'domain.nc'
    longitude=np.array([[1.,1.1],[2.,2.1],[3.,3.1]])
    latitude=np.array([[45.,46.],[45.2,46.2],[45.4,46.4]])
    with Dataset(path,'w') as n:
        n.createDimension('y',2);n.createDimension('x',3)
        gm=n.createVariable('map','i4');gm.setncatts(crs.to_cf())
        for name,std,unit,values in [('lon','longitude','degrees_east',longitude),('lat','latitude','degrees_north',latitude)]:
            a=n.createVariable(name,'f8',('x','y'));a[:]=values;a.standard_name=std;a.units=unit
        v=n.createVariable('measurement','f8',('y','x'));v[:]=np.arange(1.,7.).reshape(2,3)
        v.grid_mapping='map';v.coordinates='lon lat'
    Plug.Registry().RegisterPlugins(str(ROOT/'schema/generated/plugInfo.json'))
    s=Usd.Stage.CreateInMemory();p=s.DefinePrim('/Data','GeospatialDataSource')
    mark(p,'GeospatialCRSBindingAPI');attr(p,'crs:wkt',Sdf.ValueTypeNames.Token,wkt,True)
    for name,kind,value in [('asset',Sdf.ValueTypeNames.Asset,Sdf.AssetPath(str(path))),('format',Sdf.ValueTypeNames.Token,'CF'),
                             ('field',Sdf.ValueTypeNames.String,'measurement'),('coordinateDomain',Sdf.ValueTypeNames.String,'map')]:
        attr(p,'data:'+name,kind,value,True)
    r=read_source(p)
    np.testing.assert_allclose(r['coordinates'],np.c_[longitude.T.ravel(),latitude.T.ravel()],atol=1e-13,rtol=0)
    np.testing.assert_array_equal(r['values'],np.arange(1.,7.))

def test_comparison_preserves_component_residual_units_and_magnitude():
    a={'queries':[{'prim':'/P','coordinates':[[6378137.,0,0]]}],'geometry':{}}
    b={'queries':[{'prim':'/P','coordinates':[[6378137.,.0005,0]]}],'geometry':{}}
    report=compare(a,b,ECEF)
    np.testing.assert_allclose(report['max_abs_component_residuals_output_units'],[0,.0005,0],atol=1e-15,rtol=0)
    assert report['max_abs_output_coordinate_components'][0]==6378137
    assert report['max_distance_metres']==pytest.approx(.0005)
    assert report['component_units']==['metre']*3
