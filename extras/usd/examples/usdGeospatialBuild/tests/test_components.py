import math
import os
from pathlib import Path

import pytest
from pxr import Gf, Sdf, Usd, UsdGeom
from pyproj import CRS

from geobuild.bindings import BindingError, read_binding
from geobuild.engine import ProjEngine, TransformError


def definition(stage, path, value):
    prim = stage.DefinePrim(path, "GeospatialCRS")
    prim.CreateAttribute("crs:wkt", Sdf.ValueTypeNames.String).Set(value)


def bind(stage, path, target):
    stage.GetPrimAtPath(path).CreateRelationship("crs:binding").SetTargets([target])


def sample_stage():
    stage = Usd.Stage.CreateInMemory()
    stage.DefinePrim("/Asset", "Xform")
    stage.DefinePrim("/Asset/Child", "Xform")
    definition(stage, "/Asset/CRS", "opaque definition A")
    bind(stage, "/Asset", "/Asset/CRS")
    return stage


def test_binding_composed_reference_flatten_and_sublayer():
    source = sample_stage()
    reference = Usd.Stage.CreateInMemory()
    reference.DefinePrim("/Placed").GetReferences().AddReference(source.GetRootLayer().identifier, "/Asset")
    flat = Usd.Stage.Open(reference.Flatten())
    layered = Usd.Stage.CreateInMemory()
    layered.GetRootLayer().subLayerPaths = [reference.GetRootLayer().identifier]
    results = [read_binding(s, "/Placed/Child") for s in (reference, flat, layered)]
    assert results[0] == results[1] == results[2]
    assert results[0].definition == "/Placed/CRS"
    assert results[0].wkt == "opaque definition A"  # USD need not parse WKT.


def test_binding_nested_override_and_no_mutation():
    stage = sample_stage()
    definition(stage, "/Asset/OtherCRS", "opaque definition B")
    stage.DefinePrim("/Asset/Child/Leaf", "Xform")
    bind(stage, "/Asset/Child", "/Asset/OtherCRS")
    before = {s.identifier: s.ExportToString() for s in stage.GetUsedLayers()}
    assert read_binding(stage, "/Asset").wkt == "opaque definition A"
    assert read_binding(stage, "/Asset/Child/Leaf").wkt == "opaque definition B"
    assert before == {s.identifier: s.ExportToString() for s in stage.GetUsedLayers()}


def test_binding_stronger_opinion_and_forwarding():
    source = sample_stage()
    stage = Usd.Stage.CreateInMemory()
    stage.GetRootLayer().subLayerPaths = [source.GetRootLayer().identifier]
    definition(stage, "/Other", "strong definition")
    relay = stage.DefinePrim("/Relay").CreateRelationship("target")
    relay.SetTargets(["/Other"])
    bind(stage, "/Asset", "/Relay.target")
    assert read_binding(stage, "/Asset/Child").definition == "/Other"


@pytest.mark.parametrize("targets", [[], ["/Missing"], ["/Asset/CRS", "/Asset/Child"], ["/Asset/Child"]])
def test_binding_invalid_nearer_binding_never_falls_back(targets):
    stage = sample_stage()
    stage.GetPrimAtPath("/Asset/Child").CreateRelationship("crs:binding").SetTargets(targets)
    with pytest.raises(BindingError):
        read_binding(stage, "/Asset/Child")


def test_additive_metadata_leaves_stock_transform_unchanged():
    stage = Usd.Stage.CreateInMemory()
    root = UsdGeom.Xform.Define(stage, "/Root")
    root.AddTranslateOp().Set(Gf.Vec3d(100, 200, 3))
    child = UsdGeom.Xform.Define(stage, "/Root/Child")
    child.AddTranslateOp().Set(Gf.Vec3d(1, 2, 3))
    before = UsdGeom.XformCache().GetLocalToWorldTransform(child.GetPrim())
    definition(stage, "/CRS", "opaque definition")
    bind(stage, "/Root", "/CRS")
    after = UsdGeom.XformCache().GetLocalToWorldTransform(child.GetPrim())
    assert before == after
    assert tuple(after.ExtractTranslation()) == (101, 202, 6)


# Expected results use ellipsoid equations, not this adapter or a second PROJ path.
# Constants are WGS 84 defining parameters. 1 micrometre is a harness numerical
# check at ~6.4e6 metres, not an endorsed survey/placement accuracy requirement.
A = 6378137.0
INV_F = 298.257223563


def analytic_ecef(lon, lat, height):
    longitude, latitude = math.radians(lon), math.radians(lat)
    f = 1 / INV_F
    e2 = f * (2 - f)
    n = A / math.sqrt(1 - e2 * math.sin(latitude) ** 2)
    return ((n + height) * math.cos(latitude) * math.cos(longitude),
            (n + height) * math.cos(latitude) * math.sin(longitude),
            (n * (1 - e2) + height) * math.sin(latitude))


@pytest.fixture
def crss():
    # Registry used to prepare full WKT inputs only, never as a replacement for
    # a definition in the scene or expected numerical output.
    return CRS.from_epsg(4979).to_wkt(), CRS.from_epsg(4978).to_wkt()


def test_engine_analytic_global_points_and_provenance(crss, record_property):
    points = ((0, 0, 0), (90, 0, 10), (12, 45, 100), (151, -34, 20), (-70, 80, 5))
    result = ProjEngine().convert(*crss, points)
    residuals = [math.dist(actual, analytic_ecef(*p)) for actual, p in zip(result.coordinates, points)]
    assert max(residuals) <= 1e-6
    assert result.provenance["pipeline"]
    assert result.provenance["operation"]
    # This pinned PROJ build reports no accuracy estimate for this conversion.
    # Preserve unknown rather than manufacture a zero-accuracy claim.
    assert result.provenance["accuracy_metres"] is None
    assert result.provenance["network"] is False
    record_property("max_residual_m", max(residuals))
    record_property("max_coordinate_magnitude_m", max(math.dist(p, (0, 0, 0)) for p in result.coordinates))
    record_property("operation", result.provenance["operation"])
    record_property("engine_accuracy_m", "unknown")


def test_engine_analytic_geographic_reporting(crss):
    expected = ((0, 0, 0), (12, 45, 100), (151, -34, 20))
    input_points = tuple(analytic_ecef(*p) for p in expected)
    result = ProjEngine().convert(crss[1], crss[0], input_points)
    # Express disagreement as a metre distance rather than a count of angular digits.
    for actual, reference in zip(result.coordinates, input_points):
        assert math.dist(analytic_ecef(*actual), reference) <= 1e-6


@pytest.mark.parametrize("bad", [(0, 91, 0), (181, 0, 0), (0, 0, float("nan")), (1, 2), (float("inf"), 0, 0)])
def test_engine_reject_invalid_batch(crss, bad):
    with pytest.raises(TransformError):
        ProjEngine().convert(*crss, [(0, 0, 0), bad])


def test_engine_reject_codes_unsupported_and_empty(crss):
    engine = ProjEngine()
    for source, target, points in [
        ("EPSG:4979", crss[1], [(0, 0, 0)]),
        (crss[0], CRS.from_epsg(3857).to_wkt(), [(0, 0, 0)]),
        (*crss, []),
        (crss[1], crss[0], [(0, 0, 0)]),
    ]:
        with pytest.raises(TransformError):
            engine.convert(source, target, points)


def test_engine_reject_unavailable_best_operation(crss, monkeypatch):
    import pyproj.transformer
    from types import SimpleNamespace
    monkeypatch.setattr(pyproj.transformer, "TransformerGroup",
                        lambda *a, **kw: SimpleNamespace(best_available=False, transformers=[]))
    with pytest.raises(TransformError, match="Best operation unavailable"):
        ProjEngine().convert(*crss, [(0, 0, 0)])


def test_engine_reject_partial_result(crss, monkeypatch):
    import pyproj.transformer
    from types import SimpleNamespace
    bad_operation = SimpleNamespace(transform=lambda *a, **kw: ([A, math.inf], [0, 0], [0, 0]))
    monkeypatch.setattr(pyproj.transformer, "TransformerGroup",
                        lambda *a, **kw: SimpleNamespace(best_available=True, transformers=[bad_operation]))
    with pytest.raises(TransformError, match="incomplete or non-finite"):
        ProjEngine().convert(*crss, [(0, 0, 0), (1, 0, 0)])


def test_native_sample_midpoint_before_conversion(crss, record_property):
    # Conditional example from requirement 20, NOT a geographic scene carrier.
    engine = ProjEngine()
    midpoint = engine.convert(*crss, [(0, 0, 0)]).coordinates[0]
    endpoints = engine.convert(*crss, [(-1, 0, 0), (1, 0, 0)]).coordinates
    chord = tuple((a + b) / 2 for a, b in zip(*endpoints))
    depth = math.dist(midpoint, chord)
    assert math.dist(midpoint, (A, 0, 0)) <= 1e-6
    assert abs(depth - A * (1 - math.cos(math.radians(1)))) <= 1e-6
    assert 970 < depth < 972
    record_property("wrong_order_chord_depth_m", depth)


def aeco_stage():
    path = os.environ.get("GEO_AECO_SCENE")
    if not path:
        pytest.skip("Partner attachment not supplied; no practitioner fixture evidence.")
    return Usd.Stage.Open(path)


def test_aeco_partner_stated_origin_and_conformance(record_property):
    stage = aeco_stage()
    before = {s.identifier: s.ExportToString() for s in stage.GetUsedLayers()}
    placement = stage.GetPrimAtPath("/Site/EiffelTower")
    cache = UsdGeom.XformCache()
    origin = cache.GetLocalToWorldTransform(placement).ExtractTranslation()
    expected = (648237.125, 6862251.890, 33.790)  # Partner README, not calculated by resolver.
    residual = math.dist(origin, expected)
    assert residual < 1e-6
    geom = stage.GetPrimAtPath("/Site/EiffelTower/Geom")
    up = cache.GetLocalToWorldTransform(geom).TransformDir(Gf.Vec3d(0, 1, 0))
    assert math.dist(up, (0, 0, 1)) < 1e-12
    bbox = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_]).ComputeWorldBound(geom).ComputeAlignedRange()
    assert 299 < bbox.GetSize()[2] < 301  # Partner says approximately 300 metres.
    assert before == {s.identifier: s.ExportToString() for s in stage.GetUsedLayers()}
    record_property("origin_residual_m", residual)
    record_property("height_m", bbox.GetSize()[2])


def test_aeco_wkt_library_and_calibration_origin(record_property):
    stage = aeco_stage()
    path = Path(os.environ["GEO_AECO_SCENE"]).with_name("crs_library.usda")
    library = Usd.Stage.Open(str(path))
    definitions = {}
    for name in ("LocalSiteGrid", "Lambert93_IGN69", "Topocentric_WGS84"):
        wkt = library.GetPrimAtPath("/CRS/" + name).GetAttribute("crs:wkt").Get()
        definitions[name] = CRS.from_wkt(wkt)
        assert len(definitions[name].axis_info) == 3
    # This probes the partner fixture with stock PROJ, not the new runtime.
    from pyproj import Transformer
    transform = Transformer.from_crs(definitions["LocalSiteGrid"], definitions["Lambert93_IGN69"],
                                     always_xy=True, allow_ballpark=False, only_best=True)
    result = transform.transform(1000, 1000, 33, errcheck=True)
    residual = math.dist(result[:2], (648200, 6862200))
    assert residual < .001  # Partner's stated sub-millimetre origin check.
    record_property("calibration_origin_residual_m", residual)
