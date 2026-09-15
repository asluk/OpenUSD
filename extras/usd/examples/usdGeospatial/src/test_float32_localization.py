#!/usr/bin/env python3
"""
test_float32_localization.py -- the C-05 precision proof, free from the
anchor-injection model.

Why it matters: ECEF coordinates near Earth's surface are ~6.4e6 m. Stored as
float32 (the GPU/runtime norm for vertex data) the representable spacing at that
magnitude is ~0.5 m -- so an asset modelled in absolute ECEF float32 JITTERS at
the half-metre level, and two nearby vertices can collapse to the same float.

The inject-don't-bake / anchor model fixes this for free: the large magnitude
lives in the DOUBLE-precision injected anchor frame (~6.4e6 m), while the asset's
own vertices are small float32 LOCAL offsets (metres from the anchor), where
float32 spacing is ~1e-6 m. Same final world position, ~6 orders of magnitude
better local precision.

Assertions (teeth):
  C1: absolute-float32 round-trip of a surface point loses >> 1 mm (it must, by
      float32 spacing at 6.4e6 m) -- quantifies the problem.
  C2: anchor(double) + local-offset(float32) reconstructs the SAME point to
      sub-millimetre -- quantifies the fix.
  C3: the fix is >= 1e5x better than absolute float32 at this magnitude.
"""
import sys
import numpy as np
from pyproj import CRS
from pxr import Usd, UsdGeom, Sdf, Gf

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import _schema_setup  # noqa
import resolve_runtime as rr

GEO = CRS.from_epsg(4979)
ECEF = CRS.from_epsg(4978)
LON, LAT, H = -73.985656, 40.748817, 0.0


def author(out):
    stage = Usd.Stage.CreateNew(out)
    w = UsdGeom.Xform.Define(stage, "/World"); stage.SetDefaultPrim(w.GetPrim())
    UsdGeom.Scope.Define(stage, "/World/CRS")
    crs_prim = stage.DefinePrim("/World/CRS/WGS84_Geographic3D",
                                "CoordinateReferenceSystem")
    crs_prim.CreateAttribute("crs:wkt", Sdf.ValueTypeNames.Token, False,
                             Sdf.VariabilityUniform).Set(GEO.to_wkt(version="WKT2_2019"))
    anchor = UsdGeom.Xform.Define(stage, "/World/Anchor").GetPrim()
    anchor.CreateRelationship("crs:binding", False).SetTargets([crs_prim.GetPath()])
    anchor.CreateAttribute("crs:position", Sdf.ValueTypeNames.Double3, False) \
          .Set(Gf.Vec3d(LON, LAT, H))
    return stage, anchor


def main(out="out/_test_float32_localization.usda"):
    stage, anchor = author(out)
    cache = {}
    Mframe, _ = rr.anchor_frame(anchor, ECEF, cache)

    # A detail vertex 12.345 m east, 7.891 m north, 3.210 m up of the anchor.
    local = np.array([12.345, 7.891, 3.210])
    world_double = np.array(Mframe.Transform(Gf.Vec3d(*local)))

    # (C1) absolute float32: store the world point itself as float32.
    abs_f32 = world_double.astype(np.float32).astype(np.float64)
    err_abs = np.linalg.norm(abs_f32 - world_double)

    # (C2) anchor(double) + local-offset(float32): only the small local offset is
    # float32; the anchor frame stays double.
    local_f32 = local.astype(np.float32).astype(np.float64)
    world_local = np.array(Mframe.Transform(Gf.Vec3d(*local_f32)))
    err_local = np.linalg.norm(world_local - world_double)

    print(f"[author] {out}")
    print(f"  anchor magnitude (ECEF)         = {np.linalg.norm(world_double):.1f} m")
    print(f"  detail vertex local offset      = {tuple(float(v) for v in local)} m")
    print()
    print(f"[C1] absolute-float32 error        = {err_abs*1000:.4f} mm  (float32 @ 6.4e6 m)")
    print(f"[C2] anchor(double)+local(float32) = {err_local*1000:.6f} mm")
    ratio = err_abs / max(err_local, 1e-12)
    print(f"[C3] improvement factor            = {ratio:.3e}x")

    c1 = err_abs > 1e-3            # absolute float32 loses >> 1 mm (the problem)
    c2 = err_local < 1e-3          # localized float32 keeps sub-mm (the fix)
    c3 = ratio > 1e5              # orders-of-magnitude better
    ok = c1 and c2 and c3
    print()
    print(f"[check] C1 absolute float32 loses precision (>1 mm):  {c1}")
    print(f"[check] C2 localized float32 keeps sub-mm:            {c2}")
    print(f"[check] C3 localization >= 1e5x better:               {c3}")
    print("\nRESULT:", "FLOAT32 LOCALIZATION (C-05) DEMONSTRATED ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*(sys.argv[1:2] or [])))
