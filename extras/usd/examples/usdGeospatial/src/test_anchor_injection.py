#!/usr/bin/env python3
"""
test_anchor_injection.py -- the INVERSE of test_ancestor_compose, and the proof
that inject-don't-bake actually works.

test_ancestor_compose covers: a CARTESIAN ancestor over a GEOREF leaf.
This covers the case stock USD gets wrong and that the milestone fixes: a GEOREF
ANCHOR with a NON-GEOREF Cartesian SUBTREE. Without anchor injection, the child
(which has no crs:position) is invisible to the resolver and renders at the world
origin, because the anchor's georeferencing lives in crs:position -- which the USD
xform stack / XformCache never reads.

Scene:
  /World                       Xform (defaultPrim), identity
  /World/Anchor                Xform, crs:binding -> WGS84 geographic,
                               crs:position = (lon, lat, h)   [the georef ANCHOR]
    /World/Anchor/Bldg         Xform, AUTHORED local xform (translate in metres),
                               NO crs:position                [non-georef child]
      /World/Anchor/Bldg/Roof  Xform, AUTHORED local translate (z = up), NO crs:position

Assertions (all teeth, all vs CLOSED-FORM geodesy -- never a parallel pyproj call):
  P1 (anchor lands): injected anchor world == closed-form ECEF of (lon,lat,h).
  P2 (orientation injected, not just position): a child authored 1000 m EAST,
      500 m NORTH, 0 up lands at anchor + 1000*Ehat + 500*Nhat (ENU basis), NOT at
      anchor + (1000,500,0) in raw ECEF axes. We assert it matches the ENU
      placement AND is far (>>1 m) from the naive position-only placement -- so a
      position-only resolver provably FAILS this test.
  P3 (up is local vertical): a roof authored +20 m in local Z rises along the
      ellipsoidal normal at the anchor (closed-form (lon,lat,h+20)), to mm.
  P4 (stock USD sees origin): the same child resolved by ordinary XformCache
      (no injection) sits at its authored local offset near the ORIGIN -- ~6.4e6 m
      away from the truth. This is the gap the milestone closes; we assert it.
"""
import sys
import numpy as np
from pyproj import CRS
from pxr import Usd, UsdGeom, Sdf, Gf

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import _schema_setup  # noqa
import resolve_runtime as rr

GEO = CRS.from_epsg(4979)
ECEF = CRS.from_epsg(4978)
LON, LAT, H = -73.985656, 40.748817, 0.0     # NYC benchmark (independent NOAA point)

# closed-form WGS84 ground truth (NOT pyproj) -------------------------------
_A = 6378137.0
_F = 1.0 / 298.257223563
_E2 = _F * (2.0 - _F)


def cf_ecef(lon, lat, h=0.0):
    lam = np.radians(lon); phi = np.radians(lat)
    N = _A / np.sqrt(1.0 - _E2 * np.sin(phi) ** 2)
    return np.array([(N + h) * np.cos(phi) * np.cos(lam),
                     (N + h) * np.cos(phi) * np.sin(lam),
                     (N * (1.0 - _E2) + h) * np.sin(phi)])


def enu(lon, lat):
    lam = np.radians(lon); phi = np.radians(lat)
    e = np.array([-np.sin(lam), np.cos(lam), 0.0])
    n = np.array([-np.sin(phi) * np.cos(lam), -np.sin(phi) * np.sin(lam), np.cos(phi)])
    u = np.array([np.cos(phi) * np.cos(lam), np.cos(phi) * np.sin(lam), np.sin(phi)])
    return e, n, u


def author(out):
    stage = Usd.Stage.CreateNew(out)
    w = UsdGeom.Xform.Define(stage, "/World"); stage.SetDefaultPrim(w.GetPrim())
    UsdGeom.Scope.Define(stage, "/World/CRS")
    crs_prim = stage.DefinePrim("/World/CRS/WGS84_Geographic3D",
                                "CoordinateReferenceSystem")
    a = crs_prim.CreateAttribute("crs:wkt", Sdf.ValueTypeNames.Token, False,
                                 Sdf.VariabilityUniform)
    a.Set(GEO.to_wkt(version="WKT2_2019"))

    # The georef ANCHOR. Its OWN xform stack is identity (neutral scene).
    anchor = UsdGeom.Xform.Define(stage, "/World/Anchor").GetPrim()
    anchor.CreateRelationship("crs:binding", False).SetTargets([crs_prim.GetPath()])
    anchor.CreateAttribute("crs:position", Sdf.ValueTypeNames.Double3, False) \
          .Set(Gf.Vec3d(LON, LAT, H))

    # Non-georef child authored in LOCAL metres: 1000 m east, 500 m north.
    bldg = UsdGeom.Xform.Define(stage, "/World/Anchor/Bldg")
    bldg.AddTranslateOp().Set(Gf.Vec3d(1000.0, 500.0, 0.0))

    # Roof authored +20 m up in local Z, relative to Bldg.
    roof = UsdGeom.Xform.Define(stage, "/World/Anchor/Bldg/Roof")
    roof.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, 20.0))

    stage.GetRootLayer().Save()
    return stage


def main(out="out/_test_anchor_injection.usda"):
    stage = author(out)
    cache = {}
    xc = UsdGeom.XformCache()

    anchor = stage.GetPrimAtPath("/World/Anchor")
    bldg = stage.GetPrimAtPath("/World/Anchor/Bldg")
    roof = stage.GetPrimAtPath("/World/Anchor/Bldg/Roof")

    # Resolve via INJECTION.
    Mw_anchor, _ = rr.resolve_with_injection(anchor, ECEF, cache, xform_cache=xc)
    Mw_bldg, _ = rr.resolve_with_injection(bldg, ECEF, cache, xform_cache=xc)
    Mw_roof, _ = rr.resolve_with_injection(roof, ECEF, cache, xform_cache=xc)
    w_anchor = np.array(Mw_anchor.Transform(Gf.Vec3d(0, 0, 0)))
    w_bldg = np.array(Mw_bldg.Transform(Gf.Vec3d(0, 0, 0)))
    w_roof = np.array(Mw_roof.Transform(Gf.Vec3d(0, 0, 0)))

    # closed-form expectations
    gt_anchor = cf_ecef(LON, LAT, H)
    e, n, u = enu(LON, LAT)
    gt_bldg = gt_anchor + 1000.0 * e + 500.0 * n
    gt_roof = gt_bldg + 20.0 * u
    naive_bldg = gt_anchor + np.array([1000.0, 500.0, 0.0])   # position-only (WRONG)

    # stock USD (no injection): XformCache world of the child ignores crs:position
    stock_bldg = np.array(xc.GetLocalToWorldTransform(bldg).Transform(Gf.Vec3d(0, 0, 0)))

    d_anchor = np.linalg.norm(w_anchor - gt_anchor)
    d_bldg = np.linalg.norm(w_bldg - gt_bldg)
    d_roof = np.linalg.norm(w_roof - gt_roof)
    d_vs_naive = np.linalg.norm(w_bldg - naive_bldg)
    d_stock = np.linalg.norm(stock_bldg - gt_bldg)

    print(f"[author] {out}")
    print(f"  anchor (lon,lat,h)=({LON},{LAT},{H})")
    print(f"  child Bldg authored local (E,N,U)=(1000,500,0) m; Roof +20 m up")
    print()
    print(f"  closed-form anchor ECEF = {gt_anchor.round(3)}")
    print(f"  injected   anchor world = {w_anchor.round(3)}   d={d_anchor*1000:.3f} mm")
    print(f"  closed-form Bldg (ENU)  = {gt_bldg.round(3)}")
    print(f"  injected   Bldg world   = {w_bldg.round(3)}   d={d_bldg*1000:.3f} mm")
    print(f"  closed-form Roof (+20U) = {gt_roof.round(3)}")
    print(f"  injected   Roof world   = {w_roof.round(3)}   d={d_roof*1000:.3f} mm")
    print()
    print(f"[P2] distance from position-only (orientation-ignoring) placement: {d_vs_naive:.1f} m  (want >> 0)")
    print(f"[P4] stock USD (XformCache, no injection) places Bldg {d_stock/1e6:.3f}e6 m from truth (origin gap)")

    tol = 1e-3
    p1 = d_anchor < tol
    p2 = d_bldg < tol and d_vs_naive > 100.0     # lands at ENU AND not at naive
    p3 = d_roof < tol
    p4 = d_stock > 1e6                            # stock USD really does see ~origin
    ok = p1 and p2 and p3 and p4
    print()
    print(f"[check] P1 anchor lands (closed-form):                 {p1}")
    print(f"[check] P2 orientation injected (ENU, not raw axes):   {p2}")
    print(f"[check] P3 local +Z rises along ellipsoidal normal:    {p3}")
    print(f"[check] P4 stock USD would render child at ~origin:    {p4}")
    print("\nRESULT:", "ANCHOR INJECTION (inject-don't-bake) DEMONSTRATED ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*(sys.argv[1:2] or [])))
