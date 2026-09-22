import math
import numpy as np
import pytest
from pxr import Gf,Sdf,Usd,UsdGeom
from pyproj import CRS
from pyproj.crs import CompoundCRS
from geobuild.engine import TransformError
from geobuild.operations import ProjOperations,KarneyOperations
from geobuild.runtime import SceneResolver,SceneError,Experiment,definition,bind,position,declare,export_resolved
from test_scene_runtime import scene,GEO,ECEF,UTM


def test_complete_W06_extent_sweep_and_precision(record_property):
    samples=[]
    for footprint in (.01,10,1000,20000):
        stage,anchor=scene()
        UsdGeom.Cube(stage.GetPrimAtPath('/World/Asset/Detail')).GetSizeAttr().Set(footprint)
        affine=SceneResolver(stage).resolve()
        pointwise=SceneResolver(stage,experiment=Experiment(placement='per_vertex')).resolve()
        delta=np.linalg.norm(affine.world_points('/World/Asset/Detail')-pointwise.world_points('/World/Asset/Detail'),axis=1).max()
        assert math.isfinite(delta)
        samples.append((footprint,float(delta)))
    assert samples[-1][1] > 39 and samples[0][1] < 1e-6
    record_property('footprint_vs_vertex_displacement_m',str(samples))
    # Cartesian anchor alternative gives a defined frame even at the pole.
    stage,anchor=scene((0,90,0))
    with pytest.raises(SceneError,match='pole'):
        SceneResolver(stage).resolve()
    definition(stage,'/CRS/Ecef',ECEF)
    bind(anchor,'/CRS/Ecef')
    position(anchor,ProjOperations().convert(GEO,ECEF,[(0,90,0)]).coordinates[0])
    result=SceneResolver(stage).resolve()
    assert abs(math.dist(*result.world_points('/World/Asset/Detail')[:2])-.01)<1e-6


def test_complete_W08_empty_binding_project_boundary_and_scope(record_property):
    stage,anchor=scene()
    bind(stage.GetPrimAtPath('/World'),'/CRS/Native')
    anchor.GetRelationship('crs:binding').SetTargets([])
    with pytest.raises(SceneError,match='one definition'):
        SceneResolver(stage).resolve()
    inherited=SceneResolver(stage,experiment=Experiment(empty_binding='inherit')).resolve()
    bind(anchor,'/CRS/Native')
    UsdGeom.Xformable(stage.GetPrimAtPath('/World')).AddTranslateOp().Set((1000,0,0))
    absolute=SceneResolver(stage).resolve()
    contrary=SceneResolver(stage,experiment=Experiment(project_placement='ancestor_after_position')).resolve()
    delta=math.dist(absolute.world_position(anchor.GetPath()),contrary.world_position(anchor.GetPath()))
    assert delta==1000
    assert inherited.world_position(anchor.GetPath())==absolute.world_position(anchor.GetPath())
    record_property('ancestor_after_absolute_violation_m',delta)
    bind(stage.GetPrimAtPath('/World/Asset/Detail'),'/CRS/Native')
    with pytest.raises(SceneError,match='offset chain'):
        SceneResolver(stage).resolve()


def test_complete_W08_dynamic_epoch_and_missing_resources(record_property):
    engine=ProjOperations()
    itrf2014=CRS.from_epsg(7912).to_wkt()
    itrf2008=CRS.from_epsg(7911).to_wkt()
    with pytest.raises(TransformError,match='epoch'):
        engine.convert(itrf2014,itrf2008,[(10,53,50)])
    a=engine.convert(itrf2014,itrf2008,[(10,53,50)],epoch=2000)
    b=engine.convert(itrf2014,itrf2008,[(10,53,50)],epoch=2025)
    assert a.coordinates!=b.coordinates
    assert a.provenance['coordinate_epoch']==2000
    record_property('dynamic_operation',a.provenance['operation'])
    with pytest.raises(TransformError,match='static datum'):
        KarneyOperations().convert(itrf2014,itrf2008,[(10,53,50)],epoch=2000)
    # Locally unavailable Canadian vertical grid; the batch must not return a
    # horizontal-only substitute. No download or guessed zero correction.
    with pytest.raises(TransformError,match='missing resources'):
        source=CompoundCRS('NAD83 with CGVD2013',[CRS.from_epsg(4269),CRS.from_epsg(6647)])
        engine.convert(source.to_wkt(),CRS.from_epsg(4979).to_wkt(),[(-75,45,10)])


def test_complete_W08_forwarding_and_time_export(tmp_path,record_property):
    stage,anchor=scene()
    forward=stage.GetPrimAtPath('/World').CreateRelationship('candidate:forward')
    forward.SetTargets(['/CRS/Native'])
    anchor.GetRelationship('crs:binding').SetTargets([forward.GetPath()])
    resolver=SceneResolver(stage)
    position(anchor,(0,0,0),Usd.TimeCode(0))
    position(anchor,(2,0,0),Usd.TimeCode(2))
    samples=[resolver.resolve(t) for t in (0,1,2)]
    result=export_resolved(samples,tmp_path/'time.usda')
    baked=SceneResolver(result)
    for time,expected in enumerate(samples):
        np.testing.assert_allclose(baked.resolve(time).world_points('/World/Asset/Detail'),
                                   expected.world_points('/World/Asset/Detail'),atol=1e-8,rtol=0)
    assert list(result.GetRootLayer().customLayerData['geospatialBuildResolved']['times'])==[0,1,2]
    before=[l.ExportToString() for l in stage.GetLayerStack()]
    report=resolver.coordinates('/World/Asset',UTM,time=1)
    assert all(math.isfinite(v) for v in report.coordinates[0])
    assert before==[l.ExportToString() for l in stage.GetLayerStack()]
    record_property('exported_native_evaluation_samples',3)
