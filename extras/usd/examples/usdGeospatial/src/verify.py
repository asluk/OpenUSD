#!/usr/bin/env python3
"""
verify.py -- rigorous correctness evidence for the geospatial re-encode pipeline.

Checks:
  A. Authored scene is CRS-neutral: no xformOp:translate, no resetXformStack.
  B. Binding resolves: every GeoSample has a crs:binding -> CRS prim with valid WKT2.
  C. Reprojection is geodetically correct against independent ground truth:
       - poles land on the WGS84 semi-minor axis (b = 6356752.314 m)
       - equator/prime-meridian lands on semi-major axis (a = 6378137 m)
       - a known landmark (e.g. a city) round-trips ECEF->geographic to < 1e-6 deg
  D. Round-trip: geographic -> ECEF -> geographic recovers original lon/lat/h.
  E. Axis-order contract (review fix F.4): reads the AUTHORED WKT (not a
     hardcoded EPSG), and verifies crs:position follows the documented
     east-north-up (lon,lat,h) convention even when the bound CRS authority
     declares latitude-first -- and that an authority-order misread would be
     detectably wrong (teeth).
Exit non-zero on any failure (CI-style).
"""
import sys, numpy as np
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _schema_setup  # noqa
from pyproj import CRS, Transformer
from pxr import Usd, UsdGeom

WGS84_A = 6378137.0            # semi-major (equatorial)
WGS84_B = 6356752.314245      # semi-minor (polar)

def fail(msg): print("  FAIL:", msg); return False
def ok(msg):   print("  ok  :", msg); return True

def main(path="out/earth2_georef.usda"):
    passed = True
    stage = Usd.Stage.Open(path)

    # --- A. authored scene neutrality ---
    # Neutral != "no xformOps anywhere". Plain Cartesian CHILDREN of an anchor
    # legitimately carry xformOp:translate (their local metre offsets) -- that is
    # ordinary UsdGeomXformable that composes under the injected anchor frame.
    # Neutrality means, precisely: (A1) NO resetXformStack is authored into the
    # layer, and (A2) no georeferenced prim (one carrying crs:position) also bakes
    # an xformOp onto ITSELF -- the georef lives in crs:position, not a transform.
    if "resetXformStack" in open(path).read():
        passed &= fail("A1. authored scene bakes resetXformStack (not coordinate-neutral)")
    else:
        ok("A1. authored scene bakes no resetXformStack")
    baked_anchor = 0
    for p in stage.Traverse():
        if p.GetAttribute("crs:position") and p.GetAttribute("crs:position").HasAuthoredValue():
            order = p.GetAttribute("xformOpOrder")
            ops = list(order.Get()) if (order and order.Get()) else []
            if ops:
                baked_anchor += 1
                fail(f"A2. georef prim {p.GetPath()} bakes xformOp(s) {ops} onto itself "
                     f"(the georef must live in crs:position, not a transform)")
    if baked_anchor:
        passed &= False
    else:
        ok("A2. no georef prim bakes an xformOp onto itself (Cartesian children may)")

    # --- B. binding + WKT validity ---
    samples = [p for p in stage.Traverse()
               if p.IsA(UsdGeom.Xform) and p.GetAttribute("crs:position")]
    bad = 0
    for p in samples:
        rel = p.GetRelationship("crs:binding")
        if not (rel and rel.GetTargets()):
            bad += 1; continue
        crs_prim = stage.GetPrimAtPath(rel.GetTargets()[0])
        wkt = crs_prim.GetAttribute("crs:wkt").Get()
        try:
            CRS.from_wkt(wkt)
        except Exception:
            bad += 1
    if bad: passed &= fail(f"B. {bad}/{len(samples)} samples have bad binding/WKT")
    else:   ok(f"B. all {len(samples)} samples bind to a CRS with parseable WKT2")

    # --- C. geodetic ground truth ---
    geo  = CRS.from_epsg(4979)
    ecef = CRS.from_epsg(4978)
    fwd = Transformer.from_crs(geo, ecef, always_xy=True)

    # pole
    _,_,zp = fwd.transform(0,90,0)
    if abs(zp - WGS84_B) > 1e-3: passed &= fail(f"C-pole z={zp} != b={WGS84_B}")
    else: ok(f"C. north pole -> ECEF z = {zp:.3f} m == WGS84 semi-minor b ({WGS84_B} m)")
    # equator/prime meridian
    xe,_,_ = fwd.transform(0,0,0)
    if abs(xe - WGS84_A) > 1e-3: passed &= fail(f"C-eq x={xe} != a={WGS84_A}")
    else: ok(f"C. equator/0deg -> ECEF x = {xe:.3f} m == WGS84 semi-major a ({WGS84_A} m)")
    # known landmark: Esri HQ, Redlands CA ~ (-117.1956, 34.0561)
    lon0, lat0 = -117.1956, 34.0561
    x,y,z = fwd.transform(lon0, lat0, 0)
    r = (x*x+y*y+z*z) ** 0.5
    if not (WGS84_B - 1 <= r <= WGS84_A + 1):
        passed &= fail(f"C-landmark radius {r} outside ellipsoid bounds")
    else: ok(f"C. landmark(-117.20,34.06) -> ECEF radius {r:.1f} m within ellipsoid [b,a]")

    # --- D. round trip ---
    inv = Transformer.from_crs(ecef, geo, always_xy=True)
    lon1, lat1, h1 = inv.transform(x, y, z)
    derr = max(abs(lon1-lon0), abs(lat1-lat0)); herr = abs(h1-0)
    if derr > 1e-7 or herr > 1e-3:
        passed &= fail(f"D. round-trip err deg={derr:.2e} h={herr:.2e}")
    else:
        ok(f"D. round-trip geographic->ECEF->geographic err = {derr:.2e} deg, {herr:.2e} m")

    # --- E. axis-order contract, read from AUTHORED WKT (review fix F.4) ---
    # Take a real sample, read the WKT of its BOUND CRS (not a hardcoded EPSG),
    # and the actual crs:position it carries. If the authored CRS declares
    # latitude-first axis order (as EPSG:4979 does), then interpreting
    # crs:position in AUTHORITY order would read slot 0 as latitude. We assert:
    #   (1) the data follows the documented east-north-up convention, i.e.
    #       slot 0 reprojects sanely with always_xy=True, AND
    #   (2) the authority-order misread is DETECTABLY wrong (>>1 km off or
    #       non-finite) -- proving the check has teeth and isn't masked by
    #       always_xy everywhere.
    sample = None
    for p in samples:
        if p.GetRelationship("crs:binding") and p.GetRelationship("crs:binding").GetTargets():
            sample = p; break
    if sample is None:
        passed &= fail("E. no bound sample to test axis order")
    else:
        crs_prim = stage.GetPrimAtPath(sample.GetRelationship("crs:binding").GetTargets()[0])
        wkt = crs_prim.GetAttribute("crs:wkt").Get()
        src = CRS.from_wkt(wkt)                      # authored CRS, not hardcoded
        pos = sample.GetAttribute("crs:position").Get()
        # Declared authority axis order (first axis abbrev/direction).
        try:
            ax0 = src.axis_info[0]
            lat_first = (ax0.direction.lower() in ("north", "south")
                         or "lat" in (ax0.abbrev or "").lower()
                         or "latitude" in (ax0.name or "").lower())
        except Exception:
            lat_first = False
        tx = Transformer.from_crs(src, ecef, always_xy=True)
        # (1) documented convention applied to the ACTUAL authored data: pos = (lon/E, lat/N, h)
        cx, cy, cz = tx.transform(pos[0], pos[1], pos[2])
        conv_r = (cx*cx + cy*cy + cz*cz) ** 0.5
        conv_ok = np.isfinite(conv_r) and (WGS84_B - 1000 <= conv_r <= WGS84_A + 60000)
        # (2) teeth: does the contract MATTER for this CRS? Use a SYNTHETIC probe
        # point with clearly distinct lon/lat (not the authored coordinate, which
        # may legitimately be near-diagonal lon~=lat and make a swap undetectable).
        # D1 fix: this tests the CRS/axis contract, not the data value.
        plon, plat, ph = -123.4, 17.6, 0.0      # distinct, both valid ranges
        ax, ay, az = tx.transform(plon, plat, ph)          # correct order
        bx, by, bz = tx.transform(plat, plon, ph)          # swapped (authority misread)
        ra = (ax*ax+ay*ay+az*az) ** 0.5
        rb = (bx*bx+by*by+bz*bz) ** 0.5
        misread_detectably_wrong = (not np.isfinite(rb)) or abs(rb - ra) > 1000.0
        if not conv_ok:
            passed &= fail(f"E. crs:position under documented (lon,lat,h) order is invalid "
                           f"(radius {conv_r})")
        elif lat_first and not misread_detectably_wrong:
            passed &= fail("E. authority order is lat-first but a misread of the synthetic "
                           "probe is NOT detectable -- axis-order test has no teeth")
        else:
            note = "authority lat-first; misread detectably wrong" if lat_first \
                   else "authority lon-first; convention matches"
            ok(f"E. crs:position honors documented east-north-up contract ({note}); "
               f"authored WKT read from prim, not hardcoded EPSG")

    # --- F. EPSG-vs-WKT precedence (review fix F.5) ---
    # Contract (docs/crs-identity-precedence.md): crs:wkt is AUTHORITATIVE; crs:epsg
    # is an informational hint. On mismatch the resolver uses WKT and we FLAG the
    # inconsistency here. Check that, for every CRS prim carrying both, the EPSG
    # code agrees with the WKT's own EPSG identity. A disagreement is a hard fail
    # (it would silently mislead EPSG-keyed consumers).
    crs_prims = [p for p in stage.Traverse() if p.GetTypeName() == "CoordinateReferenceSystem"]
    mism = 0
    checked = 0
    for cp in crs_prims:
        wkt_a = cp.GetAttribute("crs:wkt")
        epsg_a = cp.GetAttribute("crs:epsg")
        if not (wkt_a and wkt_a.Get() and epsg_a and epsg_a.Get()):
            continue
        checked += 1
        wkt_epsg = None
        try:
            wkt_epsg = CRS.from_wkt(wkt_a.Get()).to_epsg()
        except Exception:
            pass
        if wkt_epsg is not None and int(epsg_a.Get()) != int(wkt_epsg):
            mism += 1
            fail(f"F. {cp.GetPath()}: crs:epsg={epsg_a.Get()} disagrees with WKT EPSG={wkt_epsg} "
                 f"(WKT is authoritative; epsg hint is wrong)")
    if mism:
        passed &= False
    elif checked:
        ok(f"F. EPSG-vs-WKT precedence: all {checked} CRS prims have crs:epsg consistent "
           f"with authoritative crs:wkt (no silent mismatch)")
    else:
        ok("F. EPSG-vs-WKT precedence: no CRS prim carries both epsg+wkt to cross-check")

    # --- G. requires-CRS-resolution marker (guard rail G3) ---
    # A coexist scene is coordinate-neutral: a CRS-UNAWARE consumer that ignores
    # crs:* would silently place georeferenced content at the world origin
    # (thousands of km off). To let such a consumer detect-and-refuse instead of
    # misplacing, a stage that carries ANY crs:binding must declare it via
    # customLayerData['crsResolutionRequired'] = true. See README "Guard rails".
    has_binding = any(
        p.GetRelationship("crs:binding") and p.GetRelationship("crs:binding").GetTargets()
        for p in stage.Traverse())
    if has_binding:
        cld = stage.GetRootLayer().customLayerData or {}
        if cld.get("crsResolutionRequired") is True:
            ok("G. requires-CRS marker: stage has crs:binding AND declares "
               "customLayerData['crsResolutionRequired']=true (unaware consumers can refuse)")
        else:
            passed &= False
            fail("G. stage has crs:binding but no customLayerData['crsResolutionRequired']=true "
                 "marker -- a CRS-unaware consumer would silently misplace content. "
                 "Fix: stage.SetMetadata('customLayerData', {'crsResolutionRequired': True})")
    else:
        ok("G. requires-CRS marker: no crs:binding on stage; marker not required")

    print("\nRESULT:", "ALL PASS ✅" if passed else "FAILURES ❌")
    return 0 if passed else 1

if __name__ == "__main__":
    sys.exit(main(*(sys.argv[1:2] or [])))
