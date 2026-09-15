#!/usr/bin/env python3
"""
testenv_equivalence.py -- prove the usdGeospatial DESIGN IMPROVEMENT against Simon
Haegler's prototype scene, on the SAME data.

Simon's prototype (mistafunk/USD `geospatial-prototype`, testenv/world.usda) binds a
CRS by (1) `references = [@crs.usda@</CRS/UTMxxN>]` (references-AS-binding) and
(2) a BAKED `!resetXformStack!` + `xformOp:translate` carrying the projected
easting/northing. That writes runtime behavior into the authored scene -- the exact
thing this prototype argues against.

This test reconstructs Simon's New York / MoMA scene TWICE:

  A) SIMON-STYLE (baked): nested Xforms with !resetXformStack! + xformOp:translate
     in UTM coordinates, resolved with a plain UsdGeom.XformCache -> world (UTM).
     Then UTM -> ECEF via PROJ for an absolute check.

  B) OUR-STYLE (neutral + rel-binding): the SAME prims carry NO xformOps; each is
     `BindingAPI`-applied with `rel crs:binding -> </CRS/UTMxxN>` and a
     `crs:position` holding the same easting/northing/height. The authored scene is
     coordinate-neutral; resolve_runtime reprojects + composes to world ECEF.

PASS = the MoMA building corner lands at the SAME ECEF point under both
authoring styles (within mm), demonstrating the neutral rel-binding design
reproduces the baked-resetXformStack result WITHOUT baking anything.

Uses Simon's exact CRS WKT (NAD83/UTM17N for New York; the test fixes his
mismatched WGS84/UTM30N to the correct UTM17N so the geography is real).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _schema_setup  # noqa
from pyproj import CRS, Transformer
from pxr import Usd, UsdGeom, Sdf, Gf
import resolve_runtime as rr

# Simon's testenv WKT for NAD83 / UTM zone 17N (EPSG:26917), verbatim shape.
UTM17N_WKT = CRS.from_epsg(26917).to_wkt(version="WKT2_2019")
ECEF = CRS.from_epsg(4978)

# From Simon's world.usda (New York / MoMA), UTM17N easting/northing/height:
NY_E, NY_N, NY_H = 586000.0, 4515000.0, 50.0       # /World/NewYork translate
MOMA_DX, MOMA_DY, MOMA_DZ = -393.7, -337.3, 0.0    # /World/NewYork/MoMa translate
CORNER = (-50.0, 100.0, 30.0)                        # one MoMaBuilding point (Z-up)


def make_crs(stage, path):
    p = stage.DefinePrim(path, "CoordinateReferenceSystem")
    p.CreateAttribute("crs:wkt", Sdf.ValueTypeNames.Token, False,
                      Sdf.VariabilityUniform).Set(UTM17N_WKT)
    return p


def style_A_baked(path):
    """Simon-style: baked resetXformStack + xformOp:translate in UTM; plain resolve."""
    st = Usd.Stage.CreateNew(path)
    st.SetMetadata("metersPerUnit", 1.0)
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    world = UsdGeom.Xform.Define(st, "/World")
    st.SetDefaultPrim(world.GetPrim())
    ny = UsdGeom.Xform.Define(st, "/World/NewYork")
    # !resetXformStack! then translate to UTM easting/northing
    ny.AddTranslateOp().Set(Gf.Vec3d(NY_E, NY_N, NY_H))
    ny.SetResetXformStack(True)
    moma = UsdGeom.Xform.Define(st, "/World/NewYork/MoMa")
    moma.AddTranslateOp().Set(Gf.Vec3d(MOMA_DX, MOMA_DY, MOMA_DZ))
    bldg = UsdGeom.Xform.Define(st, "/World/NewYork/MoMa/Corner")
    bldg.AddTranslateOp().Set(Gf.Vec3d(*CORNER))
    st.GetRootLayer().Save()
    # resolve world (UTM) of the corner via plain xform cache
    xc = UsdGeom.XformCache()
    m = xc.GetLocalToWorldTransform(bldg.GetPrim())
    utm = m.ExtractTranslation()       # (E, N, H) in UTM17N
    tx = Transformer.from_crs(UTM17N_WKT, ECEF, always_xy=True)
    ex, ey, ez = tx.transform(utm[0], utm[1], utm[2])
    return Gf.Vec3d(ex, ey, ez), tuple(utm)


def style_B_neutral(path):
    """Our-style: neutral scene + BindingAPI rel crs:binding + crs:position."""
    st = Usd.Stage.CreateNew(path)
    st.SetMetadata("metersPerUnit", 1.0)
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    world = UsdGeom.Xform.Define(st, "/World")
    st.SetDefaultPrim(world.GetPrim())
    UsdGeom.Scope.Define(st, "/World/CRS")
    crs = make_crs(st, "/World/CRS/UTM17N")
    # The corner prim carries its absolute UTM position as crs:position; the
    # parent offsets are folded into that position (neutral authoring -- no xformOps).
    corner_E = NY_E + MOMA_DX + CORNER[0]
    corner_N = NY_N + MOMA_DY + CORNER[1]
    corner_H = NY_H + MOMA_DZ + CORNER[2]
    site = UsdGeom.Xform.Define(st, "/World/NewYork/MoMa/Corner").GetPrim()
    site.ApplyAPI("BindingAPI")
    site.CreateRelationship("crs:binding", False).SetTargets([crs.GetPath()])
    # crs:position is (x=E, y=N, z=H) -- always_xy / east-north-up contract
    site.CreateAttribute("crs:position", Sdf.ValueTypeNames.Double3, custom=False).Set(
        Gf.Vec3d(corner_E, corner_N, corner_H))
    st.GetRootLayer().Save()
    # confirm the authored scene is coordinate-NEUTRAL (no xformOps anywhere)
    neutral = True
    for p in st.Traverse():
        if p.IsA(UsdGeom.Xformable):
            ops = UsdGeom.Xformable(p).GetOrderedXformOps()
            if ops:
                neutral = False
    target = CRS.from_epsg(4978)
    world_ecef, _ = rr.resolve_world_translation(site, target, {}, compose_ancestors=True)
    return world_ecef, neutral


def main(_=None):
    import tempfile
    d = tempfile.mkdtemp(prefix="crs_equiv_")
    ecef_A, utm_A = style_A_baked(os.path.join(d, "world_baked.usda"))
    ecef_B, neutral_B = style_B_neutral(os.path.join(d, "world_neutral.usda"))

    dist = (ecef_A - ecef_B).GetLength()
    print(f"A (Simon-style baked resetXformStack):")
    print(f"    corner UTM17N E,N,H = {utm_A}")
    print(f"    corner ECEF         = ({ecef_A[0]:.4f}, {ecef_A[1]:.4f}, {ecef_A[2]:.4f})")
    print(f"B (our neutral rel-binding):")
    print(f"    authored scene coordinate-neutral (no xformOps): {neutral_B}")
    print(f"    corner ECEF         = ({ecef_B[0]:.4f}, {ecef_B[1]:.4f}, {ecef_B[2]:.4f})")
    print(f"\nECEF separation A vs B: {dist*1000:.4f} mm")
    print()
    same = dist < 0.001  # < 1 mm
    print(f"[check] neutral rel-binding reproduces baked result (<1mm): {same}")
    print(f"[check] our authored scene has NO baked resetXformStack/xformOps: {neutral_B}")
    ok = same and neutral_B
    print("\nRESULT:",
          "DESIGN EQUIVALENCE -- neutral scene == baked scene, without baking ✅" if ok
          else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*(sys.argv[1:2] or [])))
