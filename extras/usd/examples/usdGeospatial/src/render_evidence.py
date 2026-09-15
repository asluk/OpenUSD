#!/usr/bin/env python3
"""
render_evidence.py -- visual evidence that the re-encoded data is correctly
georeferenced: resolve every sample to ECEF and plot the 3D globe + a
lon/lat graticule check. If the CRS pipeline is right, the points form a
correct WGS84 ellipsoid and the t2m field sits at the right latitudes
(cold poles, warm tropics) -- without any baked sphere.
"""
import argparse, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pyproj import CRS, Transformer
from pxr import Usd, UsdGeom


def load_resolved(path, target_epsg=4978):
    stage = Usd.Stage.Open(path)
    geo = None
    fwd = None
    cache = {}
    target = CRS.from_epsg(target_epsg)
    lons, lats, xs, ys, zs, t2m = [], [], [], [], [], []
    for p in stage.Traverse():
        if not (p.IsA(UsdGeom.Xform) and p.GetAttribute("crs:position")):
            continue
        rel = p.GetRelationship("crs:binding")
        crs_prim = stage.GetPrimAtPath(rel.GetTargets()[0])
        wkt = crs_prim.GetAttribute("crs:wkt").Get()
        if wkt not in cache:
            cache[wkt] = Transformer.from_crs(CRS.from_wkt(wkt), target, always_xy=True)
        pos = p.GetAttribute("crs:position").Get()
        x, y, z = cache[wkt].transform(pos[0], pos[1], pos[2])
        lons.append(pos[0]); lats.append(pos[1])
        xs.append(x); ys.append(y); zs.append(z)
        t2m.append(p.GetAttribute("primvars:t2m").Get())
    return (np.array(a) for a in (lons, lats, xs, ys, zs, t2m))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="out/earth2_georef.usda")
    ap.add_argument("--out", default="out/evidence.png")
    args = ap.parse_args()
    lons, lats, xs, ys, zs, t2m = load_resolved(args.inp)
    c = (t2m - t2m.min()) / (np.ptp(t2m) + 1e-9)

    fig = plt.figure(figsize=(15, 5))

    # 1) ECEF 3D globe, viewed over the Atlantic
    ax = fig.add_subplot(1, 3, 1, projection="3d")
    ax.scatter(xs, ys, zs, c=c, cmap="turbo", s=4)
    ax.set_title("Resolved ECEF (EPSG:4978)\nfrom crs:position, no baked sphere")
    ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=20, azim=-40)
    ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel("Z")

    # 2) ECEF 3D globe, over the pole (shows polar flattening)
    ax2 = fig.add_subplot(1, 3, 2, projection="3d")
    ax2.scatter(xs, ys, zs, c=c, cmap="turbo", s=4)
    ax2.set_title("ECEF over N pole\n(ellipsoid, not sphere)")
    ax2.set_box_aspect((1, 1, 1)); ax2.view_init(elev=80, azim=0)

    # 3) lon/lat scatter colored by t2m -- the data is at correct geo coords
    ax3 = fig.add_subplot(1, 3, 3)
    sc = ax3.scatter(np.where(lons > 180, lons - 360, lons), lats, c=t2m,
                     cmap="turbo", s=6)
    ax3.set_title("t2m at authored lon/lat\n(cold poles, warm tropics)")
    ax3.set_xlabel("longitude"); ax3.set_ylabel("latitude")
    ax3.set_xlim(-180, 180); ax3.set_ylim(-90, 90); ax3.grid(alpha=0.3)
    fig.colorbar(sc, ax=ax3, label="t2m (K)", shrink=0.8)

    fig.tight_layout()
    fig.savefig(args.out, dpi=120)
    print(f"[render] wrote {args.out}  ({len(xs)} resolved georeferenced points)")
    # quick correctness signal: equatorial radius vs polar radius
    r = np.sqrt(xs**2 + ys**2 + zs**2)
    eq = r[np.abs(lats) < 5].mean() if (np.abs(lats) < 5).any() else float("nan")
    pol = r[np.abs(lats) > 85].mean() if (np.abs(lats) > 85).any() else float("nan")
    print(f"[check] mean radius near equator={eq:.0f} m, near pole={pol:.0f} m "
          f"(WGS84 a=6378137, b=6356752 -> flattening visible: {eq>pol})")


if __name__ == "__main__":
    main()
