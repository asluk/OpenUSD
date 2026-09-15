//
// crsEngine.h -- C++ CRS engine seam (mirrors src/crs_engine.py).
//
// Contract (identical to the Python reference):
//   * WKT STAYS OPAQUE TO USD. USD never parses WKT. This engine is the only
//     component that consumes the authored WKT string; it hands it to PROJ.
//   * Two operations:
//       Reproject(srcWkt, dstWkt, x, y, z, epoch) -> (X,Y,Z)
//       LocalFrameToEcef(srcWkt, x, y, z, epoch)  -> GfMatrix4d
//     The (x,y,z) follow the AXIS-ORDER CONTRACT: always (lon/E, lat/N, h),
//     regardless of the CRS authority's declared axis order (PROJ always_xy).
//   * LocalFrameToEcef returns the RIGID ENU/topocentric local-frame -> ECEF
//     transform (orientation + position): world_ecef = M.Transform(local_xyz),
//     using Gf row-vector convention (basis vectors in rows 0..2, origin row 3).
//
// This is a C++ form of crs_engine.PyprojEngine; PROJ is linked
// directly (libproj). A different deployment could swap a GPU engine in behind
// the same interface, exactly as the Python seam allows.
//
#ifndef USDGEOSPATIAL_CRS_ENGINE_H
#define USDGEOSPATIAL_CRS_ENGINE_H

#include <pxr/pxr.h>
#include <pxr/base/gf/matrix4d.h>
#include <pxr/base/gf/vec3d.h>

#include <string>
#include <memory>
#include <mutex>
#include <unordered_map>

PXR_NAMESPACE_OPEN_SCOPE

/// A CRS engine: consumes opaque WKT, performs geodesy via PROJ.
class GeoCrsEngine
{
public:
    GeoCrsEngine();
    ~GeoCrsEngine();

    /// Process-wide default engine (matches the Python module-level default).
    static GeoCrsEngine& GetDefault();

    /// Reproject a single (x=lon/E, y=lat/N, z=h) point from srcWkt to dstWkt.
    /// epoch < 0 means "unspecified" (no 4D time coordinate).
    GfVec3d Reproject(const std::string& srcWkt, const std::string& dstWkt,
                      double x, double y, double z, double epoch = -1.0) const;

    /// Rigid ENU/topocentric local-frame -> ECEF (EPSG:4978) transform at the
    /// authored point. Works for geographic AND projected source CRSs (the basis
    /// is taken at the point's geographic footprint either way).
    GfMatrix4d LocalFrameToEcef(const std::string& srcWkt,
                                double x, double y, double z,
                                double epoch = -1.0) const;

    /// Geographic (lon,lat,h) footprint of an authored point (handles projected
    /// source CRS by projecting to its geodetic CRS). Exposed for testing.
    GfVec3d LonLatOf(const std::string& srcWkt,
                     double x, double y, double z, double epoch = -1.0) const;

private:
    struct Impl;
    std::unique_ptr<Impl> _impl;
};

PXR_NAMESPACE_CLOSE_SCOPE

#endif
