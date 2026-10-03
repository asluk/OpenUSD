"""Controls for defects hidden by the earlier candidate-only verification."""
from pathlib import Path
import json,sys
import numpy as np
import pytest
from pxr import Usd,UsdGeom,Sdf,Gf,Vt
from pyproj import CRS
from geobuild.model import normalize_wkt,validate,GeoError
from geobuild.resolve import Resolver
from geobuild.export import export

ROOT=Path(__file__).resolve().parents[1]
T=json.loads((ROOT/'targets.json').read_text())
sys.path.insert(0,str(ROOT/'ov'))
from independent import OVResolver

def composition():
    layer=Sdf.Layer.CreateAnonymous('quality-control.usda')
    layer.ImportFromString((ROOT/'scenes/composition.usda').read_text())
    return Usd.Stage.Open(layer)

def test_delimiter_normalization_preserves_quoted_punctuation():
    canonical=T['ecef'][:-1]+',REMARK["Keep literal [brackets] and (parentheses)"]]'
    parts=[];quoted=False
    for c in canonical:
        if c=='"':quoted=not quoted
        parts.append({'[':'(',']':')'}.get(c,c) if not quoted else c)
    variant=''.join(parts)
    assert normalize_wkt(variant)==canonical
    assert CRS.from_wkt(normalize_wkt(variant))==CRS.from_wkt(canonical)
    assert '[brackets] and (parentheses)' in normalize_wkt(variant)
    with pytest.raises(GeoError):normalize_wkt(variant.replace('GEODCRS(','GEODCRS[',1))
    with pytest.raises(GeoError):normalize_wkt(variant.replace('GEODCRS','GEOD CRS',1))

@pytest.mark.parametrize('defect',['broken','empty','multiple'])
def test_broken_enclosing_binding_cannot_be_treated_as_absent(defect):
    s=composition();parent=s.GetPrimAtPath('/Project');r=parent.GetRelationship('crs:binding')
    r.SetTargets({'broken':['/Missing'],'empty':[],'multiple':['/CRS/Source','/Missing']}[defect])
    p=s.GetPrimAtPath('/Project/Model')
    with pytest.raises(GeoError):Resolver(s).full_points(p,[[0,0,0]],T['utm31'])
    with pytest.raises((ValueError,RuntimeError)):OVResolver(s,T['utm31']).full(p,[[0,0,0]],Usd.TimeCode.Default())

def test_absent_enclosing_binding_still_uses_source_context():
    s=composition();s.GetPrimAtPath('/Project').RemoveProperty('crs:binding')
    p=s.GetPrimAtPath('/Project/Model')
    np.testing.assert_allclose(Resolver(s).full_points(p,[[0,0,0]],T['utm31']).points[0],[1007,2008,39],rtol=0,atol=1e-8)

def test_inherited_measurement_role_receives_authored_checks():
    s=composition();p=s.DefinePrim('/Project/Measurements','Scope')
    a=p.CreateAttribute('samples:locations',Sdf.ValueTypeNames.Float3Array,custom=True)
    a.Set(Vt.Vec3fArray([Gf.Vec3f(1,2,3)]))
    p.CreateRelationship('crs:coordinateProperties',custom=True).SetTargets([a.GetPath()])
    assert any(path==str(p.GetPath()) and 'double3' in message for path,message in validate(s))

def test_nonfixture_names_and_same_prim_associations_export(tmp_path):
    s=Usd.Stage.CreateInMemory();s.GetRootLayer().customLayerData={'geospatialResolutionRequired':True}
    c=s.DefinePrim('/CRS','CoordinateReferenceSystem')
    c.CreateAttribute('crs:wkt',Sdf.ValueTypeNames.Token,custom=True,variability=Sdf.VariabilityUniform).Set(T['geographic'])
    scope=s.DefinePrim('/Dataset','Scope');scope.CreateRelationship('crs:binding',custom=True).SetTargets(['/CRS'])
    p=s.DefinePrim('/Dataset/Samples','Scope')
    coordinates=p.CreateAttribute('samples:locations',Sdf.ValueTypeNames.Double3Array,custom=True)
    coordinates.Set(Vt.Vec3dArray([Gf.Vec3d(2,48,80),Gf.Vec3d(3,49,90)]))
    p.CreateRelationship('crs:coordinateProperties',custom=True).SetTargets([coordinates.GetPath()])
    values=p.CreateAttribute('observations:temperature',Sdf.ValueTypeNames.DoubleArray,custom=True)
    values.Set(Vt.DoubleArray([10,20]),0);values.Set(Vt.DoubleArray([11,21]),10)
    values.SetCustomData({'units':'kelvin'})
    p.CreateRelationship('observations:locations',custom=True).SetTargets([coordinates.GetPath()])
    assert validate(s)==[]
    d=export(s,tmp_path/'measurement-only.usda',T['geographic'],[0,5,10])
    fresh=Usd.Stage.Open(str(tmp_path/'measurement-only.usda'));q=fresh.GetPrimAtPath('/Dataset/Samples')
    assert q.GetAttribute('observations:temperature').GetTimeSamples()==[0,10]
    assert list(q.GetAttribute('observations:temperature').Get(10))==[11,21]
    assert q.GetAttribute('observations:temperature').GetCustomData()['units']=='kelvin'
    assert q.GetRelationship('observations:locations').GetTargets()==[q.GetAttribute('samples:locations').GetPath()]
    np.testing.assert_allclose(next(iter(Resolver(fresh).measures(q,T['geographic'],Usd.TimeCode(5)).values())).points,[[2,48,80],[3,49,90]],rtol=0,atol=1e-9)
    assert validate(d)==[]

def test_default_output_and_explicit_precedence():
    s=composition();s.SetDefaultPrim(s.GetPrimAtPath('/Project'));p=s.GetPrimAtPath('/Project/Model')
    r=Resolver(s)
    np.testing.assert_array_equal(r.frame(p)[0],r.frame(p,T['utm31'])[0])
    np.testing.assert_allclose(OVResolver(s,None).frame(p,Usd.TimeCode.Default())[0],r.frame(p)[0],rtol=0,atol=1e-7)
    assert r.output_definition(T['ecef']).is_geocentric
    s.ClearDefaultPrim()
    with pytest.raises(GeoError,match='defaultPrim'):r.frame(p)
    with pytest.raises(ValueError):OVResolver(s,None)

def test_affine_bounds_include_curve_width_and_ignore_ancestor_placement():
    s=composition();p=s.DefinePrim('/Project/Model/Curve','BasisCurves');c=UsdGeom.BasisCurves(p)
    c.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(0),Gf.Vec3f(2,0,0)]));c.CreateCurveVertexCountsAttr([2]);c.CreateTypeAttr('linear');c.CreateWidthsAttr([2.]);c.SetWidthsInterpolation('constant')
    r=Resolver(s);extent=UsdGeom.Boundable.ComputeExtentFromPlugins(c,Usd.TimeCode.Default());frame,_=r.frame(s.GetPrimAtPath('/Project/Model'),T['utm31'])
    expected=Gf.BBox3d(Gf.Range3d(Gf.Vec3d(extent[0]),Gf.Vec3d(extent[1])),Gf.Matrix4d(frame)).ComputeAlignedRange()
    np.testing.assert_array_equal(r.bounds(p,T['utm31']),[expected.GetMin(),expected.GetMax()])
    assert np.all(r.bounds(p,T['utm31'])[1]-r.bounds(p,T['utm31'])[0]>0)
    with pytest.raises(GeoError,match='Angular'):r.bounds(p,T['geographic'])

def test_relative_frame_of_independent_bound_child():
    s=composition();r=Resolver(s);parent=s.GetPrimAtPath('/Project/Model');child=s.GetPrimAtPath('/Project/Model/Independent')
    a,_=r.frame(parent,T['utm31']);b,_=r.frame(child,T['utm31']);relative=r.relative_frame(child,parent,T['utm31'])
    np.testing.assert_allclose(relative@a,b,rtol=0,atol=1e-7)
    np.testing.assert_allclose(b[3,:3],[20,40,5],rtol=0,atol=1e-8)
    assert not np.allclose(relative[3,:3],child.GetAttribute('crs:position').Get())


def test_readiness_gate_does_not_equate_tests_and_authority():
    from geobuild.quality import require_derivable_proposal,ProposalNotReady
    with pytest.raises(ProposalNotReady,match='Dependent implementation stopped'):
        require_derivable_proposal(ROOT)
    result=require_derivable_proposal(ROOT,experiment=True)
    assert not result['proposal_ready'] and not result['requirements_build_complete']
    assert len(result['open_semantic_gap_ids'])==10


def test_export_preserves_both_instance_representations(tmp_path):
    s=Usd.Stage.Open(str(ROOT/'scenes/instances.usda'));before={l.identifier:l.ExportToString() for l in s.GetUsedLayers()}
    fresh=export(s,tmp_path/'instances.usda',T['utm31'],[0,5,10])
    assert before=={l.identifier:l.ExportToString() for l in s.GetUsedLayers()}
    assert len([p for p in fresh.Traverse() if p.IsA(UsdGeom.PointInstancer)])==1
    for t in [0,5,10]:
        time=Usd.TimeCode(t);one=OVResolver(s,T['utm31']).records(time);two=OVResolver(fresh,T['utm31']).records(time)
        for domain in ['geometry','point_instances']:
            assert set(one[domain])==set(two[domain])
            for key in one[domain]:np.testing.assert_allclose(one[domain][key],two[domain][key],rtol=0,atol=.002)
    with pytest.raises(GeoError,match='new asset'):export(s,tmp_path/'instances.usda',T['utm31'],[0])
    assert 'outputCRS' not in fresh.GetRootLayer().customLayerData['geospatialExport']
