//
// crsEngine.cpp -- PROJ-backed implementation of GeoCrsEngine.
//
// Geodesy is delegated to PROJ (proj.h C API). We mirror crs_engine.py's
// PyprojEngine exactly so the C++ scene index agrees with the Python reference
// runtime to sub-mm:
//   * Reproject: proj_create_crs_to_crs_from_pj(src, dst) with always_xy
//     normalization (proj_normalize_for_visualization), then proj_trans.
//   * LonLatOf: if the source CRS is projected, transform to its geodetic CRS;
//     if geographic, the input is already (lon,lat,h).
//   * LocalFrameToEcef: build the ENU basis at (lon,lat) and use the ECEF
//     position of the point as the origin; pack into a Gf row-vector matrix
//     IDENTICAL to crs_engine.PyprojEngine.local_frame_to_ecef.
//
#include "crsEngine.h"

#include <pxr/base/tf/diagnostic.h>

#include <proj.h>

#include <cmath>

PXR_NAMESPACE_OPEN_SCOPE

namespace {
constexpr const char* kEcefWkt =
    // EPSG:4978 (WGS84 geocentric / ECEF). We pass an authority string; PROJ
    // resolves it from its db. Using "EPSG:4978" keeps us off any WKT-version
    // quirks for the well-known target.
    "EPSG:4978";
}

struct GeoCrsEngine::Impl
{
    PJ_CONTEXT* ctx = nullptr;

    // cache of normalized crs->crs transformers keyed by (src||dst)
    mutable std::mutex mutex;
    mutable std::unordered_map<std::string, PJ*> tcache;
    // cache of src-wkt -> its geodetic-CRS auth-or-wkt string
    mutable std::unordered_map<std::string, std::string> geodeticCache;

    Impl() { ctx = proj_context_create(); }
    ~Impl()
    {
        for (auto& kv : tcache) {
            if (kv.second) proj_destroy(kv.second);
        }
        if (ctx) proj_context_destroy(ctx);
    }

    PJ* GetTransformer(const std::string& srcWkt, const std::string& dstWkt) const
    {
        const std::string key = srcWkt + "\x1e" + dstWkt;
        std::lock_guard<std::mutex> lock(mutex);
        auto it = tcache.find(key);
        if (it != tcache.end()) return it->second;

        PJ* P = proj_create_crs_to_crs(ctx, srcWkt.c_str(), dstWkt.c_str(), nullptr);
        if (!P) {
            TF_WARN("GeoCrsEngine: proj_create_crs_to_crs failed for src/dst");
            tcache[key] = nullptr;
            return nullptr;
        }
        // always_xy: normalize so inputs/outputs are (lon/E, lat/N) order,
        // equivalent to pyproj Transformer.from_crs(..., always_xy=True).
        PJ* Pn = proj_normalize_for_visualization(ctx, P);
        proj_destroy(P);
        tcache[key] = Pn;
        return Pn;
    }

    // Return an authority/WKT string for the geodetic (lon/lat) CRS underlying
    // srcWkt. If srcWkt is already geographic, returns srcWkt unchanged.
    std::string GeodeticOf(const std::string& srcWkt) const
    {
        {
            std::lock_guard<std::mutex> lock(mutex);
            auto it = geodeticCache.find(srcWkt);
            if (it != geodeticCache.end()) return it->second;
        }
        std::string result = srcWkt;
        PJ* crs = proj_create(ctx, srcWkt.c_str());
        if (crs) {
            int t = proj_get_type(crs);
            const bool isGeographic =
                (t == PJ_TYPE_GEOGRAPHIC_2D_CRS ||
                 t == PJ_TYPE_GEOGRAPHIC_3D_CRS ||
                 t == PJ_TYPE_GEODETIC_CRS);
            if (!isGeographic) {
                PJ* geod = proj_crs_get_geodetic_crs(ctx, crs);
                if (geod) {
                    const char* wkt = proj_as_wkt(ctx, geod, PJ_WKT2_2019, nullptr);
                    if (wkt) result = wkt;
                    proj_destroy(geod);
                }
            }
            proj_destroy(crs);
        }
        std::lock_guard<std::mutex> lock(mutex);
        geodeticCache[srcWkt] = result;
        return result;
    }
};

GeoCrsEngine::GeoCrsEngine() : _impl(new Impl()) {}
GeoCrsEngine::~GeoCrsEngine() = default;

GeoCrsEngine& GeoCrsEngine::GetDefault()
{
    static GeoCrsEngine engine;
    return engine;
}

GfVec3d GeoCrsEngine::Reproject(const std::string& srcWkt, const std::string& dstWkt,
                                double x, double y, double z, double epoch) const
{
    PJ* P = _impl->GetTransformer(srcWkt, dstWkt);
    if (!P) return GfVec3d(0.0);
    PJ_COORD c = proj_coord(x, y, z, epoch >= 0.0 ? epoch : HUGE_VAL);
    PJ_COORD o = proj_trans(P, PJ_FWD, c);
    return GfVec3d(o.xyzt.x, o.xyzt.y, o.xyzt.z);
}

GfVec3d GeoCrsEngine::LonLatOf(const std::string& srcWkt,
                               double x, double y, double z, double epoch) const
{
    const std::string geod = _impl->GeodeticOf(srcWkt);
    if (geod == srcWkt) {
        // already geographic: (x=lon, y=lat, z=h)
        return GfVec3d(x, y, z);
    }
    return Reproject(srcWkt, geod, x, y, z, epoch);
}

GfMatrix4d GeoCrsEngine::LocalFrameToEcef(const std::string& srcWkt,
                                          double x, double y, double z,
                                          double epoch) const
{
    // geographic footprint
    GfVec3d ll = LonLatOf(srcWkt, x, y, z, epoch);
    const double lon = ll[0];
    const double lat = ll[1];

    // ECEF position of the anchor (reproject straight to 4978)
    GfVec3d X = Reproject(srcWkt, kEcefWkt, x, y, z, epoch);

    const double lam = lon * M_PI / 180.0;
    const double phi = lat * M_PI / 180.0;
    const double sl = std::sin(lam), cl = std::cos(lam);
    const double sp = std::sin(phi), cp = std::cos(phi);

    // basis vectors (identical to crs_engine.py)
    const GfVec3d east (-sl,        cl,       0.0);
    const GfVec3d north(-sp * cl, -sp * sl,  cp);
    const GfVec3d up   ( cp * cl,  cp * sl,  sp);

    // Gf row-vector convention: rows 0..2 are the basis mapping local
    // x(E)/y(N)/z(U) into ECEF; row 3 is the ECEF origin (translation).
    return GfMatrix4d(
        east[0],  east[1],  east[2],  0.0,
        north[0], north[1], north[2], 0.0,
        up[0],    up[1],    up[2],    0.0,
        X[0],     X[1],     X[2],     1.0);
}

PXR_NAMESPACE_CLOSE_SCOPE
