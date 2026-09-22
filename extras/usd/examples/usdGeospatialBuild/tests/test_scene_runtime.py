import json
import math
import numpy as np
import pytest
from pxr import Gf, Sdf, Usd, UsdGeom
from pyproj import CRS
from geobuild.operations import ProjOperations, KarneyOperations
from geobuild.engine import TransformError
from geobuild.runtime import (SceneResolver, SceneError, Experiment, definition, bind,
                              position, declare, dependency, export_resolved)

GEO = CRS.from_epsg(4979).to_wkt()
ECEF = CRS.from_epsg(4978).to_wkt()
UTM = CRS.from_epsg(32632).to_3d().to_wkt()


def scene(point=(10,53,50), carrier="attribute", up="Z", metres=1):
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageMetersPerUnit(stage, metres)
    UsdGeom.SetStageUpAxis(stage, up)
    root = UsdGeom.Xform.Define(stage, "/World").GetPrim()
    stage.SetDefaultPrim(root)
    definition(stage, "/CRS/Native", GEO)
    anchor = UsdGeom.Xform.Define(stage, "/World/Asset").GetPrim()
    bind(anchor, "/CRS/Native")
    position(anchor, point, carrier=carrier)
    UsdGeom.Cube.Define(stage, "/World/Asset/Detail").GetSizeAttr().Set(.01)
    declare(stage, ECEF)
    return stage, anchor


def test_scene_independent_engine_and_epoch(record_property, monkeypatch):
    proj, independent = ProjOperations(), KarneyOperations()
    points = [(-73.985656,40.748817,0),(151.214,-33.857,58),(174.7762,-41.2865,5),
              (-78.4678,-.1807,2850),(15.65,78.22,10)]
    maximum = 0
    for point, code in zip(points, (32618,32756,32760,32717,32633)):
        target = CRS.from_epsg(code).to_3d().to_wkt()
        for output in (ECEF, target):
            a = proj.convert(GEO, output, [point]).coordinates[0]
            b = independent.convert(GEO, output, [point]).coordinates[0]
            maximum = max(maximum, math.dist(a,b))
            assert math.dist(a,b) < 1e-6
            assert math.dist(independent.convert(output,GEO,[b]).coordinates[0], point) < 1e-7
            assert math.dist(proj.convert(output,GEO,[a]).coordinates[0], point) < 1e-7
    monkeypatch.setattr(ProjOperations, "_operation", lambda *args: pytest.fail("Independent engine used PROJ arithmetic"))
    assert independent.convert(GEO,ECEF,points).provenance["coordinate_math_uses_proj"] is False
    with pytest.raises(TransformError, match="epoch"):
        proj.convert(CRS.from_epsg(7912).to_wkt(), ECEF, [points[0]])
    record_property("independent_max_residual_m", maximum)


@pytest.mark.parametrize("carrier", ["attribute", "translate"])
def test_scene_absolute_offsets_invalidation_export(tmp_path, carrier, record_property):
    stage, anchor = scene(carrier=carrier)
    resolver = SceneResolver(stage, experiment=Experiment(carrier=carrier))
    before = stage.GetRootLayer().ExportToString()
    result = resolver.resolve()
    expected = ProjOperations().convert(GEO,ECEF,[(10,53,50)]).coordinates[0]
    assert math.dist(result.world_position(anchor.GetPath()), expected) < 1e-8
    assert result is resolver.resolve()
    assert stage.GetRootLayer().ExportToString() == before
    UsdGeom.Xformable(stage.GetPrimAtPath('/World')).AddTranslateOp().Set((999,777,111))
    changed = resolver.resolve()
    assert changed.revision > result.revision
    np.testing.assert_allclose(changed.world_points('/World/Asset/Detail'), result.world_points('/World/Asset/Detail'), atol=1e-8, rtol=0)
    detail = UsdGeom.Xformable(stage.GetPrimAtPath('/World/Asset/Detail'))
    detail.AddTranslateOp().Set((10,0,0))
    moved = resolver.resolve()
    assert 9.99 < math.dist(moved.world_position('/World/Asset/Detail'),result.world_position('/World/Asset/Detail')) < 10.01
    baked = export_resolved([moved], tmp_path/'baked.usda')
    again = SceneResolver(baked).resolve()
    np.testing.assert_allclose(again.world_points('/World/Asset/Detail'), moved.world_points('/World/Asset/Detail'), atol=1e-8,rtol=0)
    assert all(p['already_resolved'] for p in again.prims.values())
    record_property("source_unchanged_during_resolution", True)


def test_scene_native_interpolation_dependency_and_policy_alternatives(record_property):
    stage, anchor = scene()
    position(anchor, (0,0,0), Usd.TimeCode(0))
    position(anchor, (2,0,0), Usd.TimeCode(2))
    resolver = SceneResolver(stage)
    a,b,c = (resolver.resolve(t) for t in (0,1,2))
    midpoint = np.array(b.world_position(anchor.GetPath()))
    chord = (np.array(a.world_position(anchor.GetPath())) + c.world_position(anchor.GetPath())) / 2
    residual = float(np.linalg.norm(midpoint-chord))
    assert residual > 970
    record_property('interpolate_after_transform_error_m',residual)
    declare(stage,ECEF,mode='default_prim')
    other = SceneResolver(stage,experiment=Experiment(dependency='default_prim')).resolve(1)
    np.testing.assert_allclose(other.world_position(anchor.GetPath()), midpoint)
    assert dependency(stage)['required']
    with pytest.raises(SceneError,match='conflicts'):
        SceneResolver(stage,experiment=Experiment(target='scene_locked')).resolve(1,UTM)
    with pytest.raises(SceneError,match='Geographic'):
        resolver.resolve(1,GEO)
    geographic = SceneResolver(stage,experiment=Experiment(geographic_output='per_vertex')).resolve(1,GEO)
    with pytest.raises(SceneError,match='Euclidean'):
        geographic.relative_placement('/World/Asset','/World/Asset/Detail')


def test_scene_precision_extent_and_native_hydra(record_property):
    from geobuild.hydra import consume
    frames=[]
    for location in ((10,53,50),(-78,-.1,3000),(151,-34,50)):
        stage, anchor = scene(location)
        frame = SceneResolver(stage).resolve()
        frames.append(frame)
        points=frame.world_points('/World/Asset/Detail')
        assert abs(math.dist(points[0],points[1])-.01) < 1e-6
    result=consume(frames)
    assert result['native_scene_index']
    assert result['maximum_consumer_residual_output_units'] < 1e-6
    assert result['frames'][1]['dirtied']
    record_property('hydra_nonhydra_max_residual_m', result['maximum_consumer_residual_output_units'])
    stage, anchor=scene()
    UsdGeom.Cube(stage.GetPrimAtPath('/World/Asset/Detail')).GetSizeAttr().Set(20000)
    affine=SceneResolver(stage).resolve()
    error=affine.prims['/World/Asset/Detail']['affine_vertex_error_metres']
    assert error > 10
    anchor.CreateAttribute('geo:maxErrorMetres',Sdf.ValueTypeNames.Double).Set(.01)
    with pytest.raises(SceneError,match='budget'):
        SceneResolver(stage).resolve()
    pointwise=SceneResolver(stage,experiment=Experiment(placement='per_vertex')).resolve()
    assert pointwise.prims['/World/Asset/Detail']['affine_vertex_error_metres'] > 10
    record_property('twenty_km_affine_vertex_error_m',error)


def test_scene_failures_are_atomic_and_unaware_stage_survives():
    stage,anchor=scene()
    second=UsdGeom.Xform.Define(stage,'/World/Bad').GetPrim()
    position(second,(1,91,0))
    bind(second,'/Missing')
    with pytest.raises(SceneError,match='no CRS'):
        SceneResolver(stage).resolve()
    bind(second,'/CRS/Native')
    with pytest.raises(TransformError,match='domain'):
        SceneResolver(stage).resolve()
    assert UsdGeom.XformCache().GetLocalToWorldTransform(anchor)==Gf.Matrix4d(1)
    stage.RemovePrim('/World/Bad')
    stage.GetRootLayer().customLayerData={}
    with pytest.raises(SceneError,match='dependency'):
        SceneResolver(stage).resolve(target_wkt=ECEF)
