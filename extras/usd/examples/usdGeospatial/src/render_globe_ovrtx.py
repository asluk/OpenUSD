#!/usr/bin/env python3
"""
render_globe_ovrtx.py -- HERO visual evidence.

Build a globe MESH whose vertices come straight from the geospatial runtime
resolution (crs:position -> ECEF via PROJ), color each vertex by t2m as unlit
emissive, add a /Render scope, and path-trace it with Omniverse RTX (ovrtx).

The point: the recognizable Earth in the render is *constructed from the
georeferenced data through the CRS pipeline* -- no hand-rolled sphere. If the
field lands correctly (cold poles, warm tropics) on a body with WGS84
flattening, the georeferencing is correct end to end.
"""
import argparse, os, sys, time
import numpy as np
from pyproj import CRS, Transformer
from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf, Vt


def turbo(t):
    t = np.clip(t, 0, 1)
    stops = np.array([0,.13,.25,.38,.5,.63,.75,.88,1.])
    cols = np.array([[.19,.07,.23],[.27,.41,.86],[.15,.75,.9],[.23,.92,.55],
                     [.64,.99,.24],[.92,.83,.2],[.98,.55,.15],[.85,.24,.09],[.48,.02,.01]])
    return np.stack([np.interp(t, stops, cols[:,i]) for i in range(3)], -1)


def resolve_grid(src_usd, target_epsg=4978):
    """Pull authored crs:position grid + t2m; resolve each to ECEF via the CRS pipeline."""
    stage = Usd.Stage.Open(src_usd)
    pts, cache = {}, {}
    target = CRS.from_epsg(target_epsg)
    for p in stage.Traverse():
        if not (p.IsA(UsdGeom.Xform) and p.GetAttribute("crs:position")):
            continue
        rel = p.GetRelationship("crs:binding")
        crs_prim = stage.GetPrimAtPath(rel.GetTargets()[0])
        wkt = crs_prim.GetAttribute("crs:wkt").Get()
        if wkt not in cache:
            cache[wkt] = Transformer.from_crs(CRS.from_wkt(wkt), target, always_xy=True)
        pos = p.GetAttribute("crs:position").Get()
        _, i, j = p.GetName().split("_")
        pts[(int(i), int(j))] = (cache[wkt].transform(pos[0], pos[1], pos[2]),
                                 p.GetAttribute("primvars:t2m").Get())
    return pts


def build_and_render(src_usd, out_usd, out_png, scale, steps):
    pts = resolve_grid(src_usd)
    ii = sorted({k[0] for k in pts}); jj = sorted({k[1] for k in pts})
    ni, nj = len(ii), len(jj)
    imap = {v: n for n, v in enumerate(ii)}; jmap = {v: n for n, v in enumerate(jj)}
    print(f"[mesh] grid {ni}x{nj} from resolved ECEF")

    P = np.zeros((ni, nj, 3)); T = np.zeros((ni, nj))
    for (i, j), (ecef, t2m) in pts.items():
        P[imap[i], jmap[j]] = ecef; T[imap[i], jmap[j]] = t2m
    Pc = P * scale

    verts, colors = [], []
    tn = (T - T.min()) / (np.ptp(T) + 1e-9)
    col = turbo(tn)
    for a in range(ni):
        for b in range(nj):
            verts.append(Gf.Vec3f(*Pc[a, b].astype(float)))
            colors.append(Gf.Vec3f(*col[a, b].astype(float)))
    counts, idx = [], []
    for a in range(ni - 1):
        for b in range(nj):
            b2 = (b + 1) % nj
            v00, v01 = a*nj+b, a*nj+b2
            v10, v11 = (a+1)*nj+b, (a+1)*nj+b2
            counts.append(4); idx += [v00, v01, v11, v10]

    stage = Usd.Stage.CreateNew(out_usd)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)   # ECEF z-up
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    mesh = UsdGeom.Mesh.Define(stage, "/World/Globe")
    mesh.CreatePointsAttr([Vt.Vec3fArray(verts)][0] if False else verts)
    mesh.CreateFaceVertexCountsAttr(counts)
    mesh.CreateFaceVertexIndicesAttr(idx)
    pv = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("displayColor",
            Sdf.ValueTypeNames.Color3fArray, UsdGeom.Tokens.vertex)
    pv.Set(Vt.Vec3fArray(colors))

    # unlit emissive: color == data
    mat = UsdShade.Material.Define(stage, "/World/M")
    sh = UsdShade.Shader.Define(stage, "/World/M/S")
    sh.CreateIdAttr("UsdPreviewSurface")
    rd = UsdShade.Shader.Define(stage, "/World/M/Rd")
    rd.CreateIdAttr("UsdPrimvarReader_float3")
    rd.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("displayColor")
    rd.CreateOutput("result", Sdf.ValueTypeNames.Float3)
    sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0,0,0))
    sh.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
        rd.ConnectableAPI(), "result")
    sh.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
    UsdShade.MaterialBindingAPI(mesh).Bind(mat)

    rmax = float(np.linalg.norm(Pc.reshape(-1,3), axis=1).max())
    cam = UsdGeom.Camera.Define(stage, "/World/Cam")
    d = rmax * 3.2
    eye = Gf.Vec3d(d*0.55, -d*0.7, d*0.45)
    m = Gf.Matrix4d(1); m.SetLookAt(eye, Gf.Vec3d(0,0,0), Gf.Vec3d(0,0,1))
    cam.AddTransformOp().Set(m.GetInverse())
    cam.CreateFocalLengthAttr(35.0)
    cam.CreateClippingRangeAttr(Gf.Vec2f(0.01, float(d*10)))

    UsdGeom.Scope.Define(stage, "/Render")
    prod = stage.DefinePrim("/Render/Product", "RenderProduct")
    prod.CreateRelationship("camera").SetTargets([cam.GetPath()])
    prod.CreateAttribute("resolution", Sdf.ValueTypeNames.Int2).Set(Gf.Vec2i(1280, 1280))
    prod.CreateAttribute("omni:rtx:background:source:type", Sdf.ValueTypeNames.Token).Set("sky")
    for vn in ("LdrColor", "HdrColor"):
        rv = stage.DefinePrim(f"/Render/{vn}", "RenderVar")
        rv.CreateAttribute("sourceName", Sdf.ValueTypeNames.String).Set(vn)
    prod.CreateRelationship("orderedVars").SetTargets(
        [Sdf.Path("/Render/LdrColor"), Sdf.Path("/Render/HdrColor")])
    stage.GetRootLayer().Save()
    print(f"[mesh] wrote {out_usd} ({len(verts)} verts, {len(counts)} quads)")

    import ovrtx
    from PIL import Image
    r = ovrtx.Renderer()
    r.open_usd(os.path.abspath(out_usd))
    t0 = time.time()
    products = None
    for _ in range(steps):
        products = r.step(render_products={"/Render/Product"}, delta_time=1/60)
    print(f"[render] {steps} steps in {time.time()-t0:.1f}s")
    for _, product in products.items():
        for frame in product.frames:
            rv = frame.render_vars
            name = "HdrColor" if "HdrColor" in rv else "LdrColor"
            with rv[name].map(device=ovrtx.Device.CPU) as var:
                arr = np.asarray(var.tensor.numpy())
            rgb = arr[..., :3].astype(np.float32)
            hi = np.percentile(rgb[rgb > 0], 99) if (rgb > 0).any() else 1.0
            rgb = np.clip(rgb/(hi+1e-8), 0, 1)
            srgb = np.where(rgb <= .0031308, 12.92*rgb, 1.055*np.power(rgb,1/2.4)-.055)
            Image.fromarray((np.clip(srgb,0,1)*255+.5).astype(np.uint8), "RGB").save(out_png)
            print(f"[render] saved {out_png}")
            return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="out/earth2_georef.usda")
    ap.add_argument("--out-usd", default="out/earth2_globe_ecef.usda")
    ap.add_argument("--out-png", default="out/globe_render.png")
    ap.add_argument("--scale", type=float, default=1e-6)
    ap.add_argument("--steps", type=int, default=48)
    a = ap.parse_args()
    build_and_render(a.inp, a.out_usd, a.out_png, a.scale, a.steps)


if __name__ == "__main__":
    main()
