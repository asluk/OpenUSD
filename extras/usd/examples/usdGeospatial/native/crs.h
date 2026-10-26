// WKT interpretation, source height and offline realized PROJ operations.
// See audit/source-contract.md: requirements 1-4, 12-13, 21, 28-29, 31.
#ifndef USD_GEOSPATIAL_EXAMPLE_CRS_H
#define USD_GEOSPATIAL_EXAMPLE_CRS_H
#include "common.h"
#include <map>
#include <memory>
#include <proj.h>
#include <set>
namespace usdGeospatialExample {
struct ProjObject {
    PJ* handle = nullptr;
    ProjObject() = default;
    explicit ProjObject(PJ* value) : handle(value) {}
    ~ProjObject()
    {
        if (handle) {
            proj_destroy(handle);
        }
    }
    ProjObject(const ProjObject&) = delete;
    ProjObject& operator=(const ProjObject&) = delete;
};
using ProjHandle = std::shared_ptr<ProjObject>;
std::string NormalizeWkt(const std::string& text);

// Operation handles are destroyed before their owning PROJ context.
struct CoordinateEngine {
    PJ_CONTEXT* context = proj_context_create();
    std::map<std::pair<PJ*, PJ*>, ProjHandle> operationCache;
    JsonArray operations;
    JsonArray diagnostics;
    std::set<std::string> seenOperations;
    CoordinateEngine();
    ~CoordinateEngine();
    CoordinateEngine(const CoordinateEngine&) = delete;
    CoordinateEngine& operator=(const CoordinateEngine&) = delete;
    ProjHandle ParseWkt(const std::string& text);
    std::string SerializeWkt(ProjHandle crs);
    JsonValue DescribeCrs(ProjHandle crs);
    ProjHandle WithCoordinateSystem(ProjHandle crs, bool geocentric);
    Point3d Convert(Point3d point, ProjHandle source, ProjHandle output);
};

// Component order is the proposal's semantic XYZ order, adapted through PROJ.
struct CrsInfo {
    CoordinateEngine& engine;
    ProjHandle crs;
    bool isGeographic = false, isGeocentric = false, assumedHeight = false;
    Point3d componentUnits{1, 1, 1};
    std::vector<std::string> unitNames;
    CrsInfo(CoordinateEngine& engine, ProjHandle crs, bool model);
    void ReadAxes();
    JsonValue HeightReport();
};
} // namespace usdGeospatialExample
#endif
