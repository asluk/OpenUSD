#
# Copyright 2026 NVIDIA CORPORATION & AFFILIATES
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#
"""NEW fixtures derived from authority, not prior generated scenes or tests."""

import sys, json, csv, hashlib, xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from pxr import Usd, UsdGeom, Sdf, Gf, Vt
from pyproj import CRS

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src_py"))
from crs import Engine, geocentric, normalize_wkt
from common import ROOT
from profiles import publish_claim

AUTHORED = ROOT / "inputs/authored"
ORIGINAL = ROOT / "inputs/original"


def attr(p, n, t, v, uniform=False):
    a = p.CreateAttribute(
        n,
        t,
        custom=False,
        variability=Sdf.VariabilityUniform if uniform else Sdf.VariabilityVarying,
    )
    if v is not None:
        a.Set(v)
    return a


def bind(p, wkt, position=(0, 0, 0), orientation=None):
    p.SetMetadata(
        "apiSchemas", Sdf.TokenListOp.CreateExplicit(["GeospatialCRSBindingAPI"])
    )
    # A full definition is authored once in a library, not copied onto each use.
    text = normalize_wkt(wkt)
    identifier = "CRS_" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    file = AUTHORED / "crs-library.usda"
    library = (
        Usd.Stage.Open(str(file)) if file.exists() else Usd.Stage.CreateNew(str(file))
    )
    definition = library.DefinePrim("/" + identifier, "CoordinateReferenceSystem")
    if not definition.GetAttribute("crs:wkt").HasAuthoredValueOpinion():
        attr(definition, "crs:wkt", Sdf.ValueTypeNames.Token, text, True)
    library.GetRootLayer().Save()
    p.GetReferences().AddReference("crs-library.usda", "/" + identifier)
    if position is not None:
        attr(p, "crs:position", Sdf.ValueTypeNames.Double3, Gf.Vec3d(*position))
    if orientation is not None:
        attr(p, "crs:orientation", Sdf.ValueTypeNames.Double3, Gf.Vec3d(*orientation))
    return p


def stage(name):
    s = Usd.Stage.CreateNew(str(AUTHORED / name))
    UsdGeom.SetStageUpAxis(s, "Z")
    UsdGeom.SetStageMetersPerUnit(s, 1)
    w = UsdGeom.Xform.Define(s, "/World").GetPrim()
    s.SetDefaultPrim(w)
    return s, w


def mesh(s, path, points=None):
    m = UsdGeom.Mesh.Define(s, path)
    m.CreatePointsAttr(
        Vt.Vec3fArray(
            points if points is not None else [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
        )
    )
    m.CreateFaceVertexCountsAttr([3])
    m.CreateFaceVertexIndicesAttr([0, 1, 2])
    m.CreateSubdivisionSchemeAttr("none")
    m.CreateDisplayColorAttr([(0.18, 0.48, 0.63)])
    return m


def carrier(s, path, wkt, file, fmt, field, domain):
    p = s.DefinePrim(path, "GeospatialDataSource")
    bind(p, wkt, None)
    attr(p, "data:asset", Sdf.ValueTypeNames.Asset, Sdf.AssetPath(file), True)
    attr(p, "data:format", Sdf.ValueTypeNames.Token, fmt, True)
    attr(p, "data:field", Sdf.ValueTypeNames.String, field, True)
    attr(p, "data:coordinateDomain", Sdf.ValueTypeNames.String, domain, True)
    return p


def generate():
    AUTHORED.mkdir(exist_ok=True)
    wgs = CRS.from_epsg(4979).to_wkt()
    ecef = CRS.from_epsg(4978).to_wkt()
    utm = CRS.from_epsg(32631).to_3d().to_wkt()
    # Reusable local asset: no geospatial code or generated data in the source.
    a = Usd.Stage.CreateNew(str(AUTHORED / "asset.usda"))
    r = UsdGeom.Xform.Define(a, "/Asset").GetPrim()
    a.SetDefaultPrim(r)
    mesh(a, "/Asset/Detail", [(0, 0, 0), (0.001, 0, 0), (0, 0.001, 0)])
    attr(
        r,
        "review:unrelatedInput",
        Sdf.ValueTypeNames.String,
        "preserve this source fact",
    )
    a.GetRootLayer().Save()
    s, w = stage("models.usda")
    bind(w, utm, (448000, 5410000, 80))
    p = bind(
        UsdGeom.Xform.Define(s, "/World/Model").GetPrim(),
        wgs,
        (2.2945, 48.8584, 70),
        (35, 5, 3),
    )
    UsdGeom.Xformable(p).AddTranslateOp(opSuffix="adjust").Set((30, -20, 5))
    UsdGeom.Xformable(p).AddRotateZOp(opSuffix="adjust").Set(12)
    UsdGeom.Xformable(p).AddScaleOp(opSuffix="adjust").Set((1.1, 0.95, 1.0))
    p.GetReferences().AddReference("asset.usda")
    child = UsdGeom.Xform.Define(s, "/World/Model/Child")
    child.AddTranslateOp().Set((7, 2, 1))
    mesh(s, "/World/Model/Child/Mesh")
    reset = UsdGeom.Xform.Define(s, "/World/Model/Reset")
    reset.AddTranslateOp().Set((4, 0, 0))
    reset.SetResetXformStack(True)
    mesh(s, "/World/Model/Reset/Mesh")
    nested = bind(
        UsdGeom.Xform.Define(s, "/World/Model/Independent").GetPrim(),
        wgs,
        (2.2946, 48.8585, 71),
    )
    mesh(s, "/World/Model/Independent/Mesh")
    # Native instance proxies: expansion must have the same interpretation.
    inst = bind(
        UsdGeom.Xform.Define(s, "/World/NativeInstance").GetPrim(),
        wgs,
        (2.295, 48.858, 70),
        (0, 0, 0),
    )
    inst.GetReferences().AddReference("asset.usda")
    inst.SetInstanceable(True)
    moving = bind(UsdGeom.Xform.Define(s, "/World/Moving").GetPrim(), wgs, (0, 0, 0))
    moving.GetAttribute("crs:position").Clear()
    moving.GetAttribute("crs:position").Set((-1, 0, 0), 0)
    moving.GetAttribute("crs:position").Set((1, 0, 0), 2)
    a = attr(moving, "crs:orientation", Sdf.ValueTypeNames.Double3, None)
    a.Set((350, 0, 0), 0)
    a.Set((10, 0, 0), 2)
    mesh(s, "/World/Moving/Mesh")
    pi = UsdGeom.PointInstancer.Define(s, "/World/Instancer")
    bind(pi.GetPrim(), wgs, (2.2945, 48.8584, 70))
    proto = bind(
        UsdGeom.Xform.Define(s, "/Storage/BoundPrototype").GetPrim(),
        wgs,
        (2.2947, 48.8586, 75),
        (10, 0, 0),
    )
    mesh(s, "/Storage/BoundPrototype/Mesh")
    unbound = UsdGeom.Xform.Define(s, "/Storage/LocalPrototype")
    unbound.AddTranslateOp().Set((0, 5, 0))
    mesh(s, "/Storage/LocalPrototype/Mesh")
    pi.CreatePrototypesRel().SetTargets(
        ["/Storage/BoundPrototype", "/Storage/LocalPrototype"]
    )
    pi.CreateProtoIndicesAttr([0, 0, 1])
    pi.CreatePositionsAttr([(0, 0, 0), (10, 0, 0), (20, 0, 0)])
    pi.CreateIdsAttr([11, 12, 13])
    publish_claim(s)
    s.GetRootLayer().Save()
    # Composition equivalence: layer, inherit, reference, variants, offsets, clips.
    c = Usd.Stage.CreateNew(str(AUTHORED / "class.usda"))
    cl = c.CreateClassPrim("/GeoClass")
    bind(cl, wgs, (2.2945, 48.8584, 70), (35, 5, 3))
    c.GetRootLayer().Save()
    cs, cw = stage("composition.usda")
    cw.GetReferences().AddReference("models.usda")
    cs.GetRootLayer().subLayerPaths.append("class.usda")
    ip = UsdGeom.Xform.Define(cs, "/Inherited").GetPrim()
    ip.GetInherits().AddInherit("/GeoClass")
    mesh(cs, "/Inherited/Mesh")
    off = UsdGeom.Xform.Define(cs, "/Offset").GetPrim()
    off.GetReferences().AddReference(
        "models.usda", "/World/Moving", Sdf.LayerOffset(10, 2)
    )
    # Value clips contain raw angle and position samples, evaluated by Core first.
    clip = Usd.Stage.CreateNew(str(AUTHORED / "clip.usda"))
    cp = clip.DefinePrim("/Clip", "Xform")
    attr(cp, "crs:orientation", Sdf.ValueTypeNames.Double3, None).Set((350, 0, 0), 0)
    cp.GetAttribute("crs:orientation").Set((10, 0, 0), 2)
    clip.GetRootLayer().Save()
    cp = bind(UsdGeom.Xform.Define(cs, "/Clip").GetPrim(), wgs, (2.2945, 48.8584, 70))
    attr(cp, "crs:orientation", Sdf.ValueTypeNames.Double3, None)
    clips = Usd.ClipsAPI(cp)
    clips.SetClipAssetPaths([Sdf.AssetPath("clip.usda")])
    clips.SetClipPrimPath("/Clip")
    clips.SetClipActive([(0, 0)])
    clips.SetClipTimes([(0, 0), (2, 2)])
    mesh(cs, "/Clip/Mesh")
    publish_claim(cs)
    cs.GetRootLayer().Save()
    # Interface summary stays above an unloaded payload.
    ps, pw = stage("publication.usda")
    pw.GetPayloads().AddPayload("models.usda")
    publish_claim(ps)
    ps.GetRootLayer().Save()
    # Original railway retains RFC longitude/latitude/ellipsoidal-height semantics.
    ds, dw = stage("domains.usda")
    bind(dw, utm, (448000, 5410000, 80))
    carrier(
        ds,
        "/World/Railway",
        wgs,
        "../original/railway.geojson",
        "GeoJSON",
        "",
        "geometry",
    )
    # CF example derived explicitly from the original measurement values, not a claim
    # that missing source metadata or height was present in the original download.
    import netCDF4

    original = netCDF4.Dataset(ORIGINAL / "gfs_t2m.nc")
    with netCDF4.Dataset(AUTHORED / "climate.cf.nc", "w") as f:
        f.Conventions = "CF-1.12"
        f.history = "Illustrative derived association: added CF roles, example Kelvin unit, synthetic zero ellipsoidal height, example observation times and second field with +1 K. Original file preserved; these are not recovered source metadata."
        for n, num in [("time", 2), ("lat", 37), ("lon", 72)]:
            f.createDimension(n, num)
        lat = f.createVariable("latitude", "f8", ("lat",))
        lat[:] = original["lat"][:]
        lat.standard_name = "latitude"
        lat.units = "degrees_north"
        lon = f.createVariable("longitude", "f8", ("lon",))
        lon[:] = original["lon"][:]
        lon.standard_name = "longitude"
        lon.units = "degrees_east"
        height = f.createVariable("height", "f8")
        height.assignValue(0)
        height.standard_name = "height_above_reference_ellipsoid"
        height.units = "m"
        height.positive = "up"
        tm = f.createVariable("time", "f8", ("time",))
        tm[:] = [0, 6]
        tm.units = "hours since 2026-10-23 00:00:00"
        tm.standard_name = "time"
        gm = f.createVariable("crs", "i4")
        gm.grid_mapping_name = "latitude_longitude"
        gm.crs_wkt = wgs
        values = f.createVariable(
            "temperature", "f4", ("time", "lon", "lat"), fill_value=-9999
        )
        base = np.ma.filled(original["t2m"][:], np.nan)
        values[:] = np.stack([base.T, base.T + 1])
        values.coordinates = "longitude latitude height time"
        values.grid_mapping = "crs"
        values.units = "K"
    original.close()
    carrier(ds, "/World/Climate", wgs, "climate.cf.nc", "CF", "temperature", "crs")
    # Named-order counterexample: auxiliary arrays use (lat,lon), field (lon,lat).
    with netCDF4.Dataset(AUTHORED / "permuted.cf.nc", "w") as f:
        f.createDimension("y", 2)
        f.createDimension("x", 3)
        for name, role, unit, vals in [
            ("longitude", "longitude", "degrees_east", [[1, 2, 3], [4, 5, 6]]),
            ("latitude", "latitude", "degrees_north", [[40, 40, 40], [41, 41, 41]]),
        ]:
            v = f.createVariable(name, "f8", ("y", "x"))
            v[:] = vals
            v.standard_name = role
            v.units = unit
        h = f.createVariable("height", "f8")
        h.assignValue(10)
        h.standard_name = "height_above_reference_ellipsoid"
        h.units = "m"
        gm = f.createVariable("crs", "i4")
        gm.crs_wkt = wgs
        gm.grid_mapping_name = "latitude_longitude"
        v = f.createVariable("value", "f8", ("x", "y"))
        v[:] = [[10, 40], [20, 50], [30, 60]]
        v.coordinates = "longitude latitude height"
        v.grid_mapping = "crs"
    carrier(ds, "/World/Permuted", wgs, "permuted.cf.nc", "CF", "value", "crs")
    # Deliberate GeoTIFF examples for both raster sample conventions.
    from PIL import Image, TiffImagePlugin

    for kind in (1, 2):
        tags = TiffImagePlugin.ImageFileDirectory_v2()
        tags[33550] = (2.0, 3.0, 0.0)
        tags[33922] = (0.0, 0.0, 0.0, 600000.0, 5400000.0, 0.0)
        tags[34735] = (1, 1, 0, 3, 1024, 0, 1, 1, 1025, 0, 1, kind, 3072, 0, 1, 32631)
        Image.fromarray(np.arange(6, dtype=np.uint16).reshape(2, 3)).save(
            AUTHORED / f"raster-{kind}.tif", tiffinfo=tags
        )
        carrier(
            ds,
            f"/World/Raster{kind}",
            CRS.from_epsg(32631).to_wkt(),
            f"raster-{kind}.tif",
            "GeoTIFF",
            "1",
            "0",
        )
    publish_claim(ds)
    ds.GetRootLayer().Save()
    # Eiffel source unit/up-axis adaptation is explicit ordinary authoring.
    ts, tw = stage("tower.usda")
    bind(tw, utm, (448000, 5410000, 80))
    anchor = bind(
        UsdGeom.Xform.Define(ts, "/World/Tower").GetPrim(),
        wgs,
        (2.2945, 48.8584, 70),
        (30, 0, 0),
    )
    UsdGeom.Xformable(anchor).AddTranslateOp(opSuffix="project").Set((120, -60, 0))
    UsdGeom.Xformable(anchor).AddRotateZOp(opSuffix="project").Set(20)
    UsdGeom.Xformable(anchor).AddScaleOp(opSuffix="project").Set((1.15, 1.15, 1.15))
    conform = UsdGeom.Xform.Define(ts, "/World/Tower/Conformance")
    conform.AddRotateXOp().Set(90)
    conform.AddScaleOp().Set((0.01, 0.01, 0.01))
    asset = UsdGeom.Xform.Define(
        ts, "/World/Tower/Conformance/IllustrativeSize"
    ).GetPrim()
    original_tower = Usd.Stage.Open(str(ORIGINAL / "tower.usdz"))
    bounds = (
        UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"])
        .ComputeWorldBound(original_tower.GetDefaultPrim())
        .ComputeAlignedRange()
    )
    authored_height = bounds.GetSize()[1] * 0.01
    UsdGeom.Xformable(asset).AddScaleOp(opSuffix="illustrativeSize").Set(
        (300 / authored_height,) * 3
    )
    source = UsdGeom.Xform.Define(ts, str(asset.GetPath()) + "/Asset").GetPrim()
    source.GetReferences().AddReference("../original/tower.usdz")
    publish_claim(ts)
    ts.GetRootLayer().Save()
    (ROOT / "audit/fixture-provenance.json").write_text(
        json.dumps(
            {
                "generation": "new from frozen proposal",
                "synthetic": [
                    "models.usda",
                    "composition.usda",
                    "permuted.cf.nc",
                    "raster-1.tif",
                    "raster-2.tif",
                ],
                "derived": {
                    "climate.cf.nc": "Original 2664 temperature values; added explicit CF association, synthetic ellipsoidal height=0 and second observation +1 K. These are illustration inputs, not inferred source facts.",
                    "tower.usda": "Original mesh; explicit centimetre/Y-up conformance, illustrative placement and project adjustment.",
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    generate()
