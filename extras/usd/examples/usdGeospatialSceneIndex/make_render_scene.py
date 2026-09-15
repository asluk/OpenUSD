#!/usr/bin/env python3
# make_render_scene.py -- build a small stage that references the railway georef
# scene and adds a perspective camera framed on the ECEF anchor centroid, so a
# renderer (usdrecord / usdview) that RESOLVES the geospatial binding shows the
# railway in frame. No geospatial baking; the camera is just placed in ECEF.
#
# Usage: make_render_scene.py <railway_georef.usda> <out_camera_scene.usda>
import sys
from pxr import Usd, UsdGeom, Gf, Sdf

# ECEF anchor centroid of the railway (from the oracle) + a scene radius.
CENTER = Gf.Vec3d(3742658.1003070897, 674070.6852125883, 5103320.545506689)
RADIUS = 600.0  # railway extent is a few hundred metres

def main():
    src, out = sys.argv[1], sys.argv[2]
    import os
    src = os.path.abspath(src)
    # Sublayer the georef content so ALL its prims compose at their authored
    # (absolute) paths -- keeps crs:binding relationship targets intact -- and
    # add the camera/light in the root layer alongside.
    stage = Usd.Stage.CreateNew(out)
    stage.GetRootLayer().subLayerPaths.append(src)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    cam = UsdGeom.Camera.Define(stage, "/GeoCam")
    # camera: place it backed off along the local "up" (radial) + oblique so the
    # curves are visible. up ~ normalize(center) in ECEF.
    up = CENTER.GetNormalized()
    # an oblique offset direction not parallel to up
    side = Gf.Cross(up, Gf.Vec3d(0, 0, 1)).GetNormalized()
    fwd = Gf.Cross(side, up).GetNormalized()
    dist = RADIUS * 3.0 + 300.0
    eye = CENTER + (up * 0.6 + fwd * 0.8).GetNormalized() * dist

    # build look-at matrix (camera looks down -Z in its own space)
    view = Gf.Matrix4d().SetLookAt(eye, CENTER, up)
    xf = view.GetInverse()
    cam.AddTransformOp().Set(xf)
    cam.CreateFocalLengthAttr(24.0)
    cam.CreateHorizontalApertureAttr(24.0)
    cam.CreateVerticalApertureAttr(18.0)
    cam.CreateClippingRangeAttr(Gf.Vec2f(dist * 0.01, dist * 10.0))

    # a distant light so unlit geometry is visible
    from pxr import UsdLux
    dl = UsdLux.DistantLight.Define(stage, "/Key")
    dl.CreateIntensityAttr(3000.0)

    stage.GetRootLayer().Save()
    print("wrote", out, "camera /GeoCam eye=", eye)

if __name__ == "__main__":
    main()
