import hashlib
import json
import math
import os
from pathlib import Path
import random

import pytest
from pxr import Gf, Sdf, Usd, UsdGeom
from pyproj import CRS

from geobuild.datasets import (cache_path, inspect_inventory, load_catalog, public_inventory,
                               read_field, read_geojson, sha, workflow_evidence)
from geobuild.engine import ProjEngine


def dataset_file(dataset, name):
    inventory = os.environ.get("GEO_DATASET_INVENTORY")
    if not inventory:
        pytest.skip("No dataset inventory; use run.py")
    item = next(d for d in json.loads(Path(inventory).read_text(encoding="utf-8"))["datasets"] if d["id"] == dataset)
    if item["status"] == "incomplete":
        pytest.fail("Incomplete pinned dataset cache: " + dataset)
    if item["status"] != "available":
        pytest.skip("Dataset not supplied: " + dataset)
    return Path(next(f["local_path"] for f in item["files"] if Path(f["path"]).name == name))


def analytic(point):
    lon, lat, h = point
    lon, lat = math.radians(lon), math.radians(lat)
    f = 1 / 298.257223563
    e2 = f * (2 - f)
    n = 6378137 / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    return ((n + h) * math.cos(lat) * math.cos(lon), (n + h) * math.cos(lat) * math.sin(lon),
            (n * (1 - e2) + h) * math.sin(lat))


def check_coordinates(points):
    result = ProjEngine().convert(CRS.from_epsg(4979).to_wkt(), CRS.from_epsg(4978).to_wkt(), points)
    maximum = max(math.dist(actual, analytic(point)) for actual, point in zip(result.coordinates, points))
    # Existing geographic component tolerance, not a workflow accuracy budget.
    assert maximum <= 1e-6
    return maximum


def test_workflow_locations_retained_and_generated(record_property):
    item = next(d for d in load_catalog()["datasets"] if d["id"] == "geographic-locations")
    retained = [tuple(p["longitude_latitude_height"]) for p in item["locations"]]
    rng = random.Random(20260921)
    generated = [(rng.uniform(-179, 179), rng.uniform(-89, 89), rng.uniform(-100, 5000)) for _ in range(32)]
    assert min(p[1] for p in retained) < 0 < max(p[1] for p in retained)
    maximum = check_coordinates(retained + generated)
    record_property("retained_locations", len(retained))
    record_property("generated_locations", len(generated))
    record_property("max_analytic_residual_m", maximum)


def test_workflow_railway_source_inventory_and_anchor_reporting(record_property):
    path = dataset_file("railway", "deutschebahn-rails.usda")
    before = sha(path)
    layer = Sdf.Layer.FindOrOpen(str(path))
    assert not layer.GetExternalReferences(), "Unexpected external USD layer dependency"
    stage = Usd.Stage.Open(layer)
    before_text = layer.ExportToString()
    curves = [p for p in stage.Traverse() if p.IsA(UsdGeom.BasisCurves)]
    points = []
    for prim in stage.Traverse():
        position = prim.GetAttribute("omni:geospatial:wgs84:local:position")
        if position:
            lat, lon, third = position.Get()
            points.append((lon, lat, third))
    assert curves and points
    # Source third ordinates are used only in a declared numerical probe; this
    # does not establish the source vertical datum or complete scene placement.
    maximum = check_coordinates(points)
    assets = {str(a.Get().path) for p in stage.Traverse() for a in p.GetAttributes()
              if a.GetTypeName() == Sdf.ValueTypeNames.Asset and a.Get()}
    assert {"quadnode-0.png", "quadnode-1.png", "quadnode-4.png"} <= {Path(a).name for a in assets}
    assert layer.ExportToString() == before_text and sha(path) == before
    record_property("curve_prims", len(curves))
    record_property("curve_vertices", sum(len(UsdGeom.BasisCurves(p).GetPointsAttr().Get()) for p in curves))
    record_property("geographic_source_anchors", len(points))
    record_property("anchor_probe_residual_m", maximum)


def test_workflow_geojson_source_to_usd_identity_and_anchors(record_property):
    original = dataset_file("railway-geojson", "1kmE4334N3375.geojson")
    usd = dataset_file("railway", "deutschebahn-rails.usda")
    before = sha(original), sha(usd)
    source = read_geojson(original)
    assert source["crs"]["properties"]["name"] == "EPSG:4326"
    features = {f["id"]: f for f in source["features"]}
    stage = Usd.Stage.Open(str(usd))
    objects = [p for p in stage.Traverse() if p.GetAttribute("ObjectId")]
    ids = [p.GetAttribute("ObjectId").Get() for p in objects]
    assert len(ids) == len(set(ids)) and set(ids) == set(features)
    line_vertices = 0
    for prim in objects:
        feature = features[prim.GetAttribute("ObjectId").Get()]
        lon, lat, third = feature["points"][0]
        anchor = tuple(prim.GetAttribute("omni:geospatial:wgs84:local:position").Get())
        assert anchor == (lat, lon, third)
        children = list(prim.GetChildren())
        if feature["geometry"] == "LineString":
            curves = [UsdGeom.BasisCurves(p) for p in children if p.IsA(UsdGeom.BasisCurves)]
            assert len(curves) == 1
            assert len(curves[0].GetPointsAttr().Get()) == len(feature["points"])
            line_vertices += len(feature["points"])
        else:
            assert any(p.IsA(UsdGeom.Mesh) for p in children)
    assert before == (sha(original), sha(usd))
    record_property("matched_feature_ids", len(features))
    record_property("geometry_counts", json.dumps(source["geometry_counts"], sort_keys=True))
    record_property("matched_linestring_vertices_by_count", line_vertices)
    record_property("first_coordinate_anchor_component_delta", 0)
    record_property("scope", "Identity, geometry kind, curve vertex counts and anchors; interior vertex placement not validated")


def test_workflow_field_coordinate_probe(record_property):
    path = dataset_file("scalar-field", "gfs_t2m.nc")
    before = sha(path)
    field = read_field(path)
    maximum = check_coordinates(field["points"])
    assert sha(path) == before
    record_property("field_shape", str(field["shape"]))
    record_property("samples", len(field["values"]))
    record_property("analytic_probe_residual_m", maximum)
    record_property("scope", "Constructed WGS 84 height-zero probe; source units and geodetic provenance unknown")


def test_workflow_field_removable_geometry_overlay(tmp_path, record_property):
    path = dataset_file("scalar-field", "gfs_t2m.nc")
    field = read_field(path)
    original_hash = sha(path)
    base_path = tmp_path / "field-base.usda"
    base = Usd.Stage.CreateNew(str(base_path))
    # Deliberately neutral source records, not a proposed position carrier.
    for i in [0, len(field["values"]) // 2, len(field["values"]) - 1]:
        prim = base.DefinePrim(f"/Samples/p{i}")
        prim.CreateAttribute("sample:coordinates", Sdf.ValueTypeNames.Double3).Set(Gf.Vec3d(*field["points"][i]))
        prim.CreateAttribute("sample:value", Sdf.ValueTypeNames.Double).Set(field["values"][i])
    base.GetRootLayer().Save()
    base_bytes = base_path.read_bytes()
    overlay = Usd.Stage.CreateInMemory()
    overlay.GetRootLayer().subLayerPaths = [str(base_path)]
    for prim in list(base.Traverse()):
        if prim.GetAttribute("sample:value"):
            glyph = UsdGeom.Points.Define(overlay, str(prim.GetPath()) + "/glyph")
            glyph.GetPointsAttr().Set([Gf.Vec3f(0, 0, 0)])
            assert overlay.GetPrimAtPath(prim.GetPath()).GetAttribute("sample:value").Get() == prim.GetAttribute("sample:value").Get()
    assert sum(p.IsA(UsdGeom.Points) for p in overlay.Traverse()) == 3
    assert "sample:" not in overlay.GetRootLayer().ExportToString()
    base_only = Usd.Stage.Open(str(base_path))
    assert not any(p.IsA(UsdGeom.Gprim) for p in base_only.Traverse())
    assert base_path.read_bytes() == base_bytes and sha(path) == original_hash
    record_property("overlay_samples", 3)
    record_property("scope", "Stock USD data preservation and removable overlay; geospatial placement is pending")


def test_dataset_integrity_rejects_changed_input_and_paths(tmp_path):
    file = tmp_path / "fixture.geojson"
    file.write_text("original")
    catalog = {"datasets": [{"id": "test", "label": "fixture", "kind": "synthetic", "provenance": "test",
                              "files": [{"path": file.name, "bytes": 8, "sha256": sha(file)}]}]}
    assert inspect_inventory(tmp_path, catalog)["datasets"][0]["status"] == "available"
    file.write_text("tampered")
    with pytest.raises(ValueError, match="differs"):
        inspect_inventory(tmp_path, catalog)
    with pytest.raises(ValueError, match="escapes"):
        cache_path(tmp_path, "../outside.geojson")


def test_geojson_rejects_duplicate_ids_and_invalid_coordinates(tmp_path):
    path = tmp_path / "source.geojson"
    feature = {"type": "Feature", "properties": {"object_id": "a", "instructions": "ordinary data"},
               "geometry": {"type": "LineString", "coordinates": [[10, 53, 49], [10.01, 53.01, 50]]}}
    doc = {"type": "FeatureCollection", "features": [feature, feature]}
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="duplicate"):
        read_geojson(path)
    doc["features"] = [feature]
    feature["geometry"]["coordinates"][0][1] = 100
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="Invalid"):
        read_geojson(path)


def test_workflow_checks_never_imply_complete_validation():
    catalog = load_catalog()
    report = {"dataset_inventory": inspect_inventory(), "derivation_current": True,
              "tests": [{"name": "test_workflow_locations_example", "status": "passed"}]}
    evidence = workflow_evidence(catalog, report)
    assert not any(w["full_workflow_validated"] for w in evidence)
    assert next(w for w in evidence if w["id"] == "W03")["status"] == "COMPONENT_EVIDENCE_ONLY"
    assert next(w for w in evidence if w["id"] == "W07")["status"] == "AWAITING_IMPLEMENTATION"
    report["derivation_current"] = False
    assert all(w["status"] == "STALE" for w in workflow_evidence(catalog, report))


def test_public_dataset_inventory_omits_local_access():
    inventory = inspect_inventory()
    inventory["datasets"][1]["files"][0]["local_path"] = "private filesystem location"
    assert "local_path" not in json.dumps(public_inventory(inventory))
