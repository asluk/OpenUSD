"""Authoring and evaluation controls derived from the HPR proposal before execution."""
from pathlib import Path
import math
import numpy as np
import pytest
from pxr import Gf,Sdf,Usd,UsdGeom,Plug
from pyproj import CRS
from candidate.fixtures import attr,mark,claim
from candidate.runtime import Runtime,ContractError
from review.wkt_profile import normalize
from review.placement_values import read
ROOT=Path(__file__).resolve().parents[1]
ECEF=normalize(CRS.from_epsg(4978).to_wkt())

def setup(path):
    Plug.Registry().RegisterPlugins(str(ROOT/'schema/generated/plugInfo.json'))
    stage=Usd.Stage.CreateNew(str(path));p=UsdGeom.Xform.Define(stage,'/Model').GetPrim()
    stage.SetDefaultPrim(p);UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z')
    mark(p,'GeospatialCRSBindingAPI');attr(p,'crs:wkt',Sdf.ValueTypeNames.Token,ECEF,True)
    attr(p,'crs:position',Sdf.ValueTypeNames.Double3,Gf.Vec3d(6378137,0,0))
    return stage,p

def angles(p,first=(170,0,0),last=(-170,0,0)):
    a=p.CreateAttribute('crs:orientation',Sdf.ValueTypeNames.Double3,custom=False)
    a.Set(first,0);a.Set(last,10);return a

def point_for_heading(h):
    return [6378137,2*math.sin(math.radians(h)),2*math.cos(math.radians(h))]

@pytest.mark.parametrize('hpr',[(90,0,0),(0,90,0),(0,0,90),(30,20,10),(15,90,20)])
def test_physical_axes_and_noncommuting_order(tmp_path,hpr):
    s,p=setup(tmp_path/'orientation.usda');attr(p,'crs:orientation',Sdf.ValueTypeNames.Double3,Gf.Vec3d(*hpr))
    h,pi,r=np.radians(hpr)
    # Independent column-vector axis matrices, not the reader's quaternion code.
    U=np.array([[np.cos(h),np.sin(h),0],[-np.sin(h),np.cos(h),0],[0,0,1]])
    E=np.array([[1,0,0],[0,np.cos(pi),-np.sin(pi)],[0,np.sin(pi),np.cos(pi)]])
    N=np.array([[np.cos(r),0,np.sin(r)],[0,1,0],[-np.sin(r),0,np.cos(r)]])
    metric=np.eye(3)@(U@E@N).T
    expected=metric[:,[2,0,1]]+[6378137,0,0]
    np.testing.assert_allclose(Runtime(s,ECEF).placement(p,np.eye(3)),expected,rtol=0,atol=1e-7)

@pytest.mark.parametrize('time,held,expected',[(-5,False,170),(0,False,170),(5,False,180),(10,False,-170),(20,False,-170),(5,True,170)])
def test_sample_conversion_precedes_interpolation(tmp_path,time,held,expected):
    s,p=setup(tmp_path/'samples.usda');a=angles(p)
    s.SetInterpolationType(Usd.InterpolationTypeHeld if held else Usd.InterpolationTypeLinear)
    before=s.GetRootLayer().ExportToString()
    actual=Runtime(s,ECEF,time).placement(p,[[0,2,0]])[0]
    np.testing.assert_allclose(actual,point_for_heading(expected),rtol=0,atol=1e-7)
    assert before==s.GetRootLayer().ExportToString()
    if time==5 and not held:
        assert a.Get(5)==Gf.Vec3d(0,0,0)
        assert np.linalg.norm(actual-point_for_heading(0))>3.99

def test_source_pose_edit_remains_inspectable(tmp_path):
    s,p=setup(tmp_path/'edit.usda');a=p.CreateAttribute('crs:orientation',Sdf.ValueTypeNames.Double3,custom=False)
    a.Set((10,0,0));old=Runtime(s,ECEF).placement(p,[[0,2,0]])[0]
    with Usd.EditContext(s,s.GetSessionLayer()):a.Set((40,0,0))
    before={l.identifier:l.ExportToString() for l in s.GetUsedLayers()}
    new=Runtime(s,ECEF).placement(p,[[0,2,0]])[0]
    np.testing.assert_allclose(new,point_for_heading(40),rtol=0,atol=1e-7)
    assert np.linalg.norm(new-old)>1
    assert a.Get()==Gf.Vec3d(40,0,0)
    assert before=={l.identifier:l.ExportToString() for l in s.GetUsedLayers()}
    assert {x.GetName() for x in p.GetAuthoredProperties() if x.GetName().startswith('crs:')}=={'crs:wkt','crs:position','crs:orientation'}

def test_reference_time_offsets_then_stronger_default(tmp_path):
    source,p=setup(tmp_path/'asset.usda');angles(p);source.GetRootLayer().Save()
    s=Usd.Stage.CreateNew(str(tmp_path/'assembly.usda'))
    UsdGeom.SetStageMetersPerUnit(s,1);UsdGeom.SetStageUpAxis(s,'Z')
    root=UsdGeom.Xform.Define(s,'/Placed').GetPrim()
    root.GetReferences().AddReference(str(tmp_path/'asset.usda'),'/Model',Sdf.LayerOffset(2,2))
    np.testing.assert_allclose(Runtime(s,ECEF,12).placement(root,[[0,2,0]])[0],point_for_heading(180),rtol=0,atol=1e-7)
    a=root.GetAttribute('crs:orientation')
    with Usd.EditContext(s,s.GetSessionLayer()):a.Set((45,0,0))
    np.testing.assert_allclose(Runtime(s,ECEF,12).placement(root,[[0,2,0]])[0],point_for_heading(45),rtol=0,atol=1e-7)

def test_default_query_does_not_substitute_time_samples(tmp_path):
    s,p=setup(tmp_path/'default.usda');angles(p)
    record=read(p,Usd.TimeCode.Default())
    assert record['orientation']=={'real':1.,'imaginary':[0.,0.,0.]}

def test_shortest_pose_path_does_not_infer_winding(tmp_path):
    s,p=setup(tmp_path/'turn.usda');angles(p,(0,0,0),(360,0,0))
    np.testing.assert_allclose(Runtime(s,ECEF,5).placement(p,[[0,2,0]])[0],point_for_heading(0),rtol=0,atol=1e-7)

def test_blocked_required_endpoint_fails_but_held_uses_lower(tmp_path):
    s,p=setup(tmp_path/'blocked.usda');a=angles(p)
    a.Set(Sdf.ValueBlock(),10)
    with pytest.raises(ContractError):Runtime(s,ECEF,5).placement(p,[[0,2,0]])
    s.SetInterpolationType(Usd.InterpolationTypeHeld)
    np.testing.assert_allclose(Runtime(s,ECEF,5).placement(p,[[0,2,0]])[0],point_for_heading(170),rtol=0,atol=1e-7)

def test_wrong_stored_quaternion_type_is_rejected(tmp_path):
    s,p=setup(tmp_path/'wrong-type.usda')
    a=p.CreateAttribute('crs:orientation',Sdf.ValueTypeNames.Double3,custom=False);a.Set((1,0,0))
    spec=s.GetRootLayer().GetAttributeAtPath('/Model.crs:orientation')
    spec.SetInfo('typeName','quatd');spec.default=Gf.Quatd(1)
    with pytest.raises(ContractError,match='wrong type'):Runtime(s,ECEF).placement(p,[[0,2,0]])

def test_value_clip_time_mapping_preserves_orientation_samples(tmp_path):
    clip=Usd.Stage.CreateNew(str(tmp_path/'clip.usda'))
    cp=clip.DefinePrim('/Model');angles(cp);clip.GetRootLayer().Save()
    manifest=Usd.Stage.CreateNew(str(tmp_path/'manifest.usda'))
    manifest.DefinePrim('/Model').CreateAttribute('crs:orientation',Sdf.ValueTypeNames.Double3,custom=False)
    manifest.GetRootLayer().Save()
    s,p=setup(tmp_path/'clipped.usda')
    clips=Usd.ClipsAPI(p)
    clips.SetClipAssetPaths([Sdf.AssetPath(str(tmp_path/'clip.usda'))])
    clips.SetClipManifestAssetPath(Sdf.AssetPath(str(tmp_path/'manifest.usda')))
    clips.SetClipPrimPath('/Model');clips.SetClipActive([(0,0)]);clips.SetClipTimes([(0,0),(20,10)])
    np.testing.assert_allclose(Runtime(s,ECEF,10).placement(p,[[0,2,0]])[0],point_for_heading(180),rtol=0,atol=1e-7)
