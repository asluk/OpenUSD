//
// Copyright 2026 NVIDIA CORPORATION & AFFILIATES
//
// Licensed under the terms set forth in the LICENSE.txt file available at
// https://openusd.org/license.
//
// Composed binding, physical placement, chart adjustment and occurrence queries.
// USD/Gf expressions use row vectors. See the ordering comments in Forward().
#ifndef USD_GEOSPATIAL_EXAMPLE_PLACEMENT_H
#define USD_GEOSPATIAL_EXAMPLE_PLACEMENT_H
#include "crs.h"
#include <pxr/base/gf/matrix3d.h>
#include <pxr/usd/usd/prim.h>
#include <pxr/usd/usd/stage.h>
namespace usdGeospatialExample {
bool HasDirectBinding(UsdPrim prim);
UsdPrim FindControllingBinding(UsdPrim prim);
std::string ReadWkt(UsdPrim prim, CoordinateEngine& engine);
void ValidatePlacementRole(UsdPrim prim);
Matrix4d GetLocalTransform(UsdPrim prim, UsdTimeCode time);

struct ModelPlacement {
    CoordinateEngine& engine;
    UsdPrim prim;
    UsdTimeCode time;
    CrsInfo source;
    std::unique_ptr<CrsInfo> working;
    ProjHandle sourceGeographic, sourceGeocentric, workingGeographic, workingGeocentric;
    Point3d position, originEcef, workingOrigin, workingOriginEcef;
    GfMatrix3d enuToEcef, orientation, stageToEnu, workingEnuToEcef;
    Matrix4d anchorAdjustment;
    bool chartReady = false;
    ModelPlacement(CoordinateEngine& engine, UsdPrim prim, UsdTimeCode time,
                   ProjHandle workingOverride = nullptr);
    void PrepareChart();
    Point3d ToChart(Point3d coordinate);
    Point3d FromChart(Point3d coordinate);
    Point3d Forward(Point3d point, ProjHandle output,
                    Matrix4d descendantTransform = Matrix4d(1), bool reset = false);
    Point3d Inverse(Point3d point, ProjHandle input,
                    Matrix4d descendantTransform = Matrix4d(1), bool reset = false);
};

// Request-scoped cache: model placements die before the caller's engine/context.
class PlacementEvaluator {
  public:
    explicit PlacementEvaluator(CoordinateEngine& engine) : _engine(engine) {}
    Point3d ResolvePoint(UsdPrim prim, Point3d point, ProjHandle output,
                         UsdTimeCode time);
    std::vector<Point3d> ResolveInstance(UsdPrim instancer, int index,
                                         UsdPrim prototypePrim,
                                         const std::vector<Point3d>& points,
                                         ProjHandle output, UsdTimeCode time);

  private:
    CoordinateEngine& _engine;
    std::map<std::string, std::shared_ptr<ModelPlacement>> _models;
};
} // namespace usdGeospatialExample
#endif
