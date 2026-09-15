#!/usr/bin/env python3
"""
visualize_field_glyphs.py -- add a RENDERABLE visualization to a NON-GEOMETRIC
georeferenced dataset WITHOUT touching the dataset and WITHOUT duplicating any
geospatial data, using pure USD COMPOSITION (an overlay sublayer of `over` prims
that author GEOMETRY ONLY).

WHY THIS EXISTS (Aaron's design; honor it exactly)
--------------------------------------------------
A common, legitimate geospatial-USD case is a georeferenced dataset that has NO
intrinsic shape: e.g. the Earth-2 GFS t2m grid is 7,320 bare Xforms, each
carrying only

    rel     crs:binding  -> /World/CRS/WGS84_Geographic3D
    double3 crs:position  = (lon, lat, h)
    float   primvars:t2m

Such data is still useful to VISUALIZE. The RIGHT way to add a visualization is
NOT to bake marker geometry into the dataset (that mutates and bloats the asset,
and restates georef). Instead we compose:

  BASE layer     : the pristine dataset (out/earth2_georef.usda), UNTOUCHED.
  OVERLAY layer  : a NEW layer that `subLayers` the base and adds, under each
                   georef prim, a Cartesian CHILD `over` holding a marker glyph
                   (a tiny UsdGeomPoints / mesh + displayColor). The overlay
                   authors GEOMETRY ONLY -- it NEVER restates crs:binding or
                   crs:position. Georeferencing composes DOWN from the base.

HOW IT RENDERS CORRECTLY THROUGH THE SCENE INDEX (no new code path)
-------------------------------------------------------------------
Each glyph is a NON-georef Cartesian child sitting at its parent's local origin
(0,0,0). That is EXACTLY the "non-georef Cartesian subtree under a georef anchor"
case proven to resolve to 0.0 mm in src/test_anchor_injection.py: the auto-insert
scene index injects the anchor's ENU->ECEF frame, so the child (and its glyph
geometry) lands at the anchor's resolved ECEF position. No new code path -- the
same anchor-injection already exercised by the railway curve subtree.

The glyph MARKER SIZE is a STATED DISPLAY PARAMETER -- a visualization choice,
NOT a geometric property of the data (analogous to matplotlib scatter `s=`).
Default is chosen for legibility of a global grid; override with --glyph-km.

Usage:
  visualize_field_glyphs.py BASE.usda OVERLAY.usda
        [--glyph-km K] [--sparsity N] [--value-attr primvars:t2m]
        [--cmap turbo] [--glyph {points,cube}]

  BASE.usda     pristine non-geometric georef dataset (NOT modified)
  OVERLAY.usda  overlay layer written here (subLayers BASE, adds `over` glyphs)
  --glyph-km    marker size in km (display-only; default 220 for the global grid)
  --sparsity N  author a glyph on every Nth georef prim (default 1 = all)
  --value-attr  scalar primvar used for the colormap (default primvars:t2m)
  --glyph       glyph primitive: 'points' (UsdGeomPoints, round) or 'cube'
"""
import argparse
import os
import sys

import numpy as np
from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf, Vt


# ---- matplotlib-exact colormap so rendered colors match the reference plot ----
def cmap_sample(name, t):
    t = float(np.clip(t, 0.0, 1.0))
    try:
        import matplotlib
        r, g, b, _ = matplotlib.colormaps[name](t)
        return [float(r), float(g), float(b)]
    except Exception:
        # small piecewise 'turbo' fallback only if matplotlib is unavailable
        stops = np.array([0, .13, .25, .38, .5, .63, .75, .88, 1.])
        cols = np.array([[.19, .07, .23], [.27, .41, .86], [.15, .75, .9],
                         [.23, .92, .55], [.64, .99, .24], [.92, .83, .2],
                         [.98, .55, .15], [.85, .24, .09], [.48, .02, .01]])
        return [float(np.interp(t, stops, cols[:, i])) for i in range(3)]


def srgb_to_linear(c):
    """matplotlib returns sRGB-encoded display values; Storm sRGB-encodes emissive
    on output. Store the LINEARIZED color so Storm's encode round-trips back to
    the plot's sRGB value (rendered pixels match the plot)."""
    out = []
    for v in c:
        v = float(np.clip(v, 0.0, 1.0))
        out.append(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
    return out


CRS_POSITION_ATTR = "crs:position"


def find_field_prims(stage, value_attr):
    """All georef prims in the BASE: those carrying crs:position. Return
    (prim_path, value_or_None) preserving traversal order."""
    out = []
    for p in stage.Traverse():
        if p.GetAttribute(CRS_POSITION_ATTR):
            va = p.GetAttribute(value_attr)
            v = va.Get() if va else None
            out.append((p.GetPath(), v))
    return out


def author_cube_mesh(over_prim, half):
    """A small orientation-INDEPENDENT cube at local origin. Under ENU-oriented
    injection a flat quad would go edge-on on the limb/far side; a cube reads as a
    solid point from any oblique view."""
    m = UsdGeom.Mesh(over_prim) if over_prim.IsA(UsdGeom.Mesh) else UsdGeom.Mesh.Define(
        over_prim.GetStage(), over_prim.GetPath())
    s = half
    v = [(-s, -s, -s), (s, -s, -s), (s, s, -s), (-s, s, -s),
         (-s, -s, s), (s, -s, s), (s, s, s), (-s, s, s)]
    faces = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4),
             (2, 3, 7, 6), (1, 2, 6, 5), (0, 3, 7, 4)]
    m.CreatePointsAttr([Gf.Vec3f(*p) for p in v])
    m.CreateFaceVertexCountsAttr([4] * 6)
    idx = []
    for f in faces:
        idx += list(f)
    m.CreateFaceVertexIndicesAttr(idx)
    m.CreateExtentAttr([(-s, -s, -s), (s, s, s)])
    m.CreateDoubleSidedAttr(True)
    return m.GetPrim()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base")
    ap.add_argument("overlay")
    ap.add_argument("--glyph-km", type=float, default=60.0,
                    help="marker size in km (DISPLAY parameter, not geometry; "
                         "default 60 reads as DISCRETE points like a matplotlib "
                         "scatter s=, not a solid disc)")
    ap.add_argument("--sparsity", type=int, default=1,
                    help="author a glyph on every Nth georef prim (default 1)")
    ap.add_argument("--value-attr", default="primvars:t2m")
    ap.add_argument("--cmap", default="turbo")
    ap.add_argument("--glyph", choices=["points", "cube"], default="points")
    ap.add_argument("--fixed-color", default=None,
                    help="r,g,b (0-1) constant color when no scalar field exists")
    args = ap.parse_args()

    base = os.path.abspath(args.base)
    overlay = os.path.abspath(args.overlay)
    glyph_m = args.glyph_km * 1000.0
    half = glyph_m / 2.0

    base_stage = Usd.Stage.Open(base)
    field = find_field_prims(base_stage, args.value_attr)
    if not field:
        print(f"[glyphs] ERROR: no crs:position prims found in {base}", file=sys.stderr)
        return 2

    vals = [v for _, v in field if v is not None]
    have_scalar = len(vals) > 0
    if have_scalar:
        tmin, tmax = float(min(vals)), float(max(vals))
        span = (tmax - tmin) or 1.0
    fixed = None
    if args.fixed_color:
        fixed = [float(x) for x in args.fixed_color.split(",")]

    # OVERLAY stage. It SUBLAYERS the base (composition) and authors ONLY
    # geometry `over`s. It NEVER re-authors crs:binding / crs:position.
    if os.path.exists(overlay):
        os.remove(overlay)
    stage = Usd.Stage.CreateNew(overlay)
    root = stage.GetRootLayer()
    # relative sublayer path so the overlay is portable next to the base
    rel = os.path.relpath(base, os.path.dirname(overlay))
    root.subLayerPaths.append(rel)

    n = 0
    kept = []
    for i, (path, val) in enumerate(field):
        if args.sparsity > 1 and (i % args.sparsity):
            continue
        # geometry-only CHILD `over` under the (composed-in) georef prim
        glyph_path = path.AppendChild("glyph")
        over = stage.OverridePrim(glyph_path)
        if args.glyph == "cube":
            gp = author_cube_mesh(over, half)
        else:
            # UsdGeomPoints: one round point at local origin, width = glyph size.
            pts = UsdGeom.Points.Define(stage, glyph_path)
            pts.CreatePointsAttr([Gf.Vec3f(0, 0, 0)])
            pts.CreateWidthsAttr([float(glyph_m)])
            pts.SetWidthsInterpolation(UsdGeom.Tokens.vertex)
            pts.CreateExtentAttr([(-half, -half, -half), (half, half, half)])
            gp = pts.GetPrim()
        # per-glyph displayColor (geometry attr; NOT geospatial data)
        if fixed is not None:
            col = srgb_to_linear(fixed)
        elif have_scalar and val is not None:
            col = srgb_to_linear(cmap_sample(args.cmap, (float(val) - tmin) / span))
        else:
            col = srgb_to_linear([0.9, 0.2, 0.1])
        dc = UsdGeom.PrimvarsAPI(gp).CreatePrimvar(
            "displayColor", Sdf.ValueTypeNames.Color3fArray, UsdGeom.Tokens.constant)
        dc.Set(Vt.Vec3fArray([Gf.Vec3f(*col)]))
        n += 1
        kept.append(glyph_path)

    # One shared unlit emissive material (per-glyph displayColor -> emissive) so
    # glyphs read at full brightness under llvmpipe. Bound on a NEW overlay-only
    # scope; it does not touch base prims' bindings.
    mat = UsdShade.Material.Define(stage, "/GlyphMat")
    rd = UsdShade.Shader.Define(stage, "/GlyphMat/Rd")
    rd.CreateIdAttr("UsdPrimvarReader_float3")
    rd.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("displayColor")
    rout = rd.CreateOutput("result", Sdf.ValueTypeNames.Float3)
    sh = UsdShade.Shader.Define(stage, "/GlyphMat/S")
    sh.CreateIdAttr("UsdPreviewSurface")
    sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0, 0, 0))
    sh.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(rout)
    surf = sh.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    mat.CreateSurfaceOutput().ConnectToSource(surf)
    # bind the material on EACH glyph `over` (overlay-only; base untouched)
    for gpath in kept:
        gp = stage.GetPrimAtPath(gpath)
        UsdShade.MaterialBindingAPI.Apply(gp)
        UsdShade.MaterialBindingAPI(gp).Bind(mat)

    root.Save()

    print(f"[glyphs] base    = {base}  (NOT modified)")
    print(f"[glyphs] overlay = {overlay}  (subLayers base + {n} geometry-only `over`s)")
    print(f"[glyphs]   glyph = {args.glyph}  size {args.glyph_km:g} km (DISPLAY param)"
          f"  sparsity every {args.sparsity}")
    if have_scalar:
        print(f"[glyphs]   colored by {args.value_attr} in [{tmin:.1f},{tmax:.1f}] via {args.cmap}")
    else:
        print(f"[glyphs]   no scalar field; constant color")
    return 0


if __name__ == "__main__":
    sys.exit(main())
