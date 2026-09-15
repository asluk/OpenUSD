#!/usr/bin/env python3
# make_render_scene_globe.py -- sublayer the renderable Earth-2 globe (markers
# under georef points) and add an ECEF camera looking at Earth center (origin),
# so the auto-inserted scene index places every marker at its resolved ECEF
# position and the globe assembles at render time. No baking.
#
# FIX 2 (cross-visualizer parity): the reference plot fig_globe (docs/globe.png)
# is a matplotlib 3D scatter with cmap="turbo", dark bg #0b0e14, and
# ax.view_init(elev=18, azim=-55), box aspect 1:1:1. To PROVE one runtime feeds
# multiple visualizers with the SAME resolved result, this camera reproduces the
# SAME viewpoint: matplotlib's view_init(elev,azim) looks at the data origin from
# eye direction (cos e cos a, cos e sin a, sin e). fig_globe's data axes ARE the
# ECEF axes (xs,ys,zs come straight from resolve_stage_ecef in EPSG:4978), so the
# same direction is used directly in ECEF. Result: same hemisphere/orientation.
#
# Usage: make_render_scene_globe.py <globe_renderable.usda> <out_camera_scene.usda>
import sys, os
import numpy as np
from pxr import Usd, UsdGeom, UsdLux, UsdShade, Sdf, Gf, Vt

R = 6.371e6  # Earth radius (m); markers resolve onto the WGS84 ellipsoid in ECEF

# Match fig_globe exactly.
ELEV = 18.0
AZIM = -55.0
BG = (0x0b / 255.0, 0x0e / 255.0, 0x14 / 255.0)  # #0b0e14 dark bg


def main():
    src, out = os.path.abspath(sys.argv[1]), sys.argv[2]
    stage = Usd.Stage.CreateNew(out)
    stage.GetRootLayer().subLayerPaths.append(src)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)  # ECEF z-up (through poles)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    # matplotlib view_init(elev,azim) eye direction, applied in ECEF (data==ECEF)
    e, a = np.radians(ELEV), np.radians(AZIM)
    dir_ecef = Gf.Vec3d(np.cos(e) * np.cos(a),
                        np.cos(e) * np.sin(a),
                        np.sin(e)).GetNormalized()

    cam = UsdGeom.Camera.Define(stage, "/GeoCam")
    d = R * 8.0
    eye = dir_ecef * d
    # world-up: use ECEF +Z projected off the view dir so the pole sits "up" in
    # image like the matplotlib default (its z axis points up on screen).
    view = Gf.Matrix4d().SetLookAt(eye, Gf.Vec3d(0, 0, 0), Gf.Vec3d(0, 0, 1))
    cam.AddTransformOp().Set(view.GetInverse())
    cam.CreateFocalLengthAttr(85.0)
    cam.CreateHorizontalApertureAttr(24.0)
    cam.CreateVerticalApertureAttr(24.0)     # square -> box aspect 1:1
    cam.CreateClippingRangeAttr(Gf.Vec2f(d * 0.01, d * 10.0))

    # Dark background matching globe.png (#0b0e14): a large backdrop quad far
    # behind the globe, facing the camera, with black surface. NOTE: under Storm
    # + llvmpipe on this host there is an additive clear/ambient floor of about
    # (25,25,25) in the encoded PNG, so a pure-black backdrop reads as a very
    # dark neutral grey -- the closest the renderer allows to #0b0e14 (11,14,20).
    # Emissive only ADDS, so it cannot push below that floor; black is darkest.
    back = UsdGeom.Mesh.Define(stage, "/Backdrop")
    bd = R * 40.0            # far behind the globe
    half = R * 60.0          # large enough to fill frame
    # place perpendicular to view dir, centred behind origin along -eye dir
    c = dir_ecef * (-bd)
    # basis in the backdrop plane
    up0 = Gf.Vec3d(0, 0, 1)
    right = Gf.Cross(up0, dir_ecef).GetNormalized()
    upv = Gf.Cross(dir_ecef, right).GetNormalized()
    corners = [c - right * half - upv * half,
               c - right * half + upv * half,
               c + right * half + upv * half,
               c + right * half - upv * half]
    back.CreatePointsAttr([Gf.Vec3f(*p) for p in corners])
    back.CreateFaceVertexCountsAttr([4])
    back.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    back.CreateDoubleSidedAttr(True)
    back.CreateExtentAttr([(-half * 2, -half * 2, -bd * 2), (half * 2, half * 2, bd * 2)])
    bmat = UsdShade.Material.Define(stage, "/BackMat")
    bsh = UsdShade.Shader.Define(stage, "/BackMat/S")
    bsh.CreateIdAttr("UsdPreviewSurface")
    bsh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0, 0, 0))
    bsh.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0, 0, 0))
    bsh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(1.0)
    bsurf = bsh.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    bmat.CreateSurfaceOutput().ConnectToSource(bsurf)
    UsdShade.MaterialBindingAPI.Apply(back.GetPrim())
    UsdShade.MaterialBindingAPI(back.GetPrim()).Bind(bmat)

    stage.GetRootLayer().Save()
    print(f"wrote {out}  eye={eye}  dir={dir_ecef}  bg=#0b0e14")


if __name__ == "__main__":
    main()
