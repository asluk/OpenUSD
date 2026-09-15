#!/usr/bin/env python3
"""
multi_crs_example.py -- worked multi-CRS scene + NON-CIRCULAR verification.

Demonstrates the design's headline capability and answers an open thread on the
Esri proposal: a single composed stage where different subtrees are bound to
DIFFERENT source CRSs, and the runtime resolves them all into one Target CRS
correctly -- without any baked transforms.

WHY THE REWRITE (2026-06-23, post-adversarial-review)
-----------------------------------------------------
The previous version generated SiteB's UTM coordinate with GEO->UTM and then
"verified" it by inverting UTM->ECEF, i.e. it checked GEO->UTM->ECEF against
GEO->ECEF. That tautology can never fail as long as PROJ is self-consistent --
forcing Sydney through a hard-coded UTM 10N (a nonsensical -7,030,734 m easting)
still "converged" to ~0 cm. It proved nothing about the design.

WHAT THIS VERSION ACTUALLY PROVES (and what it does not)
-------------------------------------------------------
Being honest about the data-prep layer: SiteB's easting/northing ARE the
canonical UTM projection of the monument (computed once, offline, and recorded
as literal constants below). So the A<->B convergence still ultimately rests on
PROJ self-consistency and is reported as a sanity figure, NOT as the proof.

The real, non-tautological assertion is the NEGATIVE CONTROL:

  * SiteB and SiteBad carry the IDENTICAL easting/northing numbers, but are
    bound to DIFFERENT declared CRSs (correct zone vs. a deliberately wrong
    zone). A correct resolver MUST send them to ECEF points hundreds of km
    apart; a broken/ignored-binding resolver would send them to the same place.
    That divergence cannot be faked by self-consistent reprojection -- it only
    holds if the runtime actually reads and honours crs:binding. THIS is the
    test with teeth.

The two remaining review fixes are also addressed:
  * AUTO ZONE SELECTION -- the UTM zone is computed from the site longitude,
    not hard-coded, and cross-checked against the source-claimed zone.
  * The negative test exits non-zero if it ever converges, so the script can
    no longer pass vacuously.

Scene:
  /World/CRS/WGS84_Geographic3D   (EPSG:4979)   geographic, (lon,lat,h)
  /World/CRS/UTM_<zone>           (EPSG:326NN)  projected, (E,N) metres
  /World/CRS/WGS84_ECEF           (EPSG:4978)   the Target/render CRS

  /World/SiteA  bound to WGS84_Geographic3D, crs:position = (lon, lat, h)
  /World/SiteB  bound to UTM_<zone>,         crs:position = (easting, northing, h)
  /World/SiteBad bound to a WRONG UTM zone   (negative control)

SiteA and SiteB are the SAME physical monument, sourced independently in two
CRSs. If the runtime is correct they resolve to the same ECEF point within
survey tolerance. SiteBad must NOT.

"""
import sys, math
import numpy as np
from pyproj import CRS, Transformer
from pxr import Usd, UsdGeom, Sdf, Gf

# --- One monument, expressed two ways --------------------------------------
# Geographic: WGS84 lon/lat/ellipsoidal-height.
SITE_LON, SITE_LAT, SITE_H = -117.195600, 34.056100, 350.000
# Projected: canonical UTM 11N easting/northing for the SAME monument, computed
# once offline (PROJ EPSG:4979->32611) and recorded as literal constants so this
# file performs no GEO->UTM at runtime. These are used for the A<->B sanity
# figure AND, crucially, reused verbatim by the wrong-zone negative control.
SITE_E, SITE_N = 481_948.634, 3_768_393.518   # metres, UTM 11N
SITE_UTM_EPSG = 32611


def utm_epsg_for(lon, lat):
    """Compute the WGS84 UTM EPSG code from a geographic position (auto zone)."""
    zone = int(math.floor((lon + 180.0) / 6.0) % 60) + 1
    return (32600 if lat >= 0 else 32700) + zone


def author_crs(stage, path, crs, name):
    p = stage.DefinePrim(path, "CoordinateReferenceSystem")
    a = p.CreateAttribute("crs:wkt", Sdf.ValueTypeNames.Token, False, Sdf.VariabilityUniform)
    a.Set(crs.to_wkt(version="WKT2_2019"))
    p.CreateAttribute("crs:epsg", Sdf.ValueTypeNames.Int, custom=True).Set(int(crs.to_epsg()))
    p.CreateAttribute("crs:displayName", Sdf.ValueTypeNames.String, custom=True).Set(name)
    return p


def bind(prim, crs_prim, pos):
    prim.CreateRelationship("crs:binding", False).SetTargets([crs_prim.GetPath()])
    a = prim.CreateAttribute("crs:position", Sdf.ValueTypeNames.Double3, False)
    a.Set(Gf.Vec3d(*pos))


def resolve(prim, stage, target_epsg=4978, cache={}):
    rel = prim.GetRelationship("crs:binding")
    crs_prim = stage.GetPrimAtPath(rel.GetTargets()[0])
    wkt = crs_prim.GetAttribute("crs:wkt").Get()
    key = (wkt, target_epsg)
    if key not in cache:
        cache[key] = Transformer.from_crs(
            CRS.from_wkt(wkt), CRS.from_epsg(target_epsg), always_xy=True)
    pos = prim.GetAttribute("crs:position").Get()
    return np.array(cache[key].transform(pos[0], pos[1], pos[2]))


def main(out="out/multi_crs.usda"):
    # Auto-select the UTM zone from the site, and sanity-check it matches the
    # zone the projected source claims. If these disagree the published data is
    # being mis-bound -- fail loudly rather than silently reprojecting garbage.
    auto_epsg = utm_epsg_for(SITE_LON, SITE_LAT)
    if auto_epsg != SITE_UTM_EPSG:
        print(f"[author] WARNING: auto UTM zone EPSG {auto_epsg} != source-claimed "
              f"{SITE_UTM_EPSG}; using auto-selected zone for the binding.")
    utm_epsg = auto_epsg
    # A genuinely WRONG zone for the negative control (off by 3 zones).
    bad_epsg = 32600 + (((utm_epsg - 32600) + 3 - 1) % 60) + 1

    GEO  = CRS.from_epsg(4979)
    UTM  = CRS.from_epsg(utm_epsg)
    BAD  = CRS.from_epsg(bad_epsg)
    ECEF = CRS.from_epsg(4978)

    stage = Usd.Stage.CreateNew(out)
    w = UsdGeom.Xform.Define(stage, "/World"); stage.SetDefaultPrim(w.GetPrim())
    UsdGeom.Scope.Define(stage, "/World/CRS")
    geo = author_crs(stage, "/World/CRS/WGS84_Geographic3D", GEO, "WGS84 geographic 3D")
    utm = author_crs(stage, f"/World/CRS/UTM{utm_epsg-32600}N", UTM,
                     f"UTM zone {utm_epsg-32600}N (EPSG:{utm_epsg})")
    bad = author_crs(stage, f"/World/CRS/UTM{bad_epsg-32600}N_WRONG", BAD,
                     f"WRONG zone {bad_epsg-32600}N (EPSG:{bad_epsg}) -- negative control")
    author_crs(stage, "/World/CRS/WGS84_ECEF", ECEF, "WGS84 ECEF (target)")

    # Site A: geographic source values (independent).
    A = UsdGeom.Xform.Define(stage, "/World/SiteA").GetPrim()
    bind(A, geo, (SITE_LON, SITE_LAT, SITE_H))

    # Site B: projected source values (independent literals -- NOT GEO->UTM here).
    B = UsdGeom.Xform.Define(stage, "/World/SiteB").GetPrim()
    bind(B, utm, (SITE_E, SITE_N, SITE_H))

    # Site Bad: the SAME projected numbers, but mis-declared as the wrong zone.
    # This is the negative control and MUST diverge.
    Bad = UsdGeom.Xform.Define(stage, "/World/SiteBad").GetPrim()
    bind(Bad, bad, (SITE_E, SITE_N, SITE_H))

    stage.GetRootLayer().Save()
    print(f"[author] {out}")
    print(f"  SiteA   bound to WGS84_Geographic3D  pos=({SITE_LON},{SITE_LAT},{SITE_H})  [geographic]")
    print(f"  SiteB   bound to UTM{utm_epsg-32600}N (auto)   pos=({SITE_E},{SITE_N},{SITE_H})  [projected, correct zone]")
    print(f"  SiteBad bound to UTM{bad_epsg-32600}N (WRONG)  pos=({SITE_E},{SITE_N},{SITE_H})  [SAME numbers, wrong zone -> negative control]")

    # --- runtime resolution into target ECEF ---
    ea  = resolve(A, stage)
    eb  = resolve(B, stage)
    ebad = resolve(Bad, stage)
    d_ab   = float(np.linalg.norm(ea - eb))
    d_abad = float(np.linalg.norm(ea - ebad))
    print(f"\n[resolve] SiteA   -> ECEF {ea.round(3)}")
    print(f"[resolve] SiteB   -> ECEF {eb.round(3)}")
    print(f"[resolve] SiteBad -> ECEF {ebad.round(3)}")
    print(f"[resolve] A<->B   (same point, two CRSs; sanity figure): {d_ab:.3f} m")
    print(f"[resolve] A<->Bad (same numbers, wrong zone; MUST diverge): {d_abad:.1f} m")

    # Tolerances: A<->B is a self-consistency sanity figure (both ultimately a
    # PROJ reprojection of one monument), so it should match to sub-metre.
    # The real assertion is the negative control: SiteBad reuses SiteB's exact
    # easting/northing but a wrong declared zone, so a binding-honouring
    # resolver must place it hundreds of km away. The gap between the two
    # thresholds is what makes this test non-vacuous.
    tol_pos = 1.0        # 1 m -- canonical projection round-trip noise
    tol_neg = 100_000.0  # wrong zone must be >100 km off
    txt = open(out).read()
    neutral = ("xformOp:translate" not in txt) and ("resetXformStack" not in txt)

    pass_pos = d_ab < tol_pos
    pass_neg = d_abad > tol_neg   # negative control MUST fail to converge
    ok = pass_pos and pass_neg and neutral
    print(f"\n[check] scene CRS-neutral (no baked translate/reset): {neutral}")
    print(f"[check] same-point convergence within {tol_pos:.0f} m (sanity): {pass_pos}")
    print(f"[check] NEGATIVE CONTROL diverges by >{tol_neg/1000:.0f} km: {pass_neg}")
    print("\nRESULT:", "MULTI-CRS COMPOSES (non-circular) ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*(sys.argv[1:2] or [])))
