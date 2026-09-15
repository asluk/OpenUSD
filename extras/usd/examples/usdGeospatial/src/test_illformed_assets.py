#!/usr/bin/env python3
"""
test_illformed_assets.py -- what BREAKS in a "coexist" geospatial asset, why, and
the exact authoring fix.

The companion head-to-head (test_coexist_vs_baked.py) shows coexist reproduces the
baked approach to 0.0 mm WHEN the asset obeys three structural invariants. This
script does the inverse: for each of the three guard-rail invariants it authors an
ILL-FORMED asset, shows the concrete failure (a wrong-place number vs closed-form
geodesy, or a silent misplacement), then authors the CORRECTED asset and shows it
resolves to truth. Each case prints, in order:

    [break]  the mis-authored asset + what a runtime does with it (a real number)
    [why]    the root cause, in one line
    [fix]    the corrected asset (the minimal edit)
    [proof]  the corrected asset resolved vs independent closed-form geodesy

Ground truth is computed directly with pyproj (independent of the USD resolver), so
"correct" is anchored to geodesy, not to our own runtime. The exit code gates only
on objective facts: each broken asset misplaces beyond a gross threshold, and each
corrected asset lands within a tight geodesy tolerance.

Guard rails demonstrated (see README "Guard rails"):
  G1  anchor-vs-child must be unambiguous
      break: two prims each own crs:position and are parented, expecting relative
             placement; the child ignores the parent and jumps to its own CRS point.
  G2  child offsets must be authored in the frame the anchor's CRS implies
      break: a projected-anchor child's offsets are authored as if they were ENU
             metres and lifted through ENU; grid convergence bends them ~metres.
  G3  a CRS-requiring stage must declare it
      break: a CRS-unaware consumer opens the scene with no marker to refuse on and
             silently places the building thousands of km away.
"""
import os
import sys
import math
import numpy as np
from pxr import Usd, UsdGeom, Sdf, Gf
from pyproj import CRS, Transformer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crs_engine as ce
import resolve_runtime as rr

ECEF = CRS.from_epsg(4978)
UTM17N = CRS.from_epsg(26917)   # NAD83 / UTM 17N (New York)
UTM30N = CRS.from_epsg(32630)   # WGS84 / UTM 30N (anchor)
WKT17 = UTM17N.to_wkt()
WKT30 = UTM30N.to_wkt()

# Anchor + building placement reused from the head-to-head POC scene.
ANCHOR_UTM30 = (708276.91981815, 5706731.7076084, 50.0)  # World anchor, UTM30N grid
NY_UTM17 = (586000.0, 4515000.0, 50.0)                   # NewYork anchor, UTM17N grid
MOMA_OFFSET = (-393.7, -337.3, 0.0)                      # MoMa, local grid metres
CORNER_OFFSET = (50.0, 100.0, 30.0)                      # a corner of the building


def _ecef_of_utm17(e, n, h):
    """Independent ground truth: a UTM17N grid point -> ECEF, via pyproj only."""
    t = Transformer.from_crs(UTM17N, ECEF, always_xy=True)
    x, y, z = t.transform(e, n, h)
    return np.array([x, y, z])


def _hr(title):
    print("\n" + "=" * 74)
    print(title)
    print("=" * 74)


def _crs_scope(stage):
    UsdGeom.Xform.Define(stage, "/World")
    scope = stage.DefinePrim("/World/CRS", "Scope")
    for name, wkt in (("UTM30N", WKT30), ("UTM17N", WKT17)):
        p = stage.DefinePrim(f"/World/CRS/{name}", "CoordinateReferenceSystem")
        p.CreateAttribute("crs:wkt", Sdf.ValueTypeNames.Token,
                          custom=False).Set(wkt)


def _bind(prim, crs_path, pos):
    prim.ApplyAPI("BindingAPI") if hasattr(prim, "ApplyAPI") else None
    rel = prim.GetPrim().CreateRelationship("crs:binding", custom=False)
    rel.SetTargets([Sdf.Path(crs_path)])
    prim.GetPrim().CreateAttribute("crs:position", Sdf.ValueTypeNames.Double3,
                                   custom=False).Set(Gf.Vec3d(*pos))


def _translate(stage, path, xyz):
    x = UsdGeom.Xform.Define(stage, path)
    op = x.AddTranslateOp()
    op.Set(Gf.Vec3d(*xyz))
    return x


# ---------------------------------------------------------------------------
# G1 -- anchor-vs-child must be unambiguous
# ---------------------------------------------------------------------------
def case_g1():
    _hr("G1  anchor-vs-child must be unambiguous")

    # BREAK: author a "detail" prim that ALSO owns its own crs:position (as if it
    # were an independent georeferenced leaf), and parent it under the building
    # expecting it to sit at MoMa + local offset. It does not: it resolves against
    # its OWN binding and jumps to that CRS point, ignoring the parent entirely.
    stage = Usd.Stage.CreateInMemory()
    stage.SetMetadata("upAxis", "Z")
    stage.SetMetadata("metersPerUnit", 1.0)
    _crs_scope(stage)
    ny = UsdGeom.Xform.Define(stage, "/World/NewYork")
    _bind(ny, "/World/CRS/UTM17N", NY_UTM17)
    moma = _translate(stage, "/World/NewYork/MoMa", MOMA_OFFSET)
    # the mistake: the corner is authored as its OWN georef leaf (own crs:position)
    # rather than a plain Cartesian child, and parented expecting relative placement
    corner = UsdGeom.Xform.Define(stage, "/World/NewYork/MoMa/Corner")
    _bind(corner, "/World/CRS/UTM17N",
          (NY_UTM17[0], NY_UTM17[1], NY_UTM17[2]))  # its own position == the anchor!
    corner_prim = stage.GetPrimAtPath("/World/NewYork/MoMa/Corner")

    cache = {}
    xc = UsdGeom.XformCache()
    # author-intended world: MoMa + corner offset, resolved in-plane
    intended = _ecef_of_utm17(NY_UTM17[0] + MOMA_OFFSET[0] + CORNER_OFFSET[0],
                              NY_UTM17[1] + MOMA_OFFSET[1] + CORNER_OFFSET[1],
                              NY_UTM17[2] + MOMA_OFFSET[2] + CORNER_OFFSET[2])
    world_broken, anchor_path = rr.resolve_with_injection(corner_prim, ECEF, cache,
                                                          xform_cache=xc)
    got = np.array(world_broken.Transform(Gf.Vec3d(0, 0, 0)))
    err = np.linalg.norm(got - intended)
    print(f"[break]  /World/NewYork/MoMa/Corner ALSO carries its own crs:binding +")
    print(f"[break]    crs:position, so it is treated as an independent georef leaf.")
    print(f"[break]    Author expected: MoMa origin + corner offset (50,100,30 m).")
    print(f"[break]    Resolver used the corner's OWN binding -> nearest anchor = "
          f"{anchor_path}")
    print(f"[break]    misplaced by {err:.3f} m ({err*100:.0f} cm) vs the intended spot")
    print(f"[why]    a prim that owns crs:position is an ANCHOR, not a relative child;"
          f" parenting does not make it relative.")

    # FIX: drop the corner's own binding/position; author it as a plain Cartesian
    # child (ordinary xformOp:translate). It then composes under MoMa's frame.
    stage2 = Usd.Stage.CreateInMemory()
    stage2.SetMetadata("upAxis", "Z")
    stage2.SetMetadata("metersPerUnit", 1.0)
    _crs_scope(stage2)
    ny2 = UsdGeom.Xform.Define(stage2, "/World/NewYork")
    _bind(ny2, "/World/CRS/UTM17N", NY_UTM17)
    _translate(stage2, "/World/NewYork/MoMa", MOMA_OFFSET)
    _translate(stage2, "/World/NewYork/MoMa/Corner", CORNER_OFFSET)  # plain child
    corner2 = stage2.GetPrimAtPath("/World/NewYork/MoMa/Corner")
    print(f"[fix]    remove Corner's crs:binding + crs:position; author it as a plain")
    print(f"[fix]      Cartesian child:  double3 xformOp:translate = (50, 100, 30)")
    world_fixed, _ = rr.resolve_with_injection(corner2, ECEF, {}, xform_cache=UsdGeom.XformCache())
    gotf = np.array(world_fixed.Transform(Gf.Vec3d(0, 0, 0)))
    errf = np.linalg.norm(gotf - intended) * 1000.0
    print(f"[proof]  corrected corner vs closed-form geodesy = {errf:.6f} mm")
    return err > 1.0 and errf < 1.0


# ---------------------------------------------------------------------------
# G2 -- child offsets must be authored in the frame the anchor's CRS implies
# ---------------------------------------------------------------------------
def case_g2():
    _hr("G2  child offsets must be authored in the frame the anchor's CRS implies")

    # A projected (UTM) anchor's child offsets live in the GRID plane. If a runtime
    # (or an author who assumes "local metres == ENU") composes them through the
    # anchor's true-ENU basis, grid convergence + point-scale bend them. We show the
    # ENU-lift result (the WRONG frame) vs the in-plane result (the CRS-implied frame).
    eng = ce.get_engine()
    # ground truth: grid add + reproject (the projected CRS's own plane)
    gt = _ecef_of_utm17(NY_UTM17[0] + MOMA_OFFSET[0] + CORNER_OFFSET[0],
                        NY_UTM17[1] + MOMA_OFFSET[1] + CORNER_OFFSET[1],
                        NY_UTM17[2] + MOMA_OFFSET[2] + CORNER_OFFSET[2])
    total_off = (MOMA_OFFSET[0] + CORNER_OFFSET[0],
                 MOMA_OFFSET[1] + CORNER_OFFSET[1],
                 MOMA_OFFSET[2] + CORNER_OFFSET[2])

    # WRONG frame: lift the grid offset through the anchor's true-ENU basis.
    # local_frame_to_ecef returns a Gf.Matrix4d (the rigid ENU->ECEF transform).
    M = eng.local_frame_to_ecef(WKT17, NY_UTM17[0], NY_UTM17[1], NY_UTM17[2])
    enu_world = np.array(M.Transform(Gf.Vec3d(*total_off)))
    err_enu = np.linalg.norm(enu_world - gt)

    # RIGHT frame: compose in the grid plane and reproject
    X, Y, Z = eng.project_grid_offset_to_target(WKT17, ECEF.to_wkt(), NY_UTM17,
                                                total_off)
    inplane = np.array([X, Y, Z])
    err_inplane = np.linalg.norm(inplane - gt)

    print(f"[break]  projected (UTM17N) anchor; child offset {total_off} m composed")
    print(f"[break]    through the anchor's TRUE-ENU basis (as if offsets were ENU)")
    print(f"[break]    misplaced by {err_enu:.3f} m ({err_enu*100:.0f} cm) vs geodesy")
    print(f"[why]    UTM grid axes differ from true ENU by grid-convergence + point-")
    print(f"[why]      scale; over the ~{np.hypot(*total_off[:2]):.0f} m lever that is metres.")
    print(f"[fix]    author/compose the offset IN the anchor's grid plane, then")
    print(f"[fix]      reproject (grid add + reproject) -- the CRS-implied frame.")
    print(f"[proof]  in-plane composition vs closed-form geodesy = {err_inplane*1000.0:.6f} mm")
    return err_enu > 1.0 and err_inplane < 1.0


# ---------------------------------------------------------------------------
# G3 -- a CRS-requiring stage must declare it (else silent misplacement)
# ---------------------------------------------------------------------------
CRS_REQUIRED_KEY = "crsResolutionRequired"


def case_g3():
    _hr("G3  a CRS-requiring stage must declare it (detect-and-refuse)")

    # BREAK: a coexist scene with NO stage marker. A CRS-unaware consumer (plain
    # XformCache, no resolver) has nothing to refuse on, so it silently places the
    # building at its bare local offset near the world origin -- thousands of km off.
    stage = Usd.Stage.CreateInMemory()
    stage.SetMetadata("upAxis", "Z")
    stage.SetMetadata("metersPerUnit", 1.0)
    _crs_scope(stage)
    ny = UsdGeom.Xform.Define(stage, "/World/NewYork")
    _bind(ny, "/World/CRS/UTM17N", NY_UTM17)
    _translate(stage, "/World/NewYork/MoMa", MOMA_OFFSET)
    _translate(stage, "/World/NewYork/MoMa/Corner", CORNER_OFFSET)
    corner = stage.GetPrimAtPath("/World/NewYork/MoMa/Corner")

    gt = _ecef_of_utm17(NY_UTM17[0] + MOMA_OFFSET[0] + CORNER_OFFSET[0],
                        NY_UTM17[1] + MOMA_OFFSET[1] + CORNER_OFFSET[1],
                        NY_UTM17[2] + MOMA_OFFSET[2] + CORNER_OFFSET[2])
    naive = np.array(UsdGeom.XformCache().GetLocalToWorldTransform(corner)
                     .Transform(Gf.Vec3d(0, 0, 0)))
    off = np.linalg.norm(naive - gt)

    def consumer_can_refuse(stg):
        # a conformant consumer checks the marker before rendering
        cld = stg.GetRootLayer().customLayerData or {}
        return bool(cld.get(CRS_REQUIRED_KEY))

    print(f"[break]  no stage marker; CRS-unaware consumer reads the bare local")
    print(f"[break]    offset via UsdGeom.XformCache and renders it as-is.")
    print(f"[break]    building lands {off:,.0f} m ({off/1000:,.0f} km) from truth,"
          f" silently -- no error.")
    print(f"[break]    marker present? {consumer_can_refuse(stage)}  ->"
          f" consumer has nothing to refuse on.")
    print(f"[why]    codeless schema = no missing plugin to signal; unknown crs:")
    print(f"[why]      properties are ignored, so 'wrong place' looks like 'loaded'.")

    # FIX: stamp a requires-CRS marker in customLayerData. A conformant consumer
    # detects it and refuses (or defers to a resolver) instead of misplacing.
    stage.GetRootLayer().customLayerData = {CRS_REQUIRED_KEY: True}
    refused = consumer_can_refuse(stage)
    print(f"[fix]    stamp stage customLayerData['{CRS_REQUIRED_KEY}'] = true")
    print(f"[proof]  conformant consumer now detects marker -> refuses/defers:"
          f" {refused}")
    print(f"[proof]  (with a CRS resolver the same scene resolves to 0 mm; the marker")
    print(f"[proof]   only guarantees an UNAWARE consumer fails LOUD, not silent.)")
    return off > 1e6 and refused


def main():
    print("Ill-formed 'coexist' assets: what breaks, why, and the authoring fix.")
    print("Ground truth is independent closed-form pyproj geodesy.")
    r1 = case_g1()
    r2 = case_g2()
    r3 = case_g3()
    _hr("SUMMARY (objective gates)")
    print(f"[check] G1 broken asset misplaces AND corrected asset hits geodesy: {r1}")
    print(f"[check] G2 wrong-frame misplaces AND in-plane hits geodesy:         {r2}")
    print(f"[check] G3 unmarked scene misplaces AND marker enables refusal:     {r3}")
    ok = r1 and r2 and r3
    print(f"\n[{'PASS' if ok else 'FAIL'}] all guard-rail break/fix demonstrations")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
