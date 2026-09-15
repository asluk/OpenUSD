#!/usr/bin/env python3
"""
convert_omni_geospatial.py -- convert a dataset authored in the ORIGINAL Omniverse
geospatial schema (omni:geospatial:wgs84:*) into the Esri-aligned codeless schema
this bundle uses (crs:binding -> CoordinateReferenceSystem + crs:position).

This lets us run a REAL third-party dataset (NVIDIA OpenUSD-plugin-samples'
Deutsche Bahn railway, Apache-2.0) through our reference runtime unchanged --
evidence the runtime is not overfit to our own Earth-2 authoring.

Source schema (older Omniverse PoC):
  OmniWGS84ReferencePositionAPI on an ancestor:
      double3 omni:geospatial:wgs84:reference:referencePosition = (LAT, LON, H)
      double3 omni:geospatial:wgs84:reference:orientation
  OmniWGS84LocalPositionAPI on Xformable prims:
      double3 omni:geospatial:wgs84:local:position = (LAT, LON, H)

  NOTE the axis order is LAT-FIRST (lat, lon, h). Our crs:position contract is
  (x=lon/E, y=lat/N, z=h), so the converter SWAPS lat<->lon explicitly. Getting
  this wrong is exactly the axis-order landmine; the generalization suite asserts
  against closed-form geodesy so a bad swap would be caught.

Target schema (this bundle):
  /World/CRS/WGS84_Geographic3D : CoordinateReferenceSystem (crs:wkt = EPSG:4979)
  each georeferenced prim gets BindingAPI:
      rel crs:binding -> the CRS prim
      double3 crs:position = (LON, LAT, H)
The geometry subtrees (BasisCurves etc.) are carried over unchanged -- they are
local-metre offsets that anchor injection composes under the injected frame.
"""
import argparse
import sys
from pxr import Usd, UsdGeom, Sdf, Gf
from pyproj import CRS

REF_POS = "omni:geospatial:wgs84:reference:referencePosition"
REF_ORI = "omni:geospatial:wgs84:reference:orientation"
LOCAL_POS = "omni:geospatial:wgs84:local:position"


def convert(src_path, dst_path):
    src = Usd.Stage.Open(src_path)
    dst = Usd.Stage.CreateNew(dst_path)
    dst.SetMetadata("metersPerUnit", src.GetMetadata("metersPerUnit") or 1.0)
    UsdGeom.SetStageUpAxis(dst, UsdGeom.GetStageUpAxis(src) or UsdGeom.Tokens.z)

    # Author the target CRS prim once.
    UsdGeom.Scope.Define(dst, "/World/CRS")
    crs_prim = dst.DefinePrim("/World/CRS/WGS84_Geographic3D",
                              "CoordinateReferenceSystem")
    crs_prim.CreateAttribute("crs:wkt", Sdf.ValueTypeNames.Token, False,
                             Sdf.VariabilityUniform) \
            .Set(CRS.from_epsg(4979).to_wkt(version="WKT2_2019"))

    n_anchor = n_local = 0
    ref_lonlat = None

    # Copy the source hierarchy verbatim, translating the two API schemas.
    for sp in src.Traverse():
        path = sp.GetPath()
        if str(path).startswith("/World/CRS"):
            continue
        tp = dst.OverridePrim(path) if sp.GetTypeName() == "" else \
            dst.DefinePrim(path, sp.GetTypeName())

        # carry over generic attributes (geometry etc.), skipping the omni ones
        for attr in sp.GetAttributes():
            nm = attr.GetName()
            if nm in (REF_POS, REF_ORI, LOCAL_POS):
                continue
            v = attr.Get()
            if v is None:
                continue
            ta = tp.CreateAttribute(nm, attr.GetTypeName(),
                                    custom=attr.IsCustom(),
                                    variability=attr.GetVariability())
            ta.Set(v)

        def bind(lat_lon_h):
            lat, lon, h = lat_lon_h[0], lat_lon_h[1], lat_lon_h[2]
            tp.GetPrim().CreateRelationship("crs:binding", False) \
              .SetTargets([crs_prim.GetPath()])
            tp.GetPrim().CreateAttribute("crs:position", Sdf.ValueTypeNames.Double3,
                                         False).Set(Gf.Vec3d(lon, lat, h))  # SWAP
            return (lon, lat)

        if sp.GetAttribute(REF_POS):
            ref_lonlat = bind(sp.GetAttribute(REF_POS).Get())
            n_anchor += 1
        elif sp.GetAttribute(LOCAL_POS):
            bind(sp.GetAttribute(LOCAL_POS).Get())
            n_local += 1

    dst.GetRootLayer().Save()
    print(f"[convert] {src_path} -> {dst_path}")
    print(f"[convert]   reference anchors: {n_anchor}  local-position prims: {n_local}")
    print(f"[convert]   reference (lon,lat): {ref_lonlat}")
    print(f"[convert]   axis order: source LAT-first -> target crs:position (LON,LAT,H)")
    return dst_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    args = ap.parse_args()
    sys.exit(0 if convert(args.src, args.out) else 1)
