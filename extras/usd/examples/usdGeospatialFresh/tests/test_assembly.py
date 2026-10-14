from pathlib import Path
import sys
import numpy as np
import pytest
from pxr import Gf,Sdf,Usd,UsdGeom,Vt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from fixtures import stage,bind,wkt,points,measurement
from scene import Reader
from geodesy import Definition,Operations
from errors import ResolutionFailure
from export import geometry_bake,occurrence_bake
from queries import relative_position,physical_distance,bounds
from measurements import resolve
from profiles import discover

def instance_scene(independent=True,offset=(10,0,0),context=True,child_binding=False):
    s=stage()
    if context:bind(s,'/World',pos=(0,0,0))
    # A misleading storage ancestor must not become occurrence context.
    store=bind(s,'/Library',wkt(4979),(70,20,0));UsdGeom.Xformable(store).AddTranslateOp().Set((1000,0,0))
    proto=bind(s,'/Library/Prototype') if independent else UsdGeom.Xform.Define(s,'/Library/Prototype').GetPrim()
    if child_binding:
        geo=bind(s,'/Library/Prototype/Shape');mesh=points(geo,[(0,0,0),(1,0,0),(0,1,0)])
    else:mesh=points(proto,[(0,0,0),(1,0,0),(0,1,0)])
    pi=UsdGeom.PointInstancer.Define(s,'/World/Inst')
    pi.GetPrototypesRel().SetTargets([proto.GetPath()]);pi.GetProtoIndicesAttr().Set([0]);pi.GetPositionsAttr().Set([Gf.Vec3f(*offset)])
    pi.GetIdsAttr().Set([1234])
    return s,pi,mesh

@pytest.mark.parametrize('independent',[True,False])
def test_instancer_local_offset_once(independent):
    s,pi,mesh=instance_scene(independent)
    r=Reader(s).point_instance(str(pi.GetPath()),0,str(mesh.GetPath()),[(0,0,0)],wkt(4978))
    np.testing.assert_allclose(r['coordinates'],[(6378137,10,0)],atol=1e-8,rtol=0)
    assert r['instance_identity']['prototype_relative_path']=='Mesh'

def test_identity_independent_instance_needs_no_instancer_context():
    s,pi,mesh=instance_scene(True,(0,0,0),False)
    r=Reader(s).point_instance(str(pi.GetPath()),0,str(mesh.GetPath()),[(0,0,0)],wkt(4978))
    np.testing.assert_allclose(r['coordinates'],[(6378137,0,0)],atol=1e-8,rtol=0)

def test_nonidentity_independent_instance_requires_context():
    s,pi,mesh=instance_scene(True,(10,0,0),False)
    with pytest.raises(ResolutionFailure,match='unbound-content'):Reader(s).point_instance(str(pi.GetPath()),0,str(mesh.GetPath()),[(0,0,0)],wkt(4978))

def test_independently_bound_prototype_descendant():
    s,pi,mesh=instance_scene(False,child_binding=True)
    r=Reader(s).point_instance(str(pi.GetPath()),0,str(mesh.GetPath()),[(0,0,0)],wkt(4978))
    np.testing.assert_allclose(r['coordinates'],[(6378137,10,0)],atol=1e-8,rtol=0)

def test_instance_mask_is_not_geometry():
    s,pi,mesh=instance_scene();pi.GetInvisibleIdsAttr().Set([1234])
    with pytest.raises(ResolutionFailure,match='masked-instance'):Reader(s).point_instance(str(pi.GetPath()),0,str(mesh.GetPath()),[(0,0,0)],wkt(4978))

def test_anchor_adjustment_preserved_across_requested_outputs():
    s=stage();a=bind(s,'/World/Anchor',wkt(4979),(2,49,80));UsdGeom.Xformable(a).AddTranslateOp().Set((10,0,0))
    reader=Reader(s);geographic=np.asarray(reader.coordinates('/World/Anchor',[(0,0,0)],wkt(4979))['coordinates'])
    cartesian=np.asarray(reader.coordinates('/World/Anchor',[(0,0,0)],wkt(4978))['coordinates'])
    ops=Operations();reconverted=ops.convert(geographic,Definition(wkt(4979)),Definition(wkt(4978)))
    np.testing.assert_allclose(reconverted,cartesian,atol=1e-7,rtol=0)

def test_layer_reference_time_offset(tmp_path):
    asset=stage(tmp_path/'asset.usda');a=bind(asset,'/World');p=a.GetAttribute('crs:position');p.Clear();p.Set((-1,0,0),0);p.Set((1,0,0),2);asset.GetRootLayer().Save()
    assembly=stage();ref=assembly.DefinePrim('/World/Asset','Xform');ref.GetReferences().AddReference(str(tmp_path/'asset.usda'),'/World',Sdf.LayerOffset(10,2))
    r=Reader(assembly).coordinates('/World/Asset',[(0,0,0)],wkt(4978),12)
    np.testing.assert_allclose(r['coordinates'],[(6378137,0,0)],atol=1e-8,rtol=0)

def test_value_clips_select_orientation_endpoints(tmp_path):
    clip=stage(tmp_path/'clip.usda');p=bind(clip,'/World');a=p.GetAttribute('crs:orientation');a.Set((0,0,0),0);a.Set((90,0,0),2);clip.GetRootLayer().Save()
    s=stage();p=bind(s,'/World/Anchor');api=Usd.ClipsAPI(p);api.SetClipAssetPaths([Sdf.AssetPath(str(tmp_path/'clip.usda'))]);api.SetClipPrimPath('/World');api.SetClipActive([(0,0)]);api.SetClipTimes([(0,0),(2,2)])
    r=Reader(s).coordinates('/World/Anchor',[(0,1,0)],wkt(4978),1)
    np.testing.assert_allclose(r['coordinates'],[(6378137,np.sqrt(.5),np.sqrt(.5))],atol=1e-8,rtol=0)

def test_strong_default_masks_weaker_uniform_samples(tmp_path):
    weak=stage(tmp_path/'weak.usda');p=bind(weak,'/World/Anchor');p.GetAttribute('crs:wkt').Set(wkt(4979),0);weak.GetRootLayer().Save()
    strong=stage();strong.GetRootLayer().subLayerPaths.append(str(tmp_path/'weak.usda'));p=strong.OverridePrim('/World/Anchor');p.CreateAttribute('crs:wkt',Sdf.ValueTypeNames.Token,custom=False,variability=Sdf.VariabilityUniform).Set(wkt(4979))
    r=Reader(strong).coordinates('/World/Anchor',[(0,0,0)],wkt(4978));assert r['success']

def test_baked_origin_once_and_parent_xform(tmp_path):
    s=stage();a=bind(s,'/World/Anchor');mesh=points(a,[(0,0,0),(1,0,0),(0,1,0)])
    path=tmp_path/'bake.usda';receipt=geometry_bake(s,path,wkt(4978),numeric_origin=(6378137,0,0))
    fresh=Usd.Stage.Open(str(path));geom=UsdGeom.Mesh(fresh.GetPrimAtPath(receipt['controls'][0]['export_path']));p=np.asarray(geom.GetPointsAttr().Get())
    r=Reader(fresh).coordinates(str(geom.GetPath()),p,wkt(4978))
    np.testing.assert_allclose(r['coordinates'],[(6378137,0,0),(6378137,1,0),(6378137,0,1)],atol=1e-8,rtol=0)
    aware=np.asarray(r['coordinates']);unaware=np.array([UsdGeom.XformCache().GetLocalToWorldTransform(geom.GetPrim()).Transform(Gf.Vec3d(*v.tolist())) for v in p])
    np.testing.assert_allclose(aware,unaware,atol=1e-8,rtol=0)
    assert discover(fresh)['state']=='known-none'
    assembled=stage();parent=UsdGeom.Xform.Define(assembled,'/World/Parent');parent.AddTranslateOp().Set((1000,0,0));ref=assembled.DefinePrim('/World/Parent/Copy','CoordinateReferenceSystem');ref.GetReferences().AddReference(str(path),'/World')
    meshpath='/World/Parent/Copy'+str(geom.GetPath())[len('/World'):]
    r=Reader(assembled).coordinates(meshpath,p,wkt(4978));np.testing.assert_allclose(r['coordinates'],aware+[1000,0,0],atol=1e-8,rtol=0)

def test_instance_occurrence_export(tmp_path):
    s,pi,mesh=instance_scene();path=tmp_path/'instances.usda';receipt=occurrence_bake(s,path,str(pi.GetPath()),wkt(4978),numeric_origin=(6378137,0,0))
    fresh=Usd.Stage.Open(str(path));target=UsdGeom.Mesh(fresh.GetPrimAtPath(receipt['controls'][0]['export_path']))
    r=Reader(fresh).coordinates(str(target.GetPath()),np.asarray(target.GetPointsAttr().Get()),wkt(4978))
    np.testing.assert_allclose(r['coordinates'][0],(6378137,10,0),atol=1e-8,rtol=0);assert receipt['controls'][0]['id']==1234

def test_relative_difference_is_not_relative_frame():
    s=stage();bind(s,'/World/A',wkt(4979),(1,0,0));bind(s,'/World/B',wkt(4979),(-1,0,0))
    r=relative_position(s,'/World/A','/World/B',wkt(4979));assert r['from_minus_to']==pytest.approx([2,0,0]);assert r['meaning']=='angular/height component difference';assert physical_distance(s,'/World/A','/World/B',wkt(4979))['distance_metres']>200000

def test_continuous_bound_not_inferred_from_vertices():
    s=stage();bind(s,'/World/Anchor')
    with pytest.raises(ResolutionFailure,match='uncertified-continuous-domain'):bounds(s,'/World/Anchor',[(0,0,0),(1,1,1)],wkt(4978),continuous=True)

@pytest.mark.parametrize('point',[False,True])
def test_geotiff_pixel_mapping_and_absent_height(tmp_path,point):
    import rasterio
    from rasterio.transform import from_origin
    path=tmp_path/'image.tif';a=np.arange(6,dtype=np.float32).reshape(2,3)
    with rasterio.open(path,'w',driver='GTiff',height=2,width=3,count=1,dtype='float32',crs='EPSG:32632',transform=from_origin(500000,4100000,10,10)) as ds:
        ds.write(a,1);ds.update_tags(AREA_OR_POINT='Point' if point else 'Area')
    s=stage();p=measurement(s,'/World/Image',path,'GeoTIFF','1','0',wkt(32632));r=resolve(p,wkt(32632))
    np.testing.assert_allclose(r['coordinates'][0],[500005,4099995],atol=1e-8);assert r['values'][5]==5
    with pytest.raises(ResolutionFailure,match='missing-height'):resolve(p,wkt(4978))

def test_binding_role_cannot_be_scope():
    s=stage();p=s.DefinePrim('/World/NotXformable','Scope');p.AddAppliedSchema('GeospatialCRSBindingAPI');p.CreateAttribute('crs:wkt',Sdf.ValueTypeNames.Token,variability=Sdf.VariabilityUniform).Set(wkt(4979));p.GetAttribute('crs:position').Set((0,0,0))
    with pytest.raises(ResolutionFailure,match='invalid-binding-role'):Reader(s).coordinates(str(p.GetPath()),[(0,0,0)],wkt(4978))
