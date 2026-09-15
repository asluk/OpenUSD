#!/usr/bin/env python3
"""
crs_engine.py -- the projection-ENGINE registration seam.

This is the seam Simon asked for on the Esri PR (projection support as a
registration interface, à la UsdGeomRegisterComputeExtentFunction): the schema
plugin is one thing; one-or-more projection ENGINES are registered separately,
and the runtime asks a registered engine to do the geodesy. PROJ/pyproj is the
DEFAULT engine here, not a hardcoded dependency -- a deployment could register a
GPU engine (cuProj) instead. This is the C-04 insertion
point.

WKT STAYS OPAQUE TO USD (Simon line 838; Aaron agrees): USD never parses the
WKT. The engine consumes the authored WKT string and is the only component that
understands it.

INTERFACE (deliberately broader than points->points; see Simon line ~828):
A CRS engine implements two operations --

  1. reproject(src_wkt, dst_wkt, xs, ys, zs, epoch=None) -> (X, Y, Z)
       Bulk coordinate reprojection. (x,y,z) follow the axis-order CONTRACT:
       always (lon/E, lat/N, h) regardless of the CRS authority's declared axis
       order (see docs/axis-order.md).

  2. local_frame_to_ecef(src_wkt, x, y, z, epoch=None) -> Gf.Matrix4d
       The RIGID local-frame -> ECEF transform (ORIENTATION + position) at a
       point. This is what anchor injection needs: a subtree authored in local
       metres (x=East, y=North, z=Up) must be rotated into the topocentric basis
       at the anchor, not merely translated. The local frame is:
         * ENU (east-north-up) for a GEOGRAPHIC source CRS, or
         * the projected plane (grid east / grid north / ellipsoidal up) for a
           PROJECTED source CRS -- i.e. the basis is taken at the anchor's
           geographic footprint either way.
       Returns a Gf.Matrix4d M such that  world_ecef = M.Transform(local_xyz).

Why operation 2 is mandatory here and not in Esri's prototype: Esri bakes a
resetXformStack with a PROJECTED (planar) target, so orientation is implicit in
the plane. Our target is ECEF, so the local->ECEF rotation must be supplied
explicitly or every asset lies down (local +Z != ECEF +Z except at the pole).
"""
import numpy as np
from pxr import Gf

_ENGINES = {}
_DEFAULT = None


def register_engine(name, engine, make_default=False):
    """Register a CRS engine instance under `name`. The first engine registered
    (or any with make_default=True) becomes the default."""
    global _DEFAULT
    _ENGINES[name] = engine
    if make_default or _DEFAULT is None:
        _DEFAULT = name
    return engine


def get_engine(name=None):
    if name is None:
        name = _DEFAULT
    if name not in _ENGINES:
        raise KeyError(f"no CRS engine registered as {name!r}; "
                       f"registered: {sorted(_ENGINES)}")
    return _ENGINES[name]


def list_engines():
    return {"default": _DEFAULT, "registered": sorted(_ENGINES)}


# ---------------------------------------------------------------------------
# Default engine: PROJ via pyproj. One registered engine, not baked in.
# ---------------------------------------------------------------------------
class PyprojEngine:
    name = "proj"

    def __init__(self):
        from pyproj import CRS, Transformer
        self._CRS = CRS
        self._Transformer = Transformer
        self._tcache = {}
        self._ecef = CRS.from_epsg(4978)

    def _crs(self, wkt):
        return self._CRS.from_wkt(wkt)

    def _transformer(self, src_wkt, dst_wkt):
        key = (src_wkt, dst_wkt)
        if key not in self._tcache:
            self._tcache[key] = self._Transformer.from_crs(
                self._crs(src_wkt), self._crs(dst_wkt), always_xy=True)
        return self._tcache[key]

    def reproject(self, src_wkt, dst_wkt, xs, ys, zs, epoch=None):
        t = self._transformer(src_wkt, dst_wkt)
        if epoch is not None:
            X, Y, Z, _ = t.transform(xs, ys, zs, epoch)
        else:
            X, Y, Z = t.transform(xs, ys, zs)
        return X, Y, Z

    def _is_geographic(self, crs):
        try:
            return crs.is_geographic
        except Exception:
            return False

    def is_projected(self, src_wkt):
        """True if the source CRS is a projected (planar/grid) CRS. Child offsets
        authored under a projected anchor live in the grid plane and must compose
        IN-PLANE (grid add + reproject), NOT be lifted through a true-ENU basis
        (which differs from grid axes by convergence + point-scale). See
        `resolve_runtime.resolve_with_injection`."""
        try:
            return bool(self._crs(src_wkt).is_projected)
        except Exception:
            return False

    def project_grid_offset_to_target(self, src_wkt, dst_wkt, anchor_xyz,
                                      offset_enu, epoch=None):
        """Compose a child's authored local offset under a PROJECTED anchor by
        adding the offset in the anchor's grid plane, then reprojecting the
        resulting grid point straight to the target CRS. `anchor_xyz` is the
        anchor's authored (E,N,h) grid position; `offset_enu` is the child's
        authored local (x=E, y=N, z=up) offset in metres. Returns the target-CRS
        (X,Y,Z). This keeps grid-authored geometry exact (0 mm) instead of
        incurring the grid-vs-ENU error of the topocentric lift."""
        gx = anchor_xyz[0] + offset_enu[0]
        gy = anchor_xyz[1] + offset_enu[1]
        gz = anchor_xyz[2] + offset_enu[2]
        X, Y, Z = self.reproject(src_wkt, dst_wkt, gx, gy, gz, epoch)
        return X, Y, Z

    def _lonlat_of(self, src_wkt, x, y, z, epoch=None):
        """Return the geographic (lon,lat,h) footprint of an authored point,
        regardless of whether the source CRS is geographic or projected."""
        src = self._crs(src_wkt)
        if self._is_geographic(src):
            return x, y, z
        # projected -> geographic
        geo = src.geodetic_crs or self._CRS.from_epsg(4979)
        t = self._Transformer.from_crs(src, geo, always_xy=True)
        if epoch is not None:
            lon, lat, h, _ = t.transform(x, y, z, epoch)
        else:
            lon, lat, h = t.transform(x, y, z)
        return lon, lat, h

    def local_frame_to_ecef(self, src_wkt, x, y, z, epoch=None):
        """Rigid ENU/topocentric local-frame -> ECEF transform at the point."""
        lon, lat, h = self._lonlat_of(src_wkt, x, y, z, epoch)
        # ECEF position of the anchor (reproject straight to 4978).
        X, Y, Z = self.reproject(src_wkt, self._ecef.to_wkt(version="WKT2_2019"),
                                 x, y, z, epoch)
        lam = np.radians(lon); phi = np.radians(lat)
        east  = np.array([-np.sin(lam),              np.cos(lam),             0.0])
        north = np.array([-np.sin(phi)*np.cos(lam), -np.sin(phi)*np.sin(lam), np.cos(phi)])
        up    = np.array([ np.cos(phi)*np.cos(lam),  np.cos(phi)*np.sin(lam), np.sin(phi)])
        # Gf.Matrix4d row-vector convention: world = local * M, and
        # M.Transform(v) applies it. Rows 0..2 are the basis vectors mapping
        # local x(E)/y(N)/z(U) into ECEF; row 3 is the ECEF origin (translation).
        M = Gf.Matrix4d(
            east[0],  east[1],  east[2],  0.0,
            north[0], north[1], north[2], 0.0,
            up[0],    up[1],    up[2],    0.0,
            X,        Y,        Z,        1.0,
        )
        return M


# register the default engine at import
register_engine(PyprojEngine.name, PyprojEngine(), make_default=True)
