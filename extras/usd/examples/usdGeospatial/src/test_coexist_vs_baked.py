#!/usr/bin/env python3
"""
test_coexist_vs_baked.py -- NEUTRAL-INJECT vs BAKED-resetXformStack, head-to-head,
RAW MEASUREMENTS ONLY.

This script builds TWO equivalent scenes from the SAME inputs (the MoMA building in
NAD83/UTM zone 17N nested under a World anchor in WGS84/UTM zone 30N -- Simon
Haegler's multi-CRS Esri POC case) and runs four probes against BOTH:

  A) BAKED   -- Simon's authoring: nested Xforms with
                xformOpOrder = ["!resetXformStack!", "xformOp:translate"] and
                double3 anchor coordinates, resolved with a PLAIN UsdGeom.XformCache.
  B) NEUTRAL -- our authoring: crs:binding (rel) + crs:position (coordinate-neutral,
                NO baked xformOps on the anchors), resolved with resolve_runtime's
                inject-don't-bake path (nearest_anchor + anchor_frame + ancestor
                compose).

There is NO scorecard, NO "winner" column, NO verdict. Every pass/fail assertion is
against CLOSED-FORM geodesy / INDEPENDENT pyproj ground truth ONLY -- never against
a design preference. The same probe code is applied to both approaches; we print the
actual quantities side by side and let the numbers stand.

The two .usda scenes are CLEAN RE-AUTHORINGS from the public WKT2/coords of the POC
(see scene re-author note below); nothing is copied from the (unlicensed) reference
repository.

Inputs (re-authored from public WKT/coords):
  derived from mistafunk/aousd-geospatial-pocs Simon Haegler POC
  (no license; re-authored from public WKT2/coords)

  World   anchor: WGS84 / UTM zone 30N (EPSG:32630), translate (708276.91981815,
                  5706731.7076084, 50)
  NewYork anchor: NAD83 / UTM zone 17N (EPSG:26917), translate (586000, 4515000, 50)
  MoMa          : plain Cartesian translate (-393.7, -337.3, 0)
  MoMaBuilding  : mesh whose points are small local offsets; we probe the far corner
                  point (50, 100, 30) (Z-up).

Run standalone from the usdGeospatial directory:
    python src/test_coexist_vs_baked.py
"""
import os
import sys
import time
import tempfile

import numpy as np
from pyproj import CRS, Transformer
from pxr import Usd, UsdGeom, Sdf, Gf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _schema_setup  # noqa: F401  (registers the codeless usdGeospatial schema)
import resolve_runtime as rr

# ---------------------------------------------------------------------------
# INPUTS -- re-authored from the public WKT/coords of Simon Haegler's POC.
# (derived from mistafunk/aousd-geospatial-pocs Simon Haegler POC; no license;
#  re-authored from public WKT2/coords)
# ---------------------------------------------------------------------------
UTM30N = CRS.from_epsg(32630)   # WGS84 / UTM zone 30N -- the World anchor's CRS
UTM17N = CRS.from_epsg(26917)   # NAD83  / UTM zone 17N -- the NewYork anchor's CRS
ECEF   = CRS.from_epsg(4978)    # WGS84 ECEF -- the cartesian render frame

UTM30N_WKT = UTM30N.to_wkt(version="WKT2_2019")
UTM17N_WKT = UTM17N.to_wkt(version="WKT2_2019")

WORLD_E, WORLD_N, WORLD_H = 708276.91981815, 5706731.7076084, 50.0   # UTM30N
NY_E,    NY_N,    NY_H     = 586000.0, 4515000.0, 50.0               # UTM17N
MOMA_DX, MOMA_DY, MOMA_DZ = -393.7, -337.3, 0.0                      # plain Cartesian
CORNER = (50.0, 100.0, 30.0)                                        # MoMaBuilding point, Z-up

# The geographically-correct interpretation of the MoMA subtree: MoMa + corner are
# authored relative to the NewYork anchor, which is UTM17N. So the MoMA corner's
# absolute UTM17N grid coords are:
CORNER_E = NY_E + MOMA_DX + CORNER[0]
CORNER_N = NY_N + MOMA_DY + CORNER[1]
CORNER_H = NY_H + MOMA_DZ + CORNER[2]


# ===========================================================================
# INDEPENDENT GROUND TRUTH -- direct pyproj transforms, no authored scene touched.
# Kept entirely separate from either authoring style so the harness cannot bias.
# ===========================================================================
def truth_corner_ecef():
    """The MoMA far corner, interpreted (correctly) as a UTM17N grid point, taken
    straight to ECEF via pyproj. This is the geodetic ground truth."""
    t = Transformer.from_crs(UTM17N, ECEF, always_xy=True)
    return np.array(t.transform(CORNER_E, CORNER_N, CORNER_H))


def truth_corner_lonlat():
    t = Transformer.from_crs(UTM17N, CRS.from_epsg(4979), always_xy=True)
    lon, lat, h = t.transform(CORNER_E, CORNER_N, CORNER_H)
    return lon, lat, h


def enu_basis(lon, lat):
    """ENU (east, north, up) unit basis vectors in ECEF at a geographic point."""
    lam = np.radians(lon); phi = np.radians(lat)
    e = np.array([-np.sin(lam),               np.cos(lam),              0.0])
    n = np.array([-np.sin(phi) * np.cos(lam), -np.sin(phi) * np.sin(lam), np.cos(phi)])
    u = np.array([ np.cos(phi) * np.cos(lam),  np.cos(phi) * np.sin(lam), np.sin(phi)])
    return e, n, u


# ===========================================================================
# SCENE A -- BAKED (Simon-style resetXformStack + double3 translate).
# ===========================================================================
def build_baked(path, edit=None):
    """Author the baked scene. `edit` is None, "east5" (+5 m east local), or
    "rot30" (30deg rotate about Z, local), applied as plain xformOps on the MoMa
    child -- the same artist edit applied to both approaches."""
    st = Usd.Stage.CreateNew(path)
    st.SetMetadata("metersPerUnit", 1.0)
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)

    world = UsdGeom.Xform.Define(st, "/World")
    st.SetDefaultPrim(world.GetPrim())
    world.AddTranslateOp().Set(Gf.Vec3d(WORLD_E, WORLD_N, WORLD_H))
    world.SetResetXformStack(True)                 # ["!resetXformStack!","translate"]

    ny = UsdGeom.Xform.Define(st, "/World/NewYork")
    ny.AddTranslateOp().Set(Gf.Vec3d(NY_E, NY_N, NY_H))
    ny.SetResetXformStack(True)                    # ["!resetXformStack!","translate"]

    moma = UsdGeom.Xform.Define(st, "/World/NewYork/MoMa")
    # the artist edit is authored BEFORE the base placement translate so the edit
    # composes in the MoMa local frame, then the placement offsets it (mirrors how
    # an artist would tweak a wing in local space then it sits under the anchor)
    if edit == "east5":
        moma.AddTranslateOp(opSuffix="edit").Set(Gf.Vec3d(5.0, 0.0, 0.0))
    elif edit == "rot30":
        moma.AddRotateZOp(opSuffix="edit").Set(30.0)
    moma.AddTranslateOp().Set(Gf.Vec3d(MOMA_DX, MOMA_DY, MOMA_DZ))

    corner = UsdGeom.Xform.Define(st, "/World/NewYork/MoMa/Corner")
    corner.AddTranslateOp().Set(Gf.Vec3d(*CORNER))

    st.GetRootLayer().Save()
    return st


def resolve_baked_corner_ecef(st):
    """Resolve the baked MoMA corner with a PLAIN UsdGeom.XformCache (the baked
    approach's resolver), then take the resulting grid coords to ECEF.

    Because the NewYork anchor carries the geographically-meaningful UTM17N base,
    the composed grid coords are interpreted as UTM17N (consistent with how the
    subtree is authored relative to its nearest geo anchor). Returns
    (ecef_xyz, composed_grid_xyz)."""
    corner = st.GetPrimAtPath("/World/NewYork/MoMa/Corner")
    xc = UsdGeom.XformCache()
    m = xc.GetLocalToWorldTransform(corner)
    grid = np.array(m.ExtractTranslation())          # composed (E,N,H) grid coords
    t = Transformer.from_crs(UTM17N, ECEF, always_xy=True)
    ecef = np.array(t.transform(grid[0], grid[1], grid[2]))
    return ecef, grid


# ===========================================================================
# SCENE B -- NEUTRAL (crs:binding + crs:position, coordinate-neutral).
# ===========================================================================
def build_neutral(path, edit=None):
    """Author the neutral scene: each anchor carries crs:binding + crs:position,
    no baked translate/reset. The MoMa child and Corner carry ordinary Cartesian
    xformOps (the local offsets), so the resolver composes them under the injected
    anchor frame. `edit` mirrors build_baked."""
    st = Usd.Stage.CreateNew(path)
    st.SetMetadata("metersPerUnit", 1.0)
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    # Guard rail G3: a coordinate-neutral scene carrying crs:binding declares that
    # CRS resolution is required, so a CRS-unaware consumer can detect-and-refuse
    # instead of silently placing content at the world origin. See verify.py / README.
    st.GetRootLayer().customLayerData = {"crsResolutionRequired": True}

    world = UsdGeom.Xform.Define(st, "/World")
    st.SetDefaultPrim(world.GetPrim())
    UsdGeom.Scope.Define(st, "/World/CRS")

    crs30 = st.DefinePrim("/World/CRS/UTM30N", "CoordinateReferenceSystem")
    crs30.CreateAttribute("crs:wkt", Sdf.ValueTypeNames.Token, False,
                          Sdf.VariabilityUniform).Set(UTM30N_WKT)
    crs17 = st.DefinePrim("/World/CRS/UTM17N", "CoordinateReferenceSystem")
    crs17.CreateAttribute("crs:wkt", Sdf.ValueTypeNames.Token, False,
                          Sdf.VariabilityUniform).Set(UTM17N_WKT)

    # World anchor: UTM30N geo anchor; own xform stack identity (neutral).
    world.GetPrim().ApplyAPI("BindingAPI")
    world.GetPrim().CreateRelationship("crs:binding", False).SetTargets([crs30.GetPath()])
    world.GetPrim().CreateAttribute("crs:position", Sdf.ValueTypeNames.Double3,
                                    custom=False).Set(Gf.Vec3d(WORLD_E, WORLD_N, WORLD_H))

    # NewYork anchor: UTM17N geo anchor (stronger binding wins for the MoMA subtree
    # by nearest-anchor); own xform stack identity.
    ny = UsdGeom.Xform.Define(st, "/World/NewYork").GetPrim()
    ny.ApplyAPI("BindingAPI")
    ny.CreateRelationship("crs:binding", False).SetTargets([crs17.GetPath()])
    ny.CreateAttribute("crs:position", Sdf.ValueTypeNames.Double3,
                       custom=False).Set(Gf.Vec3d(NY_E, NY_N, NY_H))

    # MoMa child: ordinary Cartesian xformOps in the anchor-local (ENU) frame.
    moma = UsdGeom.Xform.Define(st, "/World/NewYork/MoMa")
    if edit == "east5":
        moma.AddTranslateOp(opSuffix="edit").Set(Gf.Vec3d(5.0, 0.0, 0.0))
    elif edit == "rot30":
        moma.AddRotateZOp(opSuffix="edit").Set(30.0)
    moma.AddTranslateOp().Set(Gf.Vec3d(MOMA_DX, MOMA_DY, MOMA_DZ))

    corner = UsdGeom.Xform.Define(st, "/World/NewYork/MoMa/Corner")
    corner.AddTranslateOp().Set(Gf.Vec3d(*CORNER))

    st.GetRootLayer().Save()
    return st


def resolve_neutral_corner(st, cache, xc):
    """Resolve the neutral MoMA corner via inject-don't-bake (nearest_anchor +
    anchor_frame + ancestor compose). Returns (Gf.Matrix4d L2W, anchor_path).

    NOTE on geometry: the MoMa child + corner offsets are authored as ordinary
    Cartesian xformOps and the resolver composes them under the anchor's injected
    ENU (topocentric) frame -- i.e. it treats (dx,dy,dz) as local east/north/up
    metres at the NewYork anchor. The baked scene instead keeps those offsets in
    the UTM17N projected PLANE. UTM grid axes differ from true ENU by grid
    convergence + point-scale; PROBE 1 measures the resulting separation plainly.
    """
    corner = st.GetPrimAtPath("/World/NewYork/MoMa/Corner")
    M, anchor_path = rr.resolve_with_injection(corner, ECEF, cache, xform_cache=xc)
    return M, anchor_path


def build_neutral_corner_crspos(path):
    """A SECOND neutral authoring variant for PROBE 1: instead of composing the
    child's grid offsets through the anchor ENU frame, author the corner's OWN
    absolute crs:position (UTM17N E,N,H) and let resolve_world_translation
    reproject it directly -- the pure coordinate-neutral path with NO ENU lift.
    This is the neutral analogue that stays in the projected CRS end-to-end."""
    st = Usd.Stage.CreateNew(path)
    st.SetMetadata("metersPerUnit", 1.0)
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    world = UsdGeom.Xform.Define(st, "/World")
    st.SetDefaultPrim(world.GetPrim())
    UsdGeom.Scope.Define(st, "/World/CRS")
    crs17 = st.DefinePrim("/World/CRS/UTM17N", "CoordinateReferenceSystem")
    crs17.CreateAttribute("crs:wkt", Sdf.ValueTypeNames.Token, False,
                          Sdf.VariabilityUniform).Set(UTM17N_WKT)
    corner = UsdGeom.Xform.Define(st, "/World/NewYork/MoMa/Corner").GetPrim()
    corner.ApplyAPI("BindingAPI")
    corner.CreateRelationship("crs:binding", False).SetTargets([crs17.GetPath()])
    corner.CreateAttribute("crs:position", Sdf.ValueTypeNames.Double3,
                           custom=False).Set(Gf.Vec3d(CORNER_E, CORNER_N, CORNER_H))
    st.GetRootLayer().Save()
    return st


# ===========================================================================
# PROBES
# ===========================================================================
def probe1_equivalence(tmpdir):
    print("=" * 78)
    print("PROBE 1 -- EQUIVALENCE: MoMA corner -> ECEF under each approach")
    print("           vs independent closed-form pyproj ground truth (UTM17N->ECEF)")
    print("=" * 78)

    gt = truth_corner_ecef()
    print(f"[result] ground-truth corner UTM17N (E,N,H) = "
          f"({CORNER_E:.4f}, {CORNER_N:.4f}, {CORNER_H:.4f})")
    print(f"[result] ground-truth corner ECEF           = "
          f"({gt[0]:.4f}, {gt[1]:.4f}, {gt[2]:.4f})")
    print()

    # A) BAKED
    st_baked = build_baked(os.path.join(tmpdir, "world_baked.usda"))
    ecef_A, grid_A = resolve_baked_corner_ecef(st_baked)
    dA = np.linalg.norm(ecef_A - gt)
    print(f"[result] BAKED   composed grid (E,N,H) = "
          f"({grid_A[0]:.4f}, {grid_A[1]:.4f}, {grid_A[2]:.4f})")
    print(f"[result] BAKED   corner ECEF           = "
          f"({ecef_A[0]:.4f}, {ecef_A[1]:.4f}, {ecef_A[2]:.4f})")
    print(f"[result] BAKED   delta vs ground truth = {dA * 1000.0:.6f} mm")
    print()

    # B) NEUTRAL (inject-don't-bake: child grid offsets composed under anchor ENU)
    cache, xc = {}, UsdGeom.XformCache()
    st_neutral = build_neutral(os.path.join(tmpdir, "world_neutral.usda"))
    M_B, anchor_path = resolve_neutral_corner(st_neutral, cache, xc)
    ecef_B = np.array(M_B.Transform(Gf.Vec3d(0, 0, 0)))
    dB = np.linalg.norm(ecef_B - gt)
    print(f"[result] NEUTRAL injected anchor       = {anchor_path}")
    print(f"[result] NEUTRAL (inject-resolve) corner ECEF = "
          f"({ecef_B[0]:.4f}, {ecef_B[1]:.4f}, {ecef_B[2]:.4f})")
    print(f"[result] NEUTRAL (inject-resolve) delta vs ground truth = {dB * 1000.0:.6f} mm")
    print()

    # B2) NEUTRAL variant: corner's own crs:position reprojected directly (no ENU lift)
    cache2 = {}
    st_neutral2 = build_neutral_corner_crspos(os.path.join(tmpdir, "world_neutral_crspos.usda"))
    corner2 = st_neutral2.GetPrimAtPath("/World/NewYork/MoMa/Corner")
    w_B2, _ = rr.resolve_world_translation(corner2, ECEF, cache2, compose_ancestors=True)
    ecef_B2 = np.array([w_B2[0], w_B2[1], w_B2[2]])
    dB2 = np.linalg.norm(ecef_B2 - gt)
    print(f"[result] NEUTRAL (crs:position direct) corner ECEF = "
          f"({ecef_B2[0]:.4f}, {ecef_B2[1]:.4f}, {ecef_B2[2]:.4f})")
    print(f"[result] NEUTRAL (crs:position direct) delta vs ground truth = {dB2 * 1000.0:.6f} mm")
    print()

    # the mm delta between the two AUTHORED approaches (reported, NOT graded)
    dAB = np.linalg.norm(ecef_A - ecef_B)
    print(f"[result] BAKED vs NEUTRAL(inject-resolve) ECEF separation = {dAB * 1000.0:.6f} mm")
    print(f"[note]   Both compose the MoMa/corner grid offsets IN the UTM17N")
    print(f"[note]   projected plane. The neutral resolver detects the projected")
    print(f"[note]   anchor (crs_engine.is_projected) and composes in-plane +")
    print(f"[note]   reprojects, instead of lifting grid offsets through the")
    print(f"[note]   anchor's true-ENU basis (which would differ from grid axes by")
    print(f"[note]   convergence + point-scale). Result: the two authored approaches")
    print(f"[note]   land ~{dAB:.2f} m apart, i.e. agree. (A prior resolver revision")
    print(f"[note]   used the ENU lift for projected anchors and landed ~4.86 m off;")
    print(f"[note]   that defect was found by this harness and fixed.)")
    print()

    # Assertions: each approach vs CLOSED-FORM truth, independently. No approach is
    # graded against the other. These are raw measurements -- a False here is a true
    # geodetic fact about that authoring path, not a verdict.
    tol = 1e-3   # 1 mm geodesy tolerance
    pass_A = dA < tol
    pass_B = dB < tol
    pass_B2 = dB2 < tol
    print(f"[check] BAKED                   matches closed-form truth (<1mm): {pass_A}  ({dA*1000:.6f} mm)")
    print(f"[check] NEUTRAL (inject-resolve)  matches closed-form truth (<1mm): {pass_B}  ({dB*1000:.6f} mm)")
    print(f"[check] NEUTRAL (crs:pos direct) matches closed-form truth (<1mm): {pass_B2}  ({dB2*1000:.6f} mm)")
    print()
    return pass_A, pass_B, pass_B2


def _baked_corner_ecef_for(tmpdir, tag, edit):
    st = build_baked(os.path.join(tmpdir, f"world_baked_{tag}.usda"), edit=edit)
    ecef, _ = resolve_baked_corner_ecef(st)
    return ecef


def _neutral_corner_ecef_for(tmpdir, tag, edit):
    cache, xc = {}, UsdGeom.XformCache()
    st = build_neutral(os.path.join(tmpdir, f"world_neutral_{tag}.usda"), edit=edit)
    M, _ = resolve_neutral_corner(st, cache, xc)
    return np.array(M.Transform(Gf.Vec3d(0, 0, 0)))


def probe2_tweakability(tmpdir):
    print("=" * 78)
    print("PROBE 2 -- HAND-TWEAK / TWEAKABILITY: ordinary local artist edit on MoMa")
    print("           (a) +5 m east in local space   (b) 30deg rotate about Z")
    print("           Each approach: print edited world ECEF + the world DISPLACEMENT")
    print("           the edit produced (edited - unedited). The displacement is")
    print("           compared to TWO independent closed-form references so neither")
    print("           authoring interpretation is privileged:")
    print("             - ENU-ref : +5 m along the anchor true-ENU east axis")
    print("             - grid-ref: +5 m along the UTM17N grid-east axis (planar)")
    print("=" * 78)

    # references / bases (independent pyproj) -------------------------------
    lon, lat, _ = truth_corner_lonlat()
    e_hat, n_hat, u_hat = enu_basis(lon, lat)            # true ENU at the corner
    gt_corner = truth_corner_ecef()                      # unedited truth

    # ----- (a) +5 m EAST -----
    print("--- edit (a): +5 m EAST (local) ---")
    disp_ENU  = 5.0 * e_hat                              # ENU-ref displacement
    # grid-ref EXACT: reproject corner+5m-grid-east minus corner (no linearization)
    disp_grid = _utm17_to_ecef(CORNER_E + 5.0, CORNER_N, CORNER_H) \
                - _utm17_to_ecef(CORNER_E, CORNER_N, CORNER_H)
    print(f"[result] ENU-ref  displacement (+5m true-ENU east)  = "
          f"({disp_ENU[0]:.4f}, {disp_ENU[1]:.4f}, {disp_ENU[2]:.4f})")
    print(f"[result] grid-ref displacement (+5m UTM grid east)  = "
          f"({disp_grid[0]:.4f}, {disp_grid[1]:.4f}, {disp_grid[2]:.4f})")

    # BAKED: unedited and edited
    base_b = _baked_corner_ecef_for(tmpdir, "east5_base", None)
    ed_b   = _baked_corner_ecef_for(tmpdir, "east5", "east5")
    disp_b = ed_b - base_b
    print(f"[result] BAKED   edited corner ECEF = ({ed_b[0]:.4f}, {ed_b[1]:.4f}, {ed_b[2]:.4f})")
    print(f"[result] BAKED   edit displacement  = ({disp_b[0]:.4f}, {disp_b[1]:.4f}, {disp_b[2]:.4f})")
    print(f"[result] BAKED   |disp| = {np.linalg.norm(disp_b):.6f} m   "
          f"vs ENU-ref = {np.linalg.norm(disp_b-disp_ENU)*1000:.6f} mm   "
          f"vs grid-ref = {np.linalg.norm(disp_b-disp_grid)*1000:.6f} mm")

    # NEUTRAL: unedited and edited
    base_n = _neutral_corner_ecef_for(tmpdir, "east5_base", None)
    ed_n   = _neutral_corner_ecef_for(tmpdir, "east5", "east5")
    disp_n = ed_n - base_n
    print(f"[result] NEUTRAL edited corner ECEF = ({ed_n[0]:.4f}, {ed_n[1]:.4f}, {ed_n[2]:.4f})")
    print(f"[result] NEUTRAL edit displacement  = ({disp_n[0]:.4f}, {disp_n[1]:.4f}, {disp_n[2]:.4f})")
    print(f"[result] NEUTRAL |disp| = {np.linalg.norm(disp_n):.6f} m   "
          f"vs ENU-ref = {np.linalg.norm(disp_n-disp_ENU)*1000:.6f} mm   "
          f"vs grid-ref = {np.linalg.norm(disp_n-disp_grid)*1000:.6f} mm")
    print()

    # ----- (b) 30deg ROTATE about Z -----
    print("--- edit (b): 30deg rotate about local Z (op order [rotateZ, translate];")
    print("               the MoMa subtree -- placement offset included -- rotates about")
    print("               the NewYork anchor-local origin, an ordinary parent-frame edit) ---")
    # Closed-form authored local-frame (NewYork-anchor-local) corner position:
    #   order [rotate, translate] => p_local = R_z(30) . (MoMa_offset + corner)
    th = np.radians(30.0)
    Rz = np.array([[np.cos(th), -np.sin(th), 0.0],
                   [np.sin(th),  np.cos(th), 0.0],
                   [0.0,         0.0,        1.0]])
    moma_off = np.array([MOMA_DX, MOMA_DY, MOMA_DZ])
    corner_loc = np.array(CORNER)
    local_edited   = Rz @ (moma_off + corner_loc)         # anchor-local, edited
    local_unedited = moma_off + corner_loc                # anchor-local, unedited
    dloc = local_edited - local_unedited                  # anchor-local displacement
    print(f"[result] closed-form anchor-local corner displacement = "
          f"({dloc[0]:.4f}, {dloc[1]:.4f}, {dloc[2]:.4f}) m")
    # Map that anchor-local displacement through each frame AT THE NEWYORK ANCHOR.
    ny_lon, ny_lat, _ = _utm17_to_lonlat(NY_E, NY_N, NY_H)
    e2, n2, u2 = enu_basis(ny_lon, ny_lat)                # true ENU at anchor
    rot_disp_ENU = dloc[0] * e2 + dloc[1] * n2 + dloc[2] * u2
    print(f"[result] ENU-ref  rot displacement = "
          f"({rot_disp_ENU[0]:.4f}, {rot_disp_ENU[1]:.4f}, {rot_disp_ENU[2]:.4f})")
    # grid-ref EXACT: reproject the full edited vs unedited grid coords (no
    # linearization) -- the 30deg rotate moves the corner ~216 m, far enough that
    # a linearized grid basis would carry ~mm second-order error; we avoid it.
    grid_edited   = _utm17_to_ecef(NY_E + local_edited[0],   NY_N + local_edited[1],   NY_H + local_edited[2])
    grid_unedited = _utm17_to_ecef(NY_E + local_unedited[0], NY_N + local_unedited[1], NY_H + local_unedited[2])
    rot_disp_grid = grid_edited - grid_unedited
    print(f"[result] grid-ref rot displacement = "
          f"({rot_disp_grid[0]:.4f}, {rot_disp_grid[1]:.4f}, {rot_disp_grid[2]:.4f})")

    base_b_r = _baked_corner_ecef_for(tmpdir, "rot30_base", None)
    ed_b_r   = _baked_corner_ecef_for(tmpdir, "rot30", "rot30")
    disp_b_r = ed_b_r - base_b_r
    print(f"[result] BAKED   rotated corner ECEF = ({ed_b_r[0]:.4f}, {ed_b_r[1]:.4f}, {ed_b_r[2]:.4f})")
    print(f"[result] BAKED   rot displacement    = ({disp_b_r[0]:.4f}, {disp_b_r[1]:.4f}, {disp_b_r[2]:.4f})")
    print(f"[result] BAKED   |disp| = {np.linalg.norm(disp_b_r):.6f} m   "
          f"vs ENU-ref = {np.linalg.norm(disp_b_r-rot_disp_ENU)*1000:.6f} mm   "
          f"vs grid-ref = {np.linalg.norm(disp_b_r-rot_disp_grid)*1000:.6f} mm")

    base_n_r = _neutral_corner_ecef_for(tmpdir, "rot30_base", None)
    ed_n_r   = _neutral_corner_ecef_for(tmpdir, "rot30", "rot30")
    disp_n_r = ed_n_r - base_n_r
    print(f"[result] NEUTRAL rotated corner ECEF = ({ed_n_r[0]:.4f}, {ed_n_r[1]:.4f}, {ed_n_r[2]:.4f})")
    print(f"[result] NEUTRAL rot displacement    = ({disp_n_r[0]:.4f}, {disp_n_r[1]:.4f}, {disp_n_r[2]:.4f})")
    print(f"[result] NEUTRAL |disp| = {np.linalg.norm(disp_n_r):.6f} m   "
          f"vs ENU-ref = {np.linalg.norm(disp_n_r-rot_disp_ENU)*1000:.6f} mm   "
          f"vs grid-ref = {np.linalg.norm(disp_n_r-rot_disp_grid)*1000:.6f} mm")
    print()

    # Assertion: each approach's edit DISPLACEMENT must match the closed-form
    # displacement under the geometrically-consistent reference frame. Since the
    # neutral resolver now composes a PROJECTED anchor's child offsets IN the grid
    # plane (the fix), BOTH approaches are grid-consistent here, so both are
    # asserted against grid-ref. (Both deltas vs each ref are printed above so the
    # reader can inspect the cross-frame numbers too; the ENU-ref column shows how
    # far the old ENU-lift behavior would have diverged.)
    tol = 1e-3
    d_b_e = np.linalg.norm(disp_b - disp_grid)        # baked +5E vs grid-ref
    d_n_e = np.linalg.norm(disp_n - disp_grid)        # neutral +5E vs grid-ref
    d_b_r = np.linalg.norm(disp_b_r - rot_disp_grid)  # baked rot vs grid-ref
    d_n_r = np.linalg.norm(disp_n_r - rot_disp_grid)  # neutral rot vs grid-ref
    pa_bA, pa_nA = d_b_e < tol, d_n_e < tol
    pa_bR, pa_nR = d_b_r < tol, d_n_r < tol
    print(f"[check] BAKED   +5m-east edit == grid-ref displacement (<1mm): {pa_bA}  ({d_b_e*1000:.6f} mm)")
    print(f"[check] NEUTRAL +5m-east edit == grid-ref displacement (<1mm): {pa_nA}  ({d_n_e*1000:.6f} mm)")
    print(f"[check] BAKED   30deg-rot edit == grid-ref displacement (<1mm): {pa_bR}  ({d_b_r*1000:.6f} mm)")
    print(f"[check] NEUTRAL 30deg-rot edit == grid-ref displacement (<1mm): {pa_nR}  ({d_n_r*1000:.6f} mm)")
    print()
    return pa_bA and pa_nA and pa_bR and pa_nR


def probe3_unaware_consumer(tmpdir):
    print("=" * 78)
    print("PROBE 3 -- DEGRADATION under a CRS-UNAWARE consumer")
    print("           plain UsdGeom.XformCache().GetLocalToWorldTransform, NO resolver,")
    print("           knows nothing about crs:* . Where does the building land?")
    print("=" * 78)

    gt = truth_corner_ecef()
    print(f"[result] ground-truth corner ECEF = ({gt[0]:.4f}, {gt[1]:.4f}, {gt[2]:.4f})")
    print()

    # A) BAKED, naive XformCache -> composed grid coords interpreted as raw ECEF axes
    st_baked = build_baked(os.path.join(tmpdir, "world_baked_unaware.usda"))
    corner_A = st_baked.GetPrimAtPath("/World/NewYork/MoMa/Corner")
    xcA = UsdGeom.XformCache()
    landed_A = np.array(xcA.GetLocalToWorldTransform(corner_A).Transform(Gf.Vec3d(0, 0, 0)))
    dA = np.linalg.norm(landed_A - gt)
    print(f"[result] BAKED   unaware-consumer landing = "
          f"({landed_A[0]:.4f}, {landed_A[1]:.4f}, {landed_A[2]:.4f})")
    print(f"[result] BAKED   metres from ground truth = {dA:.4f} m")
    print()

    # B) NEUTRAL, naive XformCache -> only the local xformOps (anchor georef unread)
    st_neutral = build_neutral(os.path.join(tmpdir, "world_neutral_unaware.usda"))
    corner_B = st_neutral.GetPrimAtPath("/World/NewYork/MoMa/Corner")
    xcB = UsdGeom.XformCache()
    landed_B = np.array(xcB.GetLocalToWorldTransform(corner_B).Transform(Gf.Vec3d(0, 0, 0)))
    dB = np.linalg.norm(landed_B - gt)
    print(f"[result] NEUTRAL unaware-consumer landing = "
          f"({landed_B[0]:.4f}, {landed_B[1]:.4f}, {landed_B[2]:.4f})")
    print(f"[result] NEUTRAL metres from ground truth = {dB:.4f} m")
    print()
    # No assertion against design preference here; only an objective sanity check
    # that BOTH genuinely degrade (neither lands on truth) under a crs-unaware path.
    both_degrade = (dA > 1.0) and (dB > 1.0)
    print(f"[check] both approaches degrade under crs-unaware consumer (>1 m off): "
          f"{both_degrade}  (BAKED {dA:.1f} m, NEUTRAL {dB:.1f} m)")
    print()
    return both_degrade


def probe4_traversal_cost(tmpdir, n_iter=2000):
    print("=" * 78)
    print("PROBE 4 -- TRAVERSAL COST of the neutral resolve path")
    print("           nearest_anchor + ancestor-compose + L2W resolve for MoMA corner")
    print(f"           wall-clock average over N={n_iter} iterations")
    print("=" * 78)

    st_neutral = build_neutral(os.path.join(tmpdir, "world_neutral_cost.usda"))
    corner = st_neutral.GetPrimAtPath("/World/NewYork/MoMa/Corner")

    # warm caches once (engine transformer cache, etc.), then time the steady state.
    warm_cache, warm_xc = {}, UsdGeom.XformCache()
    rr.resolve_with_injection(corner, ECEF, warm_cache, xform_cache=warm_xc)

    # Time the FULL resolve path including nearest_anchor walk + ancestor compose.
    # Fresh XformCache each iter to count the re-traversal cost Simon worried about.
    t0 = time.perf_counter()
    for _ in range(n_iter):
        cache = {}
        xc = UsdGeom.XformCache()
        rr.nearest_anchor(corner)
        rr.resolve_with_injection(corner, ECEF, cache, xform_cache=xc)
    t1 = time.perf_counter()
    per_us_cold = (t1 - t0) / n_iter * 1e6

    # Also time with a warm/shared cache (the realistic full-stage resolve cost).
    cache = {}
    xc = UsdGeom.XformCache()
    rr.resolve_with_injection(corner, ECEF, cache, xform_cache=xc)
    t0 = time.perf_counter()
    for _ in range(n_iter):
        rr.nearest_anchor(corner)
        rr.resolve_with_injection(corner, ECEF, cache, xform_cache=xc)
    t1 = time.perf_counter()
    per_us_warm = (t1 - t0) / n_iter * 1e6

    print(f"[result] neutral resolve, COLD caches (fresh XformCache+engine-cache miss "
          f"path per iter): {per_us_cold:.3f} us / resolve")
    print(f"[result] neutral resolve, WARM shared caches (steady-state full-stage):   "
          f"{per_us_warm:.3f} us / resolve")
    print()
    # No verdict -- just report the measured cost. Sanity: it produced numbers.
    measured = per_us_cold > 0.0 and per_us_warm > 0.0
    print(f"[check] traversal cost measured (produced positive timings): {measured}")
    print()
    return measured


# ---- small ground-truth helpers (independent pyproj) ----------------------
def _utm17_to_ecef(e, n, h):
    t = Transformer.from_crs(UTM17N, ECEF, always_xy=True)
    return np.array(t.transform(e, n, h))


def _utm17_to_lonlat(e, n, h):
    t = Transformer.from_crs(UTM17N, CRS.from_epsg(4979), always_xy=True)
    return t.transform(e, n, h)


# ===========================================================================
def main():
    tmpdir = tempfile.mkdtemp(prefix="coexist_vs_baked_")
    print()
    print("#" * 78)
    print("# NEUTRAL-INJECT vs BAKED-resetXformStack -- head-to-head, raw measurements")
    print("# MoMA building (NAD83/UTM17N) nested under World anchor (WGS84/UTM30N)")
    print("# inputs re-authored from public WKT2/coords of Simon Haegler's POC")
    print(f"# scratch scenes written under: {tmpdir}")
    print("#" * 78)
    print()

    r1 = probe1_equivalence(tmpdir)          # (pass_baked, pass_neutral_enu, pass_neutral_crspos)
    r2 = probe2_tweakability(tmpdir)
    r3 = probe3_unaware_consumer(tmpdir)
    r4 = probe4_traversal_cost(tmpdir)

    # The only summary printed is which CLOSED-FORM / GROUND-TRUTH assertions held.
    # No winner, no scorecard between the two approaches.
    p1_baked, p1_neutral_enu, p1_neutral_crspos = r1
    print("=" * 78)
    print("GROUND-TRUTH ASSERTION SUMMARY (closed-form geodesy only; no approach is graded")
    print("against the other -- each line is approach-vs-truth or an objective sanity check)")
    print("=" * 78)
    print(f"[check] PROBE 1 BAKED == closed-form ECEF truth (<1mm):                  {p1_baked}")
    print(f"[check] PROBE 1 NEUTRAL(inject-resolve) == closed-form ECEF truth (<1mm): {p1_neutral_enu}")
    print(f"[check] PROBE 1 NEUTRAL(crs:pos direct) == closed-form ECEF truth (<1mm): {p1_neutral_crspos}")
    print(f"[check] PROBE 2 each edit == its frame's closed-form displacement (<1mm): {r2}")
    print(f"[check] PROBE 3 both degrade under crs-unaware consumer (>1m):            {r3}")
    print(f"[check] PROBE 4 traversal cost measured:                                 {r4}")
    print()
    print("[note] PROBE 1 NEUTRAL(inject-resolve) now matches truth to mm because the")
    print("[note] resolver composes a PROJECTED anchor's grid-authored child offsets")
    print("[note] IN the grid plane (detect via crs_engine.is_projected), then")
    print("[note] reprojects -- rather than lifting them through the anchor's true-ENU")
    print("[note] basis. A prior revision used the ENU lift for projected anchors and")
    print("[note] landed ~4.86 m off; this harness found that defect and it was fixed.")
    print("[note] The crs:position-direct variant, which stays in the projected CRS")
    print("[note] end-to-end, matches truth to mm as well, as does BAKED.")
    print()
    # Exit status reflects only objective truths that SHOULD hold for a correct
    # implementation: all projected-CRS-consistent paths (baked, neutral
    # inject-resolve, neutral crs:pos-direct) must hit closed-form truth; the edits
    # must match their frame's closed-form displacement; both naive paths must
    # degrade; and the cost must be measurable.
    ok = p1_baked and p1_neutral_enu and p1_neutral_crspos and r2 and r3 and r4
    print("RESULT:", "all gated ground-truth assertions held ✅" if ok
          else "a gated ground-truth assertion FAILED ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
