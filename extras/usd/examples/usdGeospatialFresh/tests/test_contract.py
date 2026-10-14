import math,sys
from pathlib import Path
import numpy as np
import pytest
from pxr import Gf,Sdf,Usd,UsdGeom
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from fixtures import stage,bind,wkt,measurement,cf_dataset,publish_fixture
from errors import ResolutionFailure
from scene import Reader
from geodesy import Definition,Operations,configure_resources
from wkt import normalize
from profiles import discover,publisher_audit
from measurements import resolve as measurements

configure_resources(ROOT.parent/'geospatial-model-resources')

def result(s,path='/World/Anchor',p=(0,0,0),output=4978,time=None):
    return np.asarray(Reader(s).coordinates(path,p,wkt(output),time)['coordinates'])

@pytest.mark.parametrize('local,expected',[((0,0,0),(6378137,0,0)),((1,0,0),(6378137,1,0)),((0,1,0),(6378137,0,1)),((0,0,1),(6378138,0,0))])
def test_ellipsoid_normal_model(local,expected):
    s=stage();bind(s,'/World/Anchor');np.testing.assert_allclose(result(s,p=local),expected,atol=1e-8,rtol=0)

@pytest.mark.parametrize('angles,local,expected',[((90,0,0),(0,1,0),(6378137,1,0)),((0,90,0),(0,1,0),(6378138,0,0)),((0,0,90),(1,0,0),(6378136,0,0)),((360,0,0),(0,1,0),(6378137,0,1))])
def test_physical_attitude(angles,local,expected):
    s=stage();bind(s,'/World/Anchor',orientation=angles);np.testing.assert_allclose(result(s,p=local),expected,atol=1e-8,rtol=0)

@pytest.mark.parametrize('up,unit,p,expected',[('Y',1,(0,1,0),(6378138,0,0)),('Y',.01,(0,0,-100),(6378137,0,1)),('Z',.3048,(1,0,0),(6378137,.3048,0))])
def test_stage_mapping(up,unit,p,expected):
    s=stage(up=up,unit=unit);bind(s,'/World/Anchor');np.testing.assert_allclose(result(s,p=p),expected,atol=1e-8,rtol=0)

def test_descendant_translation_follows_attitude():
    s=stage();bind(s,'/World/Anchor',orientation=(90,0,0));c=UsdGeom.Xform.Define(s,'/World/Anchor/Child');c.AddTranslateOp().Set((0,10,0))
    np.testing.assert_allclose(result(s,str(c.GetPath())),(6378137,10,0),atol=1e-8,rtol=0)

def test_direct_binding_is_absolute_and_keeps_working_context():
    s=stage();parent=bind(s,'/World/Parent');UsdGeom.Xformable(parent).AddTranslateOp().Set((1000,0,0));child=bind(s,'/World/Parent/Anchor');
    np.testing.assert_allclose(result(s,str(child.GetPath())),(6378137,0,0),atol=1e-8,rtol=0)

def test_descendant_reset_removes_ancestor_adjustment():
    s=stage();a=bind(s,'/World/Anchor');UsdGeom.Xformable(a).AddTranslateOp().Set((1000,0,0));c=UsdGeom.Xform.Define(s,'/World/Anchor/Child');c.AddTranslateOp().Set((0,10,0));c.SetResetXformStack(True)
    np.testing.assert_allclose(result(s,str(c.GetPath())),(6378137,0,10),atol=1e-8,rtol=0)

@pytest.mark.parametrize('field,role',[('crs:position','child'),('crs:orientation','child'),('crs:position','measurement'),('crs:orientation','measurement')])
def test_invalid_authored_placement_role(field,role,tmp_path):
    s=stage();bind(s,'/World/Anchor');c=s.DefinePrim('/World/Anchor/Child','GeospatialDataSource' if role=='measurement' else 'Xform');c.CreateAttribute(field,Sdf.ValueTypeNames.Double3).Set((1,2,3))
    if role=='measurement':
        from scene import placement_fields_valid
        with pytest.raises(ResolutionFailure,match='invalid-placement-role'):placement_fields_valid(c)
    else:
        with pytest.raises(ResolutionFailure,match='invalid-placement-role'):result(s,str(c.GetPath()))

@pytest.mark.parametrize('field',['crs:position','crs:orientation'])
def test_blocked_placement(field):
    s=stage();p=bind(s,'/World/Anchor');p.GetAttribute(field).Block()
    with pytest.raises(ResolutionFailure,match='unavailable'):result(s)

def test_missing_position_has_no_zero_fallback():
    s=stage();bind(s,'/World/Anchor',pos=None)
    with pytest.raises(ResolutionFailure,match='unavailable-placement'):result(s)

@pytest.mark.parametrize('value',[math.nan,math.inf,-math.inf])
def test_nonfinite_position(value):
    s=stage();bind(s,'/World/Anchor',pos=(value,0,0))
    with pytest.raises(ResolutionFailure,match='non-finite'):result(s)

def test_uniform_sample_source_is_invalid():
    s=stage();p=bind(s,'/World/Anchor');p.GetAttribute('crs:wkt').Set(wkt(4979),1)
    with pytest.raises(ResolutionFailure,match='uniform-time-samples'):result(s)

def test_geocentric_pole_attitude_not_invented():
    s=stage();bind(s,'/World/Anchor',wkt(4978),(0,0,6356752))
    with pytest.raises(ResolutionFailure,match='undetermined-pole-meridian'):result(s)

def test_geocentric_nonpole_attitude():
    s=stage();bind(s,'/World/Anchor',wkt(4978),(6378137,0,0))
    np.testing.assert_allclose(result(s,p=(1,0,0)),(6378137,1,0),atol=1e-8,rtol=0)

def test_source_longitude_interpolates_before_conversion():
    s=stage();p=bind(s,'/World/Anchor');a=p.GetAttribute('crs:position');a.Clear();a.Set((-1,0,0),0);a.Set((1,0,0),2)
    np.testing.assert_allclose(result(s,time=1),(6378137,0,0),atol=1e-8,rtol=0)
    endpoints=np.array([result(s,time=0),result(s,time=2)])
    assert 970<np.linalg.norm(result(s,time=1)-endpoints.mean(axis=0))<973

@pytest.mark.parametrize('time,held,should_fail',[(0,False,False),(1,False,True),(2,False,False),(1,True,False)])
def test_half_turn_samples(time,held,should_fail):
    s=stage();p=bind(s,'/World/Anchor');a=p.GetAttribute('crs:orientation');a.Set((0,0,0),0);a.Set((180,0,0),2)
    if held:s.SetInterpolationType(Usd.InterpolationTypeHeld)
    if should_fail:
        with pytest.raises(ResolutionFailure,match='ambiguous-half-turn'):result(s,time=time)
    else:assert np.all(np.isfinite(result(s,time=time)))

def test_default_time_does_not_read_sample():
    s=stage();p=bind(s,'/World/Anchor');a=p.GetAttribute('crs:orientation');a.Set((90,0,0),1)
    np.testing.assert_allclose(result(s,p=(0,1,0)),(6378137,0,1),atol=1e-8,rtol=0)

def test_intermediate_pose_defines_half_turn_path():
    s=stage();p=bind(s,'/World/Anchor');a=p.GetAttribute('crs:orientation');a.Set((0,0,0),0);a.Set((90,0,0),1);a.Set((180,0,0),2)
    np.testing.assert_allclose(result(s,p=(0,1,0),time=.5),(6378137,math.sqrt(.5),math.sqrt(.5)),atol=1e-8,rtol=0)

@pytest.mark.parametrize('text,expected',[('1.00','1'),('+1E0','1'),('0.50','0.5'),('-0.000E3','0'),('12345678901234567890.1234500','12345678901234567890.12345')])
def test_exact_numeric_normalization(text,expected):assert normalize('TEST['+text+']')=='TEST['+expected+']'

def test_quoted_keyword_is_not_epoch_wrapper():
    text=wkt(4979).replace('WGS 84','COORDINATEMETADATA',1);s=stage();bind(s,'/World/Anchor',text)
    np.testing.assert_allclose(result(s),(6378137,0,0),atol=1e-8,rtol=0)

def test_reader_accepts_parentheses_and_whitespace():
    text=CRS_wkt=wkt(4979).replace('[','(').replace(']',')');s=stage();bind(s,'/World/Anchor',' \n'+text+'\n ')
    r=Reader(s).coordinates('/World/Anchor',(0,0,0),wkt(4978));assert 'non-normal-wkt-spelling' in r['warnings']

def test_deferred_epoch_wrapper_rejected():
    with pytest.raises(ResolutionFailure,match='deferred-coordinate-epoch'):Definition('COORDINATEMETADATA['+wkt(4979)+',EPOCH[2026]]')

def test_source_layer_is_unchanged():
    s=stage();bind(s,'/World/Anchor');before=s.GetRootLayer().ExportToString();result(s);assert s.GetRootLayer().ExportToString()==before

def test_geographic_scene_points_are_cartesian():
    s=stage();bind(s,'/World/Anchor');r=Reader(s).scene_points('/World/Anchor',[(0,0,0)],wkt(4979));np.testing.assert_allclose(r['scene_points'],[(6378137,0,0)],atol=1e-8);assert 'GEODCRS' in r['scene_chart_wkt']

def test_analytic_normal_inverse_transpose():
    s=stage();a=bind(s,'/World/Anchor');n=Reader(s).normal('/World/Anchor',[(0,0,1)],wkt(4978));np.testing.assert_allclose(n,[(1,0,0)],atol=1e-12)

@pytest.mark.parametrize('name,required,complete,expected',[('proof-hard',True,True,'required'),('proof-none',False,True,'known-none'),('proof-unknown',False,False,'unknown')])
def test_profiles_closed_payload(name,required,complete,expected):
    p=publish_fixture(name,required,complete);s=Usd.Stage.Open(str(p),Usd.Stage.LoadNone);before=set(s.GetLoadSet());r=discover(s);assert r['state']==expected;assert set(s.GetLoadSet())==before==set();assert not s.GetPrimAtPath('/World/Model')

def test_profiles_publisher_catches_unselected_variant():
    p=publish_fixture('proof-stale',False,True,True);r=publisher_audit(p);assert not r['valid'];assert r['retained_requires_geospatial'];assert len(r['alternatives_checked'])==2

def test_cf_dimension_permutation_and_time(tmp_path):
    path=tmp_path/'native.nc';cf_dataset(path);s=stage();p=measurement(s,'/World/Data',path,'CF','temperature','earth',wkt(4979));r=measurements(p,wkt(4979));i=2*11+3
    np.testing.assert_allclose(r['coordinates'][i],[-150+3*30+2*.1,-60+2*20+3*.05,80],atol=1e-10)
    assert r['values'][i]==pytest.approx(270+2*2+3*.1);assert r['dimension_names']==['time','north','east'];assert len(r['observation_times'])==1
    assert r['mask'].sum()==1

def test_unlabelled_netcdf_is_not_cf_association():
    s=stage();p=measurement(s,'/World/Data',ROOT/'data/gfs_t2m.nc','CF','t2m','earth',wkt(4979))
    with pytest.raises(ResolutionFailure,match='missing-native-association'):measurements(p,wkt(4979))
