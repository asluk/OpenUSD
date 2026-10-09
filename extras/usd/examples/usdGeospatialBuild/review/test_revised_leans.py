"""Adversarial controls: source rules, analytical expectations and Core semantics.

These test the new scope boundaries; they do not establish whole-standard conformance.
"""
from pathlib import Path
import os,math
import numpy as np
import pytest
from pxr import Gf,Sdf,Usd,UsdGeom,Vt,Plug
from pyproj import CRS
from candidate.fixtures import mark,attr,claim
from candidate.runtime import Runtime,ContractError,dependency
from candidate.execution import execute_python,native_job,coordinate_error
from candidate.export import geometry_export
from review.wkt_profile import normalize
ROOT=Path(__file__).resolve().parents[1]
W=Path('C:/Users/aluk/Documents/Codex/2026-09-21/have')
ECEF=normalize(CRS.from_epsg(4978).to_wkt());GEO=normalize(CRS.from_epsg(4979).to_wkt())
ORIGIN=np.array([6378137.,0.,0.])

def scene(tmp_path):
    Plug.Registry().RegisterPlugins(str(ROOT/'schema/generated/plugInfo.json'))
    s=Usd.Stage.CreateNew(str(tmp_path/'scene.usda'))
    UsdGeom.SetStageUpAxis(s,'Z');UsdGeom.SetStageMetersPerUnit(s,1)
    w=UsdGeom.Xform.Define(s,'/World').GetPrim();s.SetDefaultPrim(w);claim(s)
    a=anchor(s,'/World/Model');return s,a

def anchor(s,path,wkt=ECEF,pos=ORIGIN):
    a=UsdGeom.Xform.Define(s,path).GetPrim();mark(a,'GeospatialCRSBindingAPI')
    attr(a,'crs:wkt',Sdf.ValueTypeNames.Token,wkt,True)
    attr(a,'crs:position',Sdf.ValueTypeNames.Double3,Gf.Vec3d(*pos));return a

def triangle(s,path):
    m=UsdGeom.Mesh.Define(s,path)
    m.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(0),Gf.Vec3f(1,0,0),Gf.Vec3f(0,1,0)]))
    m.CreateFaceVertexCountsAttr(Vt.IntArray([3]));m.CreateFaceVertexIndicesAttr(Vt.IntArray([0,1,2]));m.CreateSubdivisionSchemeAttr('none')
    return m

def records(s,tmp_path,queries=(),geometry=False,time=0,interpolation='linear'):
    s.GetRootLayer().Save()
    job=dict(name='adversarial',stage=s.GetRootLayer().identifier,output_wkt=ECEF,time=time,
             interpolation=interpolation,queries=list(queries),geometry=geometry)
    env=os.environ.copy()
    env['PATH']=';'.join([str(W/'work/geospatial-proj-tiff/bin'),'C:/git/usd-geospatial-fresh/inst/bin',
       'C:/git/usd-geospatial-fresh/inst/lib','C:/Users/aluk/AppData/Local/Programs/Python/Python310',env['PATH']])
    resources=str(W/'work/geospatial-model-resources')+';'+str(W/'work/geospatial-proj-tiff/share/proj')
    py=execute_python(job)
    cpp=native_job(job,tmp_path,W/'work/geospatial-leans-native-20261005/leansNative.exe',resources,env)
    return py,cpp

@pytest.mark.parametrize('offset,rotation,scale',[(10,False,1),(0,True,1),(0,False,2)])
def test_instancer_local_meaning_independent_of_binding(tmp_path,offset,rotation,scale):
    s,a=scene(tmp_path);triangle(s,'/Library/Unbound');anchor(s,'/Library/Bound');triangle(s,'/Library/Bound/Mesh')
    i=UsdGeom.PointInstancer.Define(s,'/World/Model/Instances')
    i.CreatePrototypesRel().SetTargets(['/Library/Unbound','/Library/Bound'])
    i.CreateProtoIndicesAttr(Vt.IntArray([0,1]));i.CreatePositionsAttr(Vt.Vec3fArray([Gf.Vec3f(offset,0,0)]*2))
    if rotation:i.CreateOrientationsAttr(Vt.QuathArray([Gf.Quath(math.sqrt(.5),Gf.Vec3h(0,0,math.sqrt(.5)))]*2))
    if scale!=1:i.CreateScalesAttr(Vt.Vec3fArray([Gf.Vec3f(scale)]*2))
    for r in records(s,tmp_path,geometry=True):
        parts=[np.array(v) for k,v in r['geometry'].items() if '_ResolvedInstance' in k]
        assert len(parts)==2
        np.testing.assert_allclose(parts[0],parts[1],atol=3e-4,rtol=0)
        np.testing.assert_allclose(parts[0][0],ORIGIN+[0,offset,0],atol=1e-6,rtol=0)
        if scale==2:np.testing.assert_allclose(parts[0][1],ORIGIN+[0,2,0],atol=1e-6,rtol=0)
        if rotation:np.testing.assert_allclose(parts[0][1],ORIGIN+[0,0,1],atol=3e-4,rtol=0)

@pytest.mark.parametrize('singular,offset',[(True,10),(True,0),(False,10)])
def test_instance_inverse_is_required_only_for_nonidentity(tmp_path,singular,offset):
    s,a=scene(tmp_path);anchor(s,'/Library/Bound');triangle(s,'/Library/Bound/Mesh')
    if singular:UsdGeom.Xformable(a).AddScaleOp().Set((0,1,1))
    i=UsdGeom.PointInstancer.Define(s,'/World/Model/Instances');i.CreatePrototypesRel().SetTargets(['/Library/Bound'])
    i.CreateProtoIndicesAttr(Vt.IntArray([0]));i.CreatePositionsAttr(Vt.Vec3fArray([Gf.Vec3f(offset,0,0)]))
    if singular and offset:
        with pytest.raises(ContractError,match='Singular'):Runtime(s,ECEF).geometry()
    else:assert Runtime(s,ECEF).geometry()

@pytest.mark.parametrize('reset',[False,True])
def test_bake_reassembly_matches_ordinary_usd(tmp_path,reset):
    s,a=scene(tmp_path);triangle(s,'/World/Model/Triangle');s.GetRootLayer().Save()
    r=Runtime(s,ECEF);g=r.geometry()
    job=dict(stage=s.GetRootLayer().identifier,output_wkt=ECEF,time=0)
    record=dict(geometry=g,geometry_sources=r.geometry_sources,geometry_normals=r.geometry_normals)
    baked=tmp_path/'baked.usda';geometry_export(job,record,baked)
    b=Usd.Stage.CreateNew(str(tmp_path/'assembly.usda'));UsdGeom.SetStageUpAxis(b,'Z');UsdGeom.SetStageMetersPerUnit(b,1)
    root=UsdGeom.Xform.Define(b,'/Assembly').GetPrim();b.SetDefaultPrim(root);claim(b)
    # A different enclosing geographic CRS must not reinterpret the retained Cartesian bake.
    mark(root,'GeospatialCRSBindingAPI');attr(root,'crs:wkt',Sdf.ValueTypeNames.Token,GEO,True)
    attr(root,'crs:position',Sdf.ValueTypeNames.Double3,Gf.Vec3d(0))
    parent=UsdGeom.Xform.Define(b,'/Assembly/Placed');parent.AddTranslateOp().Set((100,0,0))
    asset=b.DefinePrim('/Assembly/Placed/Asset');asset.GetReferences().AddReference(str(baked))
    mesh=next(p for p in b.Traverse() if p.IsA(UsdGeom.Mesh));v=UsdGeom.Mesh(mesh).GetPointsAttr().Get()[0]
    if reset:UsdGeom.Xformable(mesh.GetParent()).SetResetXformStack(True)
    expected=np.array(UsdGeom.XformCache(0).GetLocalToWorldTransform(mesh).Transform(Gf.Vec3d(v)))
    np.testing.assert_allclose(expected,ORIGIN+[0 if reset else 100,0,0],atol=1e-7,rtol=0)
    for rec in records(b,tmp_path,geometry=True):np.testing.assert_allclose(rec['geometry'][str(mesh.GetPath())][0],expected,atol=1e-7,rtol=0)

@pytest.mark.parametrize('kind,usage,coverage',[
    ('hard','hard','complete'),('none',None,'complete'),('unknown','hard','unknown'),('positive','hard','unknown')])
def test_profiles_complete_empty_and_unknown(tmp_path,kind,usage,coverage):
    s,a=scene(tmp_path)
    if kind=='none':
        s.RemovePrim(a.GetPath());claim(s,required=False)
    elif kind=='positive':
        s.GetDefaultPrim().ClearCustomDataByKey('profilesInfo:profileCompatibility')
    elif kind=='unknown':s.GetDefaultPrim().ClearCustomDataByKey('profilesInfo')
    for r in records(s,tmp_path):
        d=r['dependency'];assert d['usage']==usage and d['coverage']==coverage
        assert d['known_none']==(kind=='none') and not d['traversal_required']

def test_weak_profiles_dependency_is_rejected(tmp_path):
    s,a=scene(tmp_path);s.GetDefaultPrim().SetCustomDataByKey('profilesInfo:capabilityUsages:usd.geospatial.crsResolution','soft')
    with pytest.raises(ContractError,match='Weak'):dependency(s)

@pytest.mark.parametrize('end',[180,-180])
def test_half_turn_requires_path_not_spelling(tmp_path,end):
    s,a=scene(tmp_path);v=a.CreateAttribute('crs:orientation',Sdf.ValueTypeNames.Double3,custom=False);v.Set((0,0,0),0);v.Set((end,0,0),10)
    with pytest.raises(ContractError,match='half-turn'):Runtime(s,ECEF,5).placement(a,[[0,1,0]])
    for t in [0,10]:assert np.isfinite(Runtime(s,ECEF,t).placement(a,[[0,1,0]])).all()
    s.SetInterpolationType(Usd.InterpolationTypeHeld);assert np.isfinite(Runtime(s,ECEF,5).placement(a,[[0,1,0]])).all()
    v.Set((end/2,0,0),5);s.SetInterpolationType(Usd.InterpolationTypeLinear)
    for r in records(s,tmp_path,queries=[dict(prim=str(a.GetPath()),points=[[0,1,0]])],time=2.5):
        sign=1 if end>0 else -1
        expected=ORIGIN+[0,sign*math.sin(math.pi/4),math.cos(math.pi/4)]
        np.testing.assert_allclose(r['queries'][0]['coordinates'][0],expected,atol=1e-7,rtol=0)

def test_three_dimensional_metric_includes_altitude_radius():
    expected=2*(6378137+400000)*math.sin(math.pi/360)
    np.testing.assert_allclose(coordinate_error([[0,0,400000]],[[1,0,400000]],GEO),expected,atol=1e-7,rtol=0)
    d=CRS.from_wkt(GEO).to_json_dict()
    for axis in d['coordinate_system']['axis'][:2]:axis['unit']={'type':'AngularUnit','name':'grad','conversion_factor':math.pi/200}
    grad=CRS.from_json_dict(d)
    np.testing.assert_allclose(coordinate_error([[0,0,400000]],[[10/9,0,400000]],grad),expected,atol=1e-7,rtol=0)

@pytest.mark.parametrize('sign',[1,-1])
def test_geocentric_pole_has_no_model_meridian(tmp_path,sign):
    s,a=scene(tmp_path);a.GetAttribute('crs:position').Set((0,0,sign*6356752.314245179))
    with pytest.raises(ContractError,match='meridian'):Runtime(s,ECEF).placement(a,[[0,1,0]])

def test_active_uniform_source_is_not_animated(tmp_path):
    s,a=scene(tmp_path);a.GetAttribute('crs:wkt').Set(GEO,0)
    with pytest.raises(ContractError,match='time samples'):Runtime(s,ECEF).placement(a,[[0,1,0]])

def test_baked_wkt_obeys_same_normal_form(tmp_path):
    s=Usd.Stage.CreateNew(str(tmp_path/'bake.usda'));root=s.DefinePrim('/Baked','CoordinateReferenceSystem');s.SetDefaultPrim(root)
    UsdGeom.SetStageUpAxis(s,'Z');UsdGeom.SetStageMetersPerUnit(s,1)
    attr(root,'crs:wkt',Sdf.ValueTypeNames.Token,ECEF.replace('[','[ ',1),True)
    mesh=triangle(s,'/Baked/Mesh')
    with pytest.raises(ContractError,match='normalized'):Runtime(s,ECEF).placement(mesh.GetPrim(),[[0,0,0]])

@pytest.mark.parametrize('cartesian,adjusted',[(False,False),(False,True),(True,True)])
def test_absolute_geographic_adjustment_needs_authored_cartesian_context(tmp_path,cartesian,adjusted):
    s,a=scene(tmp_path)
    if not cartesian:s.RemovePrim(a.GetPath());parent='/World'
    else:parent=str(a.GetPath())
    data=anchor(s,parent+'/Data',GEO,[0,0,0]);source=CRS.from_wkt(GEO)
    if adjusted:UsdGeom.Xformable(data).AddTranslateOp().Set((0,1,0))
    r=Runtime(s,ECEF)
    if adjusted and not cartesian:
        with pytest.raises(ContractError,match='explicit Cartesian'):r.measurement(data,[[0,60,0]],source)
    else:
        base=r.convert(source,CRS.from_wkt(ECEF),[[0,60,0]])
        expected=base+([0,1,0] if adjusted else [0,0,0])
        np.testing.assert_allclose(r.measurement(data,[[0,60,0]],source),expected,atol=1e-7,rtol=0)

def test_prototype_storage_parent_does_not_supply_occurrence_context(tmp_path):
    s,a=scene(tmp_path)
    storage=anchor(s,'/Storage',GEO,[0,0,0]);bound=anchor(s,'/Storage/Bound')
    UsdGeom.Xformable(bound).AddTranslateOp().Set((0,1,0));triangle(s,'/Storage/Bound/Mesh')
    i=UsdGeom.PointInstancer.Define(s,'/World/Model/Instances')
    i.CreatePrototypesRel().SetTargets(['/Storage/Bound']);i.CreateProtoIndicesAttr(Vt.IntArray([0]))
    i.CreatePositionsAttr(Vt.Vec3fArray([Gf.Vec3f(0)]))
    # +Y is the Cartesian occurrence working frame, regardless of the geographic storage parent.
    for rec in records(s,tmp_path,geometry=True):
        instance=next(v for k,v in rec['geometry'].items() if '_ResolvedInstance' in k)
        np.testing.assert_allclose(instance[0],ORIGIN+[0,1,0],atol=1e-7,rtol=0)

def test_native_long_wkt_quote_does_not_exhaust_parser_stack(tmp_path):
    s,a=scene(tmp_path);crs=CRS.from_epsg(4978).to_json_dict();crs['name']='Long quoted CRS name '+('a'*20000)
    a.GetAttribute('crs:wkt').Set(normalize(CRS.from_json_dict(crs).to_wkt()))
    for r in records(s,tmp_path,queries=[dict(prim=str(a.GetPath()),points=[[0,0,0]])]):
        np.testing.assert_allclose(r['queries'][0]['coordinates'][0],ORIGIN,atol=1e-7,rtol=0)
