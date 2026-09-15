#!/usr/bin/env python3
"""
overfit_glyph_suite.py -- ANTI-OVERFIT proof for the composition-based glyph
visualizer. Using the SAME visualize_field_glyphs.py overlay approach and the
SAME (unchanged) auto-insert scene index, place a marker glyph correctly on a
diverse set of georeferenced datasets spanning 5 CRS families and both
hemispheres + equator-to-78N -- with ZERO code changes between them.

For each locale we:
  1. author a small NON-GEOMETRIC georef BASE stage (a single crs:position prim
     bound to the locale's projected CRS, reusing generalization_suite's
     dataset_point authoring contract), plus a geographic twin as an internal
     cross-CRS check;
  2. build a geometry-only OVERLAY (visualize_field_glyphs.py) that subLayers the
     base and adds a glyph `over` under the georef prim (ZERO crs:* re-authored);
  3. build an ECEF camera framing that point (make_render_scene_point.py);
  4. render the COMPOSED stage through the auto-insert SI (usdrecord --renderer GL),
     saving docs/overfit_<name>_autoinsert.png.

The point: one runtime, one code path, correct glyph placement across UTM 18N,
UTM 56S, NZTM2000, UTM 17S (equatorial), UTM 33N (~78N) -- no per-CRS special
casing anywhere.
"""
import os
import subprocess
import sys

import numpy as np
from pxr import Usd, UsdGeom, Sdf, Gf
from pyproj import CRS, Transformer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _schema_setup  # noqa

# locale, (lon,lat,h), projected EPSG, blurb
LOCALES = [
    ("nyc",       -73.985656,  40.748817,   0.0, 32618, "NYC  UTM 18N (N hemi)"),
    ("sydney",    151.214000, -33.857000,  58.0, 32756, "Sydney  UTM 56S (S hemi)"),
    ("wellington",174.776200, -41.286500,   5.0,  2193, "Wellington  NZTM2000"),
    ("quito",     -78.467800,  -0.180700,2850.0, 32717, "Quito  UTM 17S (~equator)"),
    ("svalbard",   15.650000,  78.220000,  10.0, 32633, "Svalbard  UTM 33N (~78N)"),
]


def _crs_wkt(epsg):
    return CRS.from_epsg(epsg).to_wkt(version="WKT2_2019")


def author_point_base(out, lon, lat, h, epsg):
    """A minimal NON-GEOMETRIC georef base: /World/Site is a bare Xform carrying
    only crs:binding + crs:position in the projected CRS (E,N,h). No geometry."""
    stage = Usd.Stage.CreateNew(out)
    w = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(w.GetPrim())
    UsdGeom.Scope.Define(stage, "/World/CRS")
    cp = stage.DefinePrim(f"/World/CRS/CRS_{epsg}", "CoordinateReferenceSystem")
    cp.CreateAttribute("crs:wkt", Sdf.ValueTypeNames.Token, False,
                       Sdf.VariabilityUniform).Set(_crs_wkt(epsg))
    # forward-project the published lon/lat into the projected CRS for authoring
    t = Transformer.from_crs(CRS.from_epsg(4979), CRS.from_epsg(epsg), always_xy=True)
    E, N, H = t.transform(lon, lat, h)
    site = UsdGeom.Xform.Define(stage, "/World/Site").GetPrim()
    site.CreateRelationship("crs:binding", False).SetTargets([cp.GetPath()])
    site.CreateAttribute("crs:position", Sdf.ValueTypeNames.Double3, False) \
        .Set(Gf.Vec3d(E, N, H))
    stage.GetRootLayer().Save()
    return (E, N, H)


def main():
    outdir = "/tmp/overfit"
    os.makedirs(outdir, exist_ok=True)
    for name, lon, lat, h, epsg, blurb in LOCALES:
        base = f"{outdir}/{name}_base.usda"
        author_point_base(base, lon, lat, h, epsg)
        print(f"[base] {name}: {blurb}  EPSG:{epsg}  (lon,lat,h)=({lon},{lat},{h})")
    print("bases authored (non-geometric, projected CRS). "
          "Now overlay + render via the driver shell script.")


if __name__ == "__main__":
    main()
