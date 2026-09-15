#!/usr/bin/env python3
# make_render_scene_topdown.py -- like make_render_scene.py, but frames the
# ground (map tiles) close to NADIR so the textured tiles read face-on, matching
# the top-down matplotlib plot docs/railway_render.png. Camera is still placed in
# ECEF only; no geospatial baking. The georeferencing comes from the auto-inserted
# scene index at render time.
#
# FIX 1 (whole-scene framing): the plot fig_railway_render is a TOP-DOWN plan
# view showing ALL tile ground planes + ALL rail curves at equal aspect over the
# full footprint. This builder now looks at the CENTROID of the full geometry
# (not the anchor origin) and backs the camera off / widens the frustum so every
# tile and rail is in frame -- the renderer's version of railway_render.png.
#
# The full local-ENU footprint of the railway (tiles + rails) is about
#   E in [-2129, +789] m  (span ~2918 m),  N in [-2121, +326] m (span ~2446 m),
# centred at roughly (E=-670, N=-898) relative to the anchor. We derive that
# footprint from the renderable stage at build time so the framing stays exact.
#
# Usage: make_render_scene_topdown.py <renderable.usda> <out_camera_scene.usda>
import sys, os
import numpy as np
from pxr import Usd, UsdGeom, UsdLux, Gf

# ECEF anchor centroid of the railway (oracle /RootGeoReference translation).
CENTER = Gf.Vec3d(3742658.1003070897, 674070.6852125883, 5103320.545506689)

# Full local-ENU footprint of the railway (ALL tiles + ALL rail curves), taken
# from the SAME resolver that draws the plot (render_figures._railway_local_geometry
# via resolve_runtime), so the camera coverage is IDENTICAL to docs/railway_render.png.
# E in [-2128.83, +789.35] m, N in [-2120.78, +325.56] m about the anchor.
FOOTPRINT_EN = (-2128.83, 789.35, -2120.78, 325.56)


def main():
    src, out = os.path.abspath(sys.argv[1]), sys.argv[2]

    emin, emax, nmin, nmax = FOOTPRINT_EN
    ecx, ncy = 0.5 * (emin + emax), 0.5 * (nmin + nmax)
    span_e, span_n = (emax - emin), (nmax - nmin)
    print(f"[topdown] footprint E[{emin:.0f},{emax:.0f}] N[{nmin:.0f},{nmax:.0f}] "
          f"centroid E={ecx:.0f} N={ncy:.0f}")

    stage = Usd.Stage.CreateNew(out)
    stage.GetRootLayer().subLayerPaths.append(src)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    up = CENTER.GetNormalized()                       # ENU up == ECEF radial
    east = Gf.Cross(Gf.Vec3d(0, 0, 1), up).GetNormalized()
    north = Gf.Cross(up, east).GetNormalized()

    # look-at target: the CENTROID of the full geometry (not the anchor origin),
    # so the whole railway network is centred in frame like the plot.
    target = CENTER + east * ecx + north * ncy

    # frame the full footprint (+margin). half-extent we must cover:
    margin = 1.15
    # keep equal aspect (square apertures) so E and N read at equal scale like
    # the plot's ax.set_aspect("equal"); cover the larger of the two spans.
    half = 0.5 * margin * max(span_e, span_n)

    cam = UsdGeom.Camera.Define(stage, "/GeoCam")
    # back the camera off far enough that a symmetric frustum at focal/aperture
    # below covers +/- half at the target plane. With focal=f and aperture=ap,
    # the half-FOV extent at distance d is  d * (ap/2) / f. Solve for d.
    focal = 24.0
    aperture = 24.0
    d = half * focal / (aperture / 2.0)               # distance so half fits
    # near-nadir: mostly straight down (along +up), with a slight north tilt so
    # rails gain a little depth and don't perfectly alias into the tile plane.
    eye = target + up * d + north * (d * 0.06)
    view = Gf.Matrix4d().SetLookAt(eye, target, north)
    cam.AddTransformOp().Set(view.GetInverse())
    cam.CreateFocalLengthAttr(focal)
    cam.CreateHorizontalApertureAttr(aperture)
    cam.CreateVerticalApertureAttr(aperture)          # square -> equal aspect
    cam.CreateClippingRangeAttr(Gf.Vec2f(d * 0.01, d * 10.0))
    print(f"[topdown] half={half:.0f} d={d:.0f} eye={eye}")

    # bright key light; rely on the emissive-driven tile material (set by
    # make_renderable_railway.py) for full-brightness map imagery. NOTE: a
    # DomeLight crashes Storm under llvmpipe on this host, so we avoid it.
    dl = UsdLux.DistantLight.Define(stage, "/Key")
    dl.CreateIntensityAttr(3000.0)
    dl.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(eye, target, north).GetInverse())

    stage.GetRootLayer().Save()
    print("wrote", out, "eye=", eye)


if __name__ == "__main__":
    main()
