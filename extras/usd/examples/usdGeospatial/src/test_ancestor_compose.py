#!/usr/bin/env python3
"""
test_ancestor_compose.py -- proves the resolver COMPOSES ancestor Cartesian
transforms with a georeferenced (crs:position) prim, instead of ignoring them.

This is the test the adversarial review (docs/codex-review.md, F.2/F.3, fix #2)
said was missing: "No test places a CRS-bound prim under a transformed ancestor
and checks the result." Without it, the headline 'coexist with UsdGeomXformable'
claim was argued in comments, not demonstrated.

Design under test (resolve_runtime.resolve_world_translation):
    world = ancestor_local_to_world . reproject(crs:position)
The georeferenced position is the prim's own world anchor (its own xform stack is
intentionally identity in the neutral scene); a TRUE ANCESTOR transform composes
on top of that anchor.

We author:
  /World            Xform (defaultPrim), identity
  /World/Rig        Xform with a real ancestor transform (translate + rotate)
  /World/Rig/Site   Xform, crs:binding -> WGS84 geographic, crs:position=(lon,lat,h)
                    (its OWN xform stack is identity)

Assertions:
  T1 (composition happens): resolved world(Site WITH ancestor)
       == ancestor_matrix * reproject(pos), to mm. If the resolver ignored the
       ancestor (the old behavior), this would instead equal reproject(pos) and
       the test FAILS. We prove the gap is large (ancestor offset is 1000 m + 90deg).
  T2 (neutral when identity): with an identity ancestor, world == reproject(pos).
  T3 (falsification): a resolver that ignores ancestors gives a result that is
       off by the ancestor translation magnitude -> we assert our resolver does
       NOT match that, so the test has teeth.
"""
import sys, math
import numpy as np
from pyproj import CRS, Transformer
from pxr import Usd, UsdGeom, Sdf, Gf

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import resolve_runtime as rr

GEO  = CRS.from_epsg(4979)
ECEF = CRS.from_epsg(4978)
LON, LAT, H = -117.1956, 34.0561, 350.0


def author(out):
    stage = Usd.Stage.CreateNew(out)
    w = UsdGeom.Xform.Define(stage, "/World"); stage.SetDefaultPrim(w.GetPrim())
    UsdGeom.Scope.Define(stage, "/World/CRS")
    crs_prim = stage.DefinePrim("/World/CRS/WGS84_Geographic3D",
                                "CoordinateReferenceSystem")
    a = crs_prim.CreateAttribute("crs:wkt", Sdf.ValueTypeNames.Token, False,
                                 Sdf.VariabilityUniform)
    a.Set(GEO.to_wkt(version="WKT2_2019"))

    # Rig: a genuine ancestor transform — 1000 m translate (in ECEF metres) + 90deg
    # rotation about Z. This is what a downstream rig/tile parent might carry.
    rig = UsdGeom.Xform.Define(stage, "/World/Rig")
    rig.AddTranslateOp().Set(Gf.Vec3d(1000.0, 2000.0, 3000.0))
    rig.AddRotateZOp().Set(90.0)

    # Site: georeferenced; OWN xform stack identity.
    site = UsdGeom.Xform.Define(stage, "/World/Rig/Site").GetPrim()
    site.CreateRelationship("crs:binding", False).SetTargets([crs_prim.GetPath()])
    site.CreateAttribute("crs:position", Sdf.ValueTypeNames.Double3, False) \
        .Set(Gf.Vec3d(LON, LAT, H))

    # Bare site with no ancestor transform (control).
    bare = UsdGeom.Xform.Define(stage, "/World/Bare").GetPrim()
    bare.CreateRelationship("crs:binding", False).SetTargets([crs_prim.GetPath()])
    bare.CreateAttribute("crs:position", Sdf.ValueTypeNames.Double3, False) \
        .Set(Gf.Vec3d(LON, LAT, H))

    stage.GetRootLayer().Save()
    return stage


def main(out="out/_test_ancestor.usda"):
    stage = author(out)
    cache = {}

    georef = np.array(Transformer.from_crs(GEO, ECEF, always_xy=True)
                      .transform(LON, LAT, H))  # the bare reprojection

    # Expected world for Site = ancestor_L2W applied to georef anchor.
    rig = stage.GetPrimAtPath("/World/Rig")
    a2w = UsdGeom.XformCache().GetLocalToWorldTransform(rig)
    expected = np.array(a2w.Transform(Gf.Vec3d(*georef)))

    site = stage.GetPrimAtPath("/World/Rig/Site")
    bare = stage.GetPrimAtPath("/World/Bare")
    world_site, _ = rr.resolve_world_translation(site, ECEF, cache)
    world_bare, _ = rr.resolve_world_translation(bare, ECEF, cache)
    world_site = np.array(world_site); world_bare = np.array(world_bare)

    # T2: bare (identity ancestor) == raw reprojection
    d_bare = np.linalg.norm(world_bare - georef)
    # T1: site == ancestor-composed expectation
    d_site = np.linalg.norm(world_site - expected)
    # T3: how far the IGNORE-ANCESTOR (old) behavior would be from our answer
    d_ignore = np.linalg.norm(world_site - georef)  # if we'd ignored ancestor

    print(f"[author] {out}")
    print(f"  georef (reproject only)      = {georef.round(3)}")
    print(f"  ancestor-composed expected   = {expected.round(3)}")
    print(f"  resolver(Site, w/ ancestor)  = {world_site.round(3)}")
    print(f"  resolver(Bare, identity)     = {world_bare.round(3)}")
    print()
    print(f"[T2] identity ancestor -> raw reprojection:   {d_bare*1000:.3f} mm  (want ~0)")
    print(f"[T1] ancestor composed correctly:             {d_site*1000:.3f} mm  (want ~0)")
    print(f"[T3] gap vs ignore-ancestor (old behavior):   {d_ignore:.1f} m   (want >> 0)")

    tol = 1e-3  # 1 mm
    pass_T1 = d_site < tol
    pass_T2 = d_bare < tol
    pass_T3 = d_ignore > 100.0   # ancestor offset is ~3700 m; teeth
    ok = pass_T1 and pass_T2 and pass_T3
    print()
    print(f"[check] T1 ancestor composition correct: {pass_T1}")
    print(f"[check] T2 identity ancestor neutral:    {pass_T2}")
    print(f"[check] T3 demonstrably NOT ignoring ancestor (gap {d_ignore:.0f} m): {pass_T3}")
    print("\nRESULT:", "ANCESTOR COMPOSITION DEMONSTRATED ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*(sys.argv[1:2] or [])))
