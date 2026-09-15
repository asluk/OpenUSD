#!/usr/bin/env python3
# probe_autoinsert.py -- confirm auto-insertion works with NO SetStage and NO
# hand-built chain: open the stage, build a UsdImagingGL.Engine (the SAME engine
# usdview uses), and read the resolved world xform of the geo prims out of the
# engine's terminal scene index. If the crs: data flowed through Hydra and our
# auto-inserted scene index resolved it, the anchor xform == ECEF oracle.
#
# Usage: probe_autoinsert.py <stage.usda> <primPath>
import sys
# NOTE: only Usd/UsdImagingGL/Gf/Sdf are needed here. (Earlier revisions also
# imported Hd/HdGp, which are not wrapped for Python in every USD build and would
# raise ImportError before this probe could run.)
from pxr import Usd, UsdImagingGL, Gf, Sdf  # noqa

def main():
    stagePath, primPath = sys.argv[1], sys.argv[2]
    stage = Usd.Stage.Open(stagePath)
    assert stage, f"cannot open {stagePath}"

    engine = UsdImagingGL.Engine()
    # The engine constructs its scene-index chain internally, auto-inserting
    # registered scene indices for the active renderer (RegisterSceneIndexForRenderer)
    # -- exactly the usdview path. Ask it for the terminal scene index.
    si = engine.GetTerminalSceneIndex() if hasattr(engine, "GetTerminalSceneIndex") else None
    if si is None:
        print("NO GetTerminalSceneIndex on this engine build")
        return 2
    # Need to prime the scene index by setting the root/stage on the engine's
    # imaging delegate. UsdImagingGL.Engine handles this when we render, but for
    # a pure xform pull we can use the scene index directly once populated.
    from pxr import UsdImaging
    prim = si.GetPrim(Sdf.Path(primPath))
    print("primType:", prim.primType)
    xf = None
    if prim.dataSource:
        ds = prim.dataSource.Get("xform")
        if ds:
            m = ds.Get("matrix")
            if m:
                xf = m.GetTypedValue(0.0)
    print("xform:", xf)
    if xf is not None:
        t = xf.ExtractTranslation()
        print(f"translation: ({t[0]:.4f}, {t[1]:.4f}, {t[2]:.4f})  |t|={t.GetLength():.1f} m")

if __name__ == "__main__":
    sys.exit(main() or 0)
