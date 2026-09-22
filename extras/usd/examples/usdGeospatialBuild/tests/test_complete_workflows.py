import json
import math
import os
from pathlib import Path
import numpy as np
import pytest
from pxr import Gf, Sdf, Usd, UsdGeom
from pyproj import CRS
from geobuild.datasets import sha
from geobuild.demonstrations import railway_original, railway_provider, field_overlay, aeco_site, GEO, ECEF, UTM
from geobuild.operations import ProjOperations, KarneyOperations
from geobuild.runtime import SceneResolver, Experiment, definition, bind, position, export_resolved
from geobuild.hydra import consume
from test_workflows import dataset_file
from test_scene_runtime import scene


def evidence(name, value):
    folder=os.environ.get('GEO_DEMONSTRATIONS')
    if folder:
        path=Path(folder)
        path.mkdir(parents=True,exist_ok=True)
        (path/(name+'.json')).write_text(json.dumps(value,allow_nan=False),encoding='utf-8')


def test_complete_W01_railway_all_vertices_tiles_and_topology(record_property):
    source=dataset_file('railway-geojson','1kmE4334N3375.geojson')
    provider=dataset_file('railway','deutschebahn-rails.usda')
    before=sha(source),sha(provider)
    stage,expected,data=railway_original(source)
    result=SceneResolver(stage,experiment=Experiment(placement='per_vertex')).resolve()
    maximum=0
    total=0
    for path,coordinates in expected.items():
        maximum=max(maximum,float(np.linalg.norm(result.world_points(path)-coordinates,axis=1).max()))
        total+=len(coordinates)
        assert sum(result.prims[path]['counts'])==len(coordinates)
    assert maximum < .0001
    provider_stage=railway_provider(provider)
    provider_result=SceneResolver(provider_stage,experiment=Experiment(placement='per_vertex')).resolve()
    tangent_result=SceneResolver(provider_stage,experiment=Experiment(placement='per_vertex',offset_basis='cartesian_tangent')).resolve()
    hydra=consume([result,provider_result,tangent_result])
    assert hydra['maximum_consumer_residual_output_units'] < .001
    # Independently compare every retained curve point to original source positions.
    by_id={f['id']: f for f in data['features']}
    residuals=[]
    tangent_residuals=[]
    tiles=[]
    engine=ProjOperations()
    for prim in provider_stage.Traverse():
        attr=prim.GetAttribute('ObjectId')
        if attr and by_id[attr.Get()]['geometry']=='LineString':
            source_points=engine.convert(GEO,UTM,by_id[attr.Get()]['points']).coordinates
            child=next(c for c in prim.GetChildren() if c.IsA(UsdGeom.BasisCurves))
            actual=provider_result.world_points(child.GetPath())
            assert len(actual)==len(source_points)
            residuals.extend(np.linalg.norm(actual-np.array(source_points),axis=1).tolist())
            tangent_residuals.extend(np.linalg.norm(tangent_result.world_points(child.GetPath())-np.array(source_points),axis=1).tolist())
        if prim.IsA(UsdGeom.Mesh) and not prim.GetParent().GetAttribute('ObjectId'):
            points=provider_result.world_points(prim.GetPath()) if str(prim.GetPath()) in provider_result.prims else []
            if len(points):
                tiles.append({'path':str(prim.GetPath()),'points':points.tolist()})
    assert len(residuals)==3526 and len(tiles)==3
    assert max(tangent_residuals) < .0001, 'Local Cartesian interpretation must retain the original curve within float-point quantization'
    assert (sha(source),sha(provider))==before
    evidence('railway',{'curves':[{'id':f['id'],'points':result.world_points(f'/World/Feature_{i}/Boundary').tolist()}
                                 for i,f in enumerate(data['features']) if f['geometry']=='LineString'],
                        'tiles':tiles,'provider_curve_residuals_m':residuals,'cartesian_tangent_residuals_m':tangent_residuals,
                        'hypothesis':'WGS84 ellipsoidal third ordinate; provider vertical datum/epoch unknown'})
    record_property('features_resolved',len(expected))
    record_property('vertices_checked',total)
    record_property('fresh_conversion_vertex_residual_m',maximum)
    record_property('provider_interior_max_discrepancy_m',max(residuals))
    record_property('cartesian_tangent_interior_max_discrepancy_m',max(tangent_residuals))
    record_property('map_tiles_resolved',len(tiles))
    record_property('hydra_nonhydra_max_residual_m',hydra['maximum_consumer_residual_output_units'])


def test_complete_W02_field_all_samples_overlay_and_query(record_property):
    source=dataset_file('scalar-field','gfs_t2m.nc')
    before=sha(source)
    base,visual,coordinates,data=field_overlay(source)
    baseline=base.GetRootLayer().ExportToString()
    base_result=SceneResolver(base).resolve()
    rendered=SceneResolver(visual).resolve()
    assert len([p for p in base_result.prims.values() if p['points']])==0
    for index,point in enumerate(coordinates):
        assert math.dist(rendered.world_position(f'/World/Sample_{index}/Marker'),point) < 1e-8
    hydra=consume([rendered,base_result])
    assert len(hydra['frames'][1]['removed'])==2664
    assert base.GetRootLayer().ExportToString()==baseline and sha(source)==before
    evidence('field',{'ecef':coordinates,'lon_lat_third':data['points'],'values':data['values'],'shape':data['shape']})
    record_property('samples_resolved',len(coordinates))
    record_property('overlay_prims_removed',len(hydra['frames'][1]['removed']))
    record_property('hydra_nonhydra_max_residual_m',hydra['maximum_consumer_residual_output_units'])


def test_complete_W03_same_place_across_frames_and_units(record_property):
    proj,independent=ProjOperations(),KarneyOperations()
    residuals=[]
    # Independent exact TM, geocentric and geographic paths, both hemispheres.
    for point,code in [((-73.985656,40.748817,0),32618),((151.214,-33.857,58),32756),
                       ((174.7762,-41.2865,5),32760),((-78.4678,-.1807,2850),32717),((15.65,78.22,10),32633)]:
        target=CRS.from_epsg(code).to_3d().to_wkt()
        stage,anchor=scene(point)
        geographic=SceneResolver(stage).resolve()
        projected=proj.convert(GEO,target,[point]).coordinates[0]
        definition(stage,'/CRS/Projected',target)
        bind(anchor,'/CRS/Projected')
        position(anchor,projected)
        resolved=SceneResolver(stage,engine=independent).resolve()
        residuals.append(math.dist(geographic.world_position(anchor.GetPath()),resolved.world_position(anchor.GetPath())))
    assert max(residuals)<1e-6
    # Same physical cube authored in centimetres/Y-up and metres/Z-up.
    centimetres, _=scene(up='Y',metres=.01)
    UsdGeom.Cube(centimetres.GetPrimAtPath('/World/Asset/Detail')).GetSizeAttr().Set(1)
    metres,_=scene()
    a=SceneResolver(centimetres).resolve().bounds()
    b=SceneResolver(metres).resolve().bounds()
    np.testing.assert_allclose(a,b,atol=1e-7,rtol=0)
    wrong=SceneResolver(centimetres,experiment=Experiment(units='author_conformed')).resolve().bounds()
    assert np.linalg.norm(np.array(wrong)-a)>.1
    record_property('independent_scene_origin_residual_m',max(residuals))


def test_complete_W04_site_grid_relocation_conformance_and_incline(record_property):
    source=os.environ.get('GEO_AECO_SCENE')
    if not source:
        pytest.skip('Private site fixture not supplied')
    folder=Path(source).parent
    hashes={p.name:sha(p) for p in folder.iterdir() if p.is_file()}
    stage,anchor=aeco_site(folder)
    resolver=SceneResolver(stage)
    initial=resolver.resolve()
    calibration=initial.world_position('/World/Site')
    assert math.dist(calibration,(648200,6862200,33))<1e-5
    height=initial.bounds()[1][2]-initial.bounds()[0][2]
    assert abs(height-300)<.01
    placement=Gf.Matrix4d().SetTranslate(Gf.Vec3d(100,-50,2))
    anchor.GetAttribute('geo:projectTransform').Set(placement)
    moved=resolver.resolve()
    for path,item in initial.prims.items():
        if item['points']:
            np.testing.assert_allclose(moved.world_points(path)-initial.world_points(path),
                                       np.tile((100,-50,2),(len(item['points']),1)),atol=.001,rtol=0)
    # Explicit synthetic inclined foundation: ordinary local modelling, not datum metadata.
    tower=UsdGeom.Xformable(stage.GetPrimAtPath('/World/Site/Tower'))
    tower.AddRotateXOp().Set(5)
    inclined=resolver.resolve()
    assert abs(inclined.bounds()[1][2]-moved.bounds()[1][2])>.1
    hydra=consume([initial,moved,inclined])
    assert hydra['maximum_consumer_residual_output_units'] < .001
    assert all(sha(folder/name)==value for name,value in hashes.items())
    evidence('site',{'initial_bounds':initial.bounds(),'moved_bounds':moved.bounds(),
                     'inclined_bounds':inclined.bounds(),'calibration':calibration,
                     'tower_origin':initial.world_position('/World/Site/Tower')})
    record_property('asset_height_m',height)
    record_property('geometry_vertices',sum(len(p['points']) for p in initial.prims.values()))
    record_property('site_calibration_residual_m',math.dist(calibration,(648200,6862200,33)))
    record_property('hydra_nonhydra_max_residual_m',hydra['maximum_consumer_residual_output_units'])


@pytest.mark.parametrize('arc',['sublayer','reference','payload','inherit','specialize','variant','instance'])
def test_complete_W05_composition_arcs_edit_and_instances(arc,record_property):
    source,source_anchor=scene()
    definition(source,'/World/Asset/CRS',GEO)
    bind(source_anchor,'/World/Asset/CRS')
    expected=SceneResolver(source).resolve()
    if arc=='sublayer':
        layer=Sdf.Layer.CreateAnonymous()
        layer.subLayerPaths=[source.GetRootLayer().identifier]
        stage=Usd.Stage.Open(layer)
        # Dependency declaration is a chosen local layer-root preflight record.
        stage.GetRootLayer().customLayerData=source.GetRootLayer().customLayerData
        UsdGeom.SetStageMetersPerUnit(stage,1)
        UsdGeom.SetStageUpAxis(stage,'Z')
    else:
        stage,anchor=scene()
        stage.RemovePrim('/World/Asset')
        anchor=UsdGeom.Xform.Define(stage,'/World/Asset').GetPrim()
        if arc in ('reference','payload','instance'):
            if arc=='payload':
                anchor.GetPayloads().AddPayload(source.GetRootLayer().identifier,'/World/Asset')
            else:
                anchor.GetReferences().AddReference(source.GetRootLayer().identifier,'/World/Asset')
            if arc=='instance':
                anchor.SetInstanceable(True)
        elif arc in ('inherit','specialize'):
            Sdf.CopySpec(source.GetRootLayer(),'/World/Asset',stage.GetRootLayer(),'/Template')
            stage.GetPrimAtPath('/Template').SetSpecifier(Sdf.SpecifierClass)
            if arc=='inherit': anchor.GetInherits().AddInherit('/Template')
            else: anchor.GetSpecializes().AddSpecialize('/Template')
        else:
            variants=anchor.GetVariantSets().AddVariantSet('placement')
            variants.AddVariant('native')
            variants.SetVariantSelection('native')
            with variants.GetVariantEditContext():
                anchor.GetReferences().AddReference(source.GetRootLayer().identifier,'/World/Asset')
    resolver=SceneResolver(stage)
    composed=resolver.resolve()
    np.testing.assert_allclose(composed.world_points('/World/Asset/Detail'),expected.world_points('/World/Asset/Detail'),atol=1e-8,rtol=0)
    flat=Usd.Stage.Open(stage.Flatten())
    np.testing.assert_allclose(SceneResolver(flat).resolve().world_points('/World/Asset/Detail'),composed.world_points('/World/Asset/Detail'),atol=1e-8,rtol=0)
    position(stage.GetPrimAtPath('/World/Asset'),(10.001,53,50))
    changed=resolver.resolve()
    assert math.dist(changed.world_position('/World/Asset'),composed.world_position('/World/Asset'))>60
    native=consume([composed,changed])
    assert native['frames'][1]['dirtied']
    record_property('composed_arc',arc)


def test_complete_W05_point_instances_masks_and_export(tmp_path,record_property):
    stage,anchor=scene()
    inst=UsdGeom.PointInstancer.Define(stage,'/World/Asset/Instances')
    cube=UsdGeom.Cube.Define(stage,'/World/Asset/Instances/Prototype')
    cube.GetSizeAttr().Set(1)
    inst.GetPrototypesRel().SetTargets([cube.GetPath()])
    inst.GetProtoIndicesAttr().Set([0,0,0])
    inst.GetPositionsAttr().Set([(0,0,0),(10,0,0),(20,0,0)])
    inst.GetIdsAttr().Set([10,11,12])
    inst.GetInvisibleIdsAttr().Set([11])
    result=SceneResolver(stage).resolve()
    paths=[p for p in result.prims if 'point_instance' in result.prims[p]]
    assert len(paths)==2 and all('Prototype' not in p for p in result.prims)
    assert 19.99 < math.dist(result.world_position(paths[0]),result.world_position(paths[1])) < 20.01
    baked=export_resolved([result],tmp_path/'instances.usda')
    again=SceneResolver(baked).resolve()
    for path in paths:
        np.testing.assert_allclose(again.world_points(path),result.world_points(path),atol=1e-6,rtol=0)
    assert consume([result])['maximum_consumer_residual_output_units']<1e-6
    record_property('visible_point_instances',len(paths))


def test_complete_W07_native_storm_and_omniverse_fabric(tmp_path,record_property):
    from geobuild.kit import consume as consume_kit
    from PIL import Image
    source=dataset_file('railway','deutschebahn-rails.usda')
    field=dataset_file('scalar-field','gfs_t2m.nc')
    site=os.environ.get('GEO_AECO_SCENE')
    if not site:
        pytest.skip('Private site fixture not supplied')
    railway=SceneResolver(railway_provider(source),experiment=Experiment(placement='per_vertex')).resolve()
    base,overlay,_,_=field_overlay(field)
    field_result=SceneResolver(overlay).resolve()
    site_stage,anchor=aeco_site(Path(site).parent)
    site_resolver=SceneResolver(site_stage)
    initial=site_resolver.resolve()
    anchor.GetAttribute('geo:projectTransform').Set(Gf.Matrix4d().SetTranslate(Gf.Vec3d(100,0,0)))
    moved=site_resolver.resolve()
    frames=[railway,field_result,initial,moved]
    fabric=consume_kit(frames)
    assert fabric['authored_unchanged']
    assert fabric['maximum_consumer_residual_output_units'] < .001
    folder=Path(os.environ.get('GEO_DEMONSTRATIONS',tmp_path))
    folder.mkdir(parents=True,exist_ok=True)
    native=consume([initial,moved],render=folder/'storm-site.png')
    assert native['rendering']['scene_index_direct']
    pixels=np.array(Image.open(folder/'storm-site.png').convert('RGB'))
    assert len(np.unique(pixels.reshape((-1,3)),axis=0))>100
    evidence('consumers',{'kit_version':fabric['kit_version'],
             'kit_extensions':fabric['enabled_extensions'],'native_usd_version':native['usd_version'],
             'native_modules':native['loaded_modules'],'rendering':native['rendering']})
    record_property('kit_version',fabric['kit_version'])
    record_property('kit_fabric_max_residual_m',fabric['maximum_consumer_residual_output_units'])
    record_property('storm_render_pixels',pixels.shape[0]*pixels.shape[1])
    record_property('native_usd_version',native['usd_version'])
    record_property('retired_geospatial_modules_loaded',False)
