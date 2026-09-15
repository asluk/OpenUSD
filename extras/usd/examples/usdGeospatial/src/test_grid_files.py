#!/usr/bin/env python3
"""
test_grid_files.py -- proves the resolver READS crs:gridFiles asset paths and
registers their directories on PROJ's grid search path (the external-grid
plumbing for high-accuracy datum/geoid transforms, review F.5).

Scope (kept honest): this verifies the ASSET PLUMBING -- that an authored
crs:gridFiles asset is resolved and its directory is added to PROJ's data dirs so
PROJ *could* find the grid. It does NOT fabricate a grid-applied transform: PROJ
applies a grid only when it exists and an operation selects it, and authoring a
real GeoTIFF grid needs GDAL / network data not available here. So we assert:
  G1 the authored asset path is read back by the resolver helper, and
  G2 its containing directory ends up in pyproj's data-dir search list.
"""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _schema_setup  # noqa
from pyproj import CRS
from pxr import Usd, UsdGeom, Sdf, Gf
import resolve_runtime as rr

GEO = CRS.from_epsg(4979)


def main(out="out/_test_grid.usda"):
    # Create a stand-in grid asset file in a temp dir (content irrelevant to the
    # plumbing test; we only check the directory gets registered).
    gdir = tempfile.mkdtemp(prefix="crs_grids_")
    gfile = os.path.join(gdir, "fake_datum_shift.tif")
    with open(gfile, "wb") as f:
        f.write(b"NOT_A_REAL_GRID")

    stage = Usd.Stage.CreateNew(out)
    w = UsdGeom.Xform.Define(stage, "/World"); stage.SetDefaultPrim(w.GetPrim())
    UsdGeom.Scope.Define(stage, "/World/CRS")
    crs = stage.DefinePrim("/World/CRS/Geo", "CoordinateReferenceSystem")
    crs.CreateAttribute("crs:wkt", Sdf.ValueTypeNames.Token, False,
                        Sdf.VariabilityUniform).Set(GEO.to_wkt(version="WKT2_2019"))
    crs.CreateAttribute("crs:gridFiles", Sdf.ValueTypeNames.AssetArray, False,
                        Sdf.VariabilityUniform).Set([Sdf.AssetPath(gfile)])

    site = UsdGeom.Xform.Define(stage, "/World/Site").GetPrim()
    site.CreateRelationship("crs:binding", False).SetTargets([crs.GetPath()])
    site.CreateAttribute("crs:position", Sdf.ValueTypeNames.Double3, False) \
        .Set(Gf.Vec3d(-117.0, 34.0, 0.0))
    stage.GetRootLayer().Save()

    # G1: resolver reads the asset paths.
    read = rr._register_grid_files(stage, crs.GetPath())
    g1 = any(os.path.basename(p) == "fake_datum_shift.tif" for p in read)

    # G2: the grid directory is now on pyproj's data-dir search path.
    from pyproj.datadir import get_data_dir
    dd = get_data_dir()
    g2 = gdir in dd  # append_data_dir prepends/joins; substring check is sufficient

    print(f"[author] {out}")
    print(f"  authored crs:gridFiles -> {gfile}")
    print(f"  resolver read back     -> {read}")
    print(f"  pyproj data dirs contain grid dir: {g2}")
    print()
    print(f"[check] G1 crs:gridFiles asset path read by resolver: {g1}")
    print(f"[check] G2 grid directory registered on PROJ search path: {g2}")
    ok = g1 and g2
    print("\nRESULT:", "GRID-FILE PLUMBING WIRED ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*(sys.argv[1:2] or [])))
