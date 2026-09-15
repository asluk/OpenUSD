#!/usr/bin/env python3
"""
reencode_georef.py  --  Re-encode an OSS Earth-2 (GFS) field as a GEOREFERENCED
USD scene instead of a baked Cartesian sphere.

Design (mirrors the Esri AOUSD CRS proposal + the schema-declares / runtime-resolves
separation proven by the omniGeoSceneIndex PoC):

  * A `CoordinateReferenceSystem` prim carries an OGC WKT2 string (`crs:wkt`).
    Pure data. No geometry, no transform behavior.
  * Each georeferenced Xform is BOUND to a CRS via a *relationship* `crs:binding`
    (parallel to UsdShadeMaterialBindingAPI), NOT via references-as-binding and
    NOT via SetResetXformStack. The authored Xformable stays semantically neutral.
  * The prim's position is authored as an absolute geodetic coordinate in the
    bound CRS, in a float64 attribute (`crs:position` = lon, lat, ellipsoidal-h).
    The Cartesian `xformOp:translate` is left for a runtime resolver to fill in.

This file only AUTHORS DATA. All coordinate math / world-transform resolution
lives in resolve_runtime.py, exactly like the Gaussian schema keeps splat runtime
in hdParticleField rather than in usdVol.

Two authoring paths, IDENTICAL output:
  * default            -- per-prim Usd API (didactic, readable, but slow at scale)
  * --fast (Sdf batch) -- author PrimSpec/AttributeSpec/RelationshipSpec directly
                          inside one Sdf.ChangeBlock; much faster for large grids
                          because it skips per-op composition/notification.
"""
import argparse, time, numpy as np, xarray as xr
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _schema_setup  # registers the codeless CRS schema so custom=False is truthful  # noqa
from pyproj import CRS
from pxr import Usd, UsdGeom, Sdf, Gf, Vt

# Standard OGC/EPSG CRSs -- we INVENT NOTHING; adopt WKT2.
CRS_GEO_3D = CRS.from_epsg(4979)   # WGS84 geographic 3D: lat, lon, ellipsoidal height
CRS_ECEF   = CRS.from_epsg(4978)   # WGS84 geocentric ECEF (the cartesian "render" frame)

GEOSPATIAL_CRS_TYPE = "CoordinateReferenceSystem"   # typed-prim name (Esri proposal)
GEO_CRS_PATH = "/World/CRS/WGS84_Geographic3D"


def load_gfs(path):
    ds = xr.open_dataset(path, decode_cf=False)
    name = [v for v in ds.data_vars if ds[v].ndim >= 2][0]
    field = np.asarray(ds[name]).squeeze().astype(np.float64)   # (lat, lon)
    lat = np.asarray(ds["lat"]).astype(np.float64)
    lon = np.asarray(ds["lon"]).astype(np.float64)
    return field, lat, lon


def author_crs_prim(stage, path, crs: CRS, name: str):
    """Author a CoordinateReferenceSystem prim. Pure data: just the WKT2 token."""
    prim = stage.DefinePrim(path, GEOSPATIAL_CRS_TYPE)
    a = prim.CreateAttribute("crs:wkt", Sdf.ValueTypeNames.Token,
                             custom=False, variability=Sdf.VariabilityUniform)
    a.Set(crs.to_wkt(version="WKT2_2019"))
    # schema-defined now (codeless CoordinateReferenceSystem) -> custom=False
    prim.CreateAttribute("crs:epsg", Sdf.ValueTypeNames.Int, custom=False).Set(int(crs.to_epsg()))
    prim.CreateAttribute("crs:displayName", Sdf.ValueTypeNames.String, custom=False).Set(name)
    return prim


def bind_crs(prim, crs_prim):
    """Bind an Xformable to a CRS via a RELATIONSHIP (the converged design).

    Parallels UsdShadeMaterialBindingAPI:  rel crs:binding -> </CRS/...>.
    We deliberately do NOT add the CRS as a reference, and do NOT call
    SetResetXformStack -- no runtime behavior baked into scene description.
    """
    rel = prim.CreateRelationship("crs:binding", custom=False)
    rel.SetTargets([crs_prim.GetPath()])
    return rel


def author_samples_usd(stage, field, lat, lon, stride):
    """Per-prim Usd-API authoring path (readable; slow at scale)."""
    geo_prim = stage.GetPrimAtPath(GEO_CRS_PATH)
    n = 0
    for i, la in enumerate(lat[::stride]):
        for j, lo in enumerate(lon[::stride]):
            t2m = float(field[i*stride, j*stride])
            xf = UsdGeom.Xform.Define(stage, f"/World/GeoSamples/p_{i}_{j}")
            p = xf.GetPrim()
            p.ApplyAPI("BindingAPI")   # real applied API schema (review fix #3a)
            bind_crs(p, geo_prim)
            pos = p.CreateAttribute("crs:position", Sdf.ValueTypeNames.Double3, custom=False)
            pos.Set(Gf.Vec3d(float(lo), float(la), 0.0))
            p.CreateAttribute("primvars:t2m", Sdf.ValueTypeNames.Float, custom=True).Set(t2m)
            n += 1
    return n


def author_samples_sdf(stage, field, lat, lon, stride):
    """Sdf batch authoring path: identical output, much faster at scale.

    Author PrimSpec/AttributeSpec/RelationshipSpec straight onto the layer inside
    a single Sdf.ChangeBlock, so USD does not recompose or fire change
    notifications per prim -- the dominant cost in the per-prim path.
    """
    layer = stage.GetRootLayer()
    parent = layer.GetPrimAtPath(Sdf.Path("/World/GeoSamples"))
    n = 0
    with Sdf.ChangeBlock():
        for i, la in enumerate(lat[::stride]):
            for j, lo in enumerate(lon[::stride]):
                t2m = float(field[i*stride, j*stride])
                ps = Sdf.PrimSpec(parent, f"p_{i}_{j}", Sdf.SpecifierDef, "Xform")
                # mirror ApplyAPI in the Sdf path so both outputs stay identical
                ps.SetInfo("apiSchemas", Sdf.TokenListOp.Create(prependedItems=["BindingAPI"]))

                rs = Sdf.RelationshipSpec(ps, "crs:binding", custom=False)
                rs.targetPathList.explicitItems.append(Sdf.Path(GEO_CRS_PATH))

                aps = Sdf.AttributeSpec(ps, "crs:position", Sdf.ValueTypeNames.Double3)
                aps.default = Gf.Vec3d(float(lo), float(la), 0.0)

                at = Sdf.AttributeSpec(ps, "primvars:t2m", Sdf.ValueTypeNames.Float)
                at.custom = True
                at.default = float(t2m)
                n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gfs", default="data/gfs_t2m.nc")
    ap.add_argument("--out", default="out/earth2_georef.usda")
    ap.add_argument("--stride", type=int, default=12, help="subsample stride (vertices)")
    ap.add_argument("--fast", action="store_true", help="use Sdf batch authoring (faster)")
    args = ap.parse_args()

    field, lat, lon = load_gfs(args.gfs)
    print(f"[load] field {field.shape}  t2m {field.min():.1f}..{field.max():.1f} K  "
          f"lat {lat.min()}..{lat.max()}  lon {lon.min()}..{lon.max()}")

    stage = Usd.Stage.CreateNew(args.out)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    # Guard rail G3: this scene carries crs:binding, so declare that CRS resolution
    # is required -- a CRS-unaware consumer can then detect-and-refuse instead of
    # silently placing content at the world origin. See verify.py check G / README.
    stage.GetRootLayer().customLayerData = {"crsResolutionRequired": True}
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())

    # --- CRS library scope: the standards CRSs as pure data prims ---
    UsdGeom.Scope.Define(stage, "/World/CRS")
    author_crs_prim(stage, GEO_CRS_PATH, CRS_GEO_3D, "WGS84 geographic 3D (EPSG:4979)")
    author_crs_prim(stage, "/World/CRS/WGS84_ECEF", CRS_ECEF, "WGS84 geocentric ECEF (EPSG:4978)")
    UsdGeom.Scope.Define(stage, "/World/GeoSamples")

    # --- Georeferenced sample points: t2m stations placed by (lon, lat, h) ---
    # NO xformOp:translate authored here -- the runtime resolver computes ECEF.
    t0 = time.time()
    n = (author_samples_sdf if args.fast else author_samples_usd)(stage, field, lat, lon, args.stride)
    dt = time.time() - t0

    stage.GetRootLayer().Save()
    print(f"[author] wrote {n} georeferenced samples -> {args.out}  "
          f"({'Sdf-batch' if args.fast else 'per-prim'} {dt:.2f}s, {n/max(dt,1e-9):.0f} prim/s)")
    print(f"[author] CRS prims: WGS84_Geographic3D (binding target), WGS84_ECEF (render target)")
    print(f"[author] NOTE: no xformOp:translate, no resetXformStack -- authored scene is CRS-neutral")


if __name__ == "__main__":
    main()
