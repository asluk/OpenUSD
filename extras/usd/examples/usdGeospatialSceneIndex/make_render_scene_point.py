#!/usr/bin/env python3
# make_render_scene_point.py -- frame a SINGLE georef point's glyph for the
# anti-overfit renders. Sublayers a composed glyph overlay (which itself
# subLayers a non-geometric georef base) and adds an ECEF camera that looks at
# the point's resolved ECEF position from an oblique angle. The glyph is placed
# by the AUTO-INSERT scene index at render time (no baking here); we only use
# closed-form geodesy to AIM the camera, not to place the glyph.
#
# Usage: make_render_scene_point.py <glyph_overlay.usda> <out_camera_scene.usda>
#                                   <lon> <lat> <h> [frame_km]
import sys
import numpy as np
from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf

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


def main():
    src, out = sys.argv[1], sys.argv[2]
    lon, lat, h = float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
    frame_km = float(sys.argv[6]) if len(sys.argv) > 6 else 1200.0

    stage = Usd.Stage.CreateNew(out)
    stage.GetRootLayer().subLayerPaths.append(src)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    target = Gf.Vec3d(*cf_ecef(lon, lat, h))
    e, n, u = enu(lon, lat)
    # oblique eye: back off along local up + a little south/east for depth cue
    d = frame_km * 1000.0
    eye_v = np.array(target) + u * d * 0.9 - n * d * 0.35 + e * d * 0.15
    eye = Gf.Vec3d(*eye_v)
    up = Gf.Vec3d(*u)  # local vertical is "up" in frame

    cam = UsdGeom.Camera.Define(stage, "/GeoCam")
    view = Gf.Matrix4d().SetLookAt(eye, target, up)
    cam.AddTransformOp().Set(view.GetInverse())
    cam.CreateFocalLengthAttr(50.0)
    cam.CreateHorizontalApertureAttr(36.0)
    cam.CreateVerticalApertureAttr(36.0)
    cam.CreateClippingRangeAttr(Gf.Vec2f(d * 0.001, d * 20.0))

    stage.GetRootLayer().Save()
    print(f"wrote {out}  target={target}  eye={eye}")


if __name__ == "__main__":
    main()
