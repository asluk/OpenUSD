#!/usr/bin/env python3
"""
dump_oracle.py -- materialize the parity dataset stages to .usda AND dump the
Python reference runtime's resolved world transforms, so the C++ GeoResolver can
be checked against BOTH:
  (1) closed-form WGS84 geodesy   (independent oracle, non-circular)
  (2) the exact Python runtime output  (implementation parity)

Outputs (into out/parity/):
  <dataset>.usda                       authored CRS-neutral stage
  oracle.tsv                           one row per resolved prim:
     stagePath \t primPath \t kind \t gtX \t gtY \t gtZ \t \
     pyX \t pyY \t pyZ \t [for injection rows: py 4x4 matrix flattened]

Datasets mirror generalization_suite.py: 4 geographic Earth-2-like points + the
5 projected benchmarks, authored as point prims; PLUS the real railway anchor+
curve subtree (out/railway_georef.usda) for the inject-don't-bake / orientation
parity (the hardest case).
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "usdGeospatial", "src"))
import _schema_setup  # noqa
import resolve_runtime as rr
from pyproj import CRS, Transformer
from pxr import Usd, UsdGeom, Sdf, Gf

ECEF = CRS.from_epsg(4978)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "parity")
os.makedirs(OUT, exist_ok=True)

_A=6378137.0; _F=1.0/298.257223563; _E2=_F*(2.0-_F)
def cf_ecef(lon,lat,h=0.0):
    lam=np.radians(lon); phi=np.radians(lat)
    N=_A/np.sqrt(1.0-_E2*np.sin(phi)**2)
    return np.array([(N+h)*np.cos(phi)*np.cos(lam),
                     (N+h)*np.cos(phi)*np.sin(lam),
                     (N*(1.0-_E2)+h)*np.sin(phi)])

def wkt(epsg): return CRS.from_epsg(epsg).to_wkt(version="WKT2_2019")
def proj_en(lon,lat,h,epsg):
    t=Transformer.from_crs(CRS.from_epsg(4979),CRS.from_epsg(epsg),always_xy=True)
    return t.transform(lon,lat,h)

POINTS = [
    ("earth2_eq",  0.0,   0.0,   0.0,  None),
    ("earth2_mid", 10.21, 53.49, 38.0, None),
    ("earth2_spole",30.0,-80.0, 100.0, None),
    ("earth2_date",179.5, 12.3,  10.0, None),
    ("noaa_nyc",  -73.985656,40.748817,0.0,32618),
    ("sydney",     151.214, -33.857, 58.0,32756),
    ("wellington", 174.7762,-41.2865, 5.0, 2193),
    ("quito",     -78.4678, -0.1807,2850.0,32717),
    ("svalbard",   15.65,   78.22,  10.0,32633),
]

def author_point_stage(name, lon, lat, h, epsg):
    path = os.path.join(OUT, f"{name}.usda")
    stage = Usd.Stage.CreateNew(path)
    UsdGeom.Scope.Define(stage, "/World/CRS")
    e = epsg if epsg else 4979
    crs_path = f"/World/CRS/CRS_{e}"
    cp = stage.DefinePrim(crs_path, "CoordinateReferenceSystem")
    cp.CreateAttribute("crs:wkt", Sdf.ValueTypeNames.Token, False,
                       Sdf.VariabilityUniform).Set(wkt(e))
    if epsg is None:
        x,y,z = lon,lat,h
    else:
        x,y,z = proj_en(lon,lat,h,epsg)
    pr = UsdGeom.Xform.Define(stage, "/World/P").GetPrim()
    pr.CreateRelationship("crs:binding", False).SetTargets([crs_path])
    pr.CreateAttribute("crs:position", Sdf.ValueTypeNames.Double3, False).Set(Gf.Vec3d(x,y,z))
    stage.GetRootLayer().Save()
    return path, "/World/P", cf_ecef(lon,lat,h)

def main():
    rows = []
    for (name,lon,lat,h,epsg) in POINTS:
        path, primpath, gt = author_point_stage(name,lon,lat,h,epsg)
        stage = Usd.Stage.Open(path)
        prim = stage.GetPrimAtPath(primpath)
        cache={}
        w,_ = rr.resolve_world_translation(prim, ECEF, cache)
        w = np.array(w)
        rows.append((path, primpath, "translation", gt, w, None))

    # railway anchor+curve subtree: inject-don't-bake + orientation parity
    rail = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "usdGeospatial", "out", "railway_georef.usda")
    rail = os.path.abspath(rail)
    # Auto-convert the committed real railway asset if it hasn't been built yet,
    # so the oracle always carries the inject-don't-bake / orientation rows (the
    # 30-row parity set: 9 points + 16 rail samples + 5 anchor frames).
    if not os.path.exists(rail):
        deutschebahn = os.path.abspath(os.path.join(
            os.path.dirname(rail), "..", "data", "thirdparty", "deutschebahn-rails.usda"))
        if os.path.exists(deutschebahn):
            import convert_omni_geospatial as cog
            os.makedirs(os.path.dirname(rail), exist_ok=True)
            cog.convert(deutschebahn, rail)
    if os.path.exists(rail):
        stage = Usd.Stage.Open(rail)
        cache={}
        # anchor-frame parity on the first curve (local 0,0,0 -> georef)
        n=0
        for p in stage.Traverse():
            if not p.GetAttribute(rr.CRS_POSITION_ATTR): continue
            n+=1
            if n % 97 and n>1: continue   # sample
            pos = p.GetAttribute(rr.CRS_POSITION_ATTR).Get()
            w,_ = rr.resolve_world_translation(p, ECEF, cache)
            rows.append((rail, str(p.GetPath()), "translation",
                         cf_ecef(pos[0],pos[1],pos[2]), np.array(w), None))
        # full injected anchor frame matrix on a few curves
        m=0
        for p in stage.Traverse():
            if not (p.GetName().startswith("CurveXform") and p.GetAttribute(rr.CRS_POSITION_ATTR)):
                continue
            m+=1
            if m>5: break
            M,_ = rr.anchor_frame(p, ECEF, cache)
            pos = p.GetAttribute(rr.CRS_POSITION_ATTR).Get()
            flat = [M[i][j] for i in range(4) for j in range(4)]
            rows.append((rail, str(p.GetPath()), "frame",
                         cf_ecef(pos[0],pos[1],pos[2]),
                         np.array(M.Transform(Gf.Vec3d(0,0,0))), flat))
    else:
        print(f"[warn] railway stage not found at {rail}; skipping injection parity",
              file=sys.stderr)

    op = os.path.join(OUT, "oracle.tsv")
    with open(op, "w") as f:
        for (path, primpath, kind, gt, w, flat) in rows:
            fields = [path, primpath, kind,
                      repr(float(gt[0])),repr(float(gt[1])),repr(float(gt[2])),
                      repr(float(w[0])), repr(float(w[1])), repr(float(w[2]))]
            if flat is not None:
                fields += [repr(float(x)) for x in flat]
            f.write("\t".join(fields)+"\n")
    print(f"[dump_oracle] wrote {len(rows)} rows -> {op}")
    print(f"[dump_oracle] stages in {OUT}")

if __name__ == "__main__":
    main()
